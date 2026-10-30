from html.parser import HTMLParser

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Mesa, Perfil


class PaginasTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mesa = Mesa.objects.create(numero=1)
        cls.cozinha = User.objects.create_user(username='cozinha')
        Perfil.objects.create(user=cls.cozinha, role='COZINHA')
        cls.garcom = User.objects.create_user(username='garcom')
        Perfil.objects.create(user=cls.garcom, role='GARCOM')

    def test_inicio_cardapio_e_login_renderizam(self):
        for url, texto in (('/', 'Seu próximo'), (reverse('cliente', args=[self.mesa.token_uuid]), 'Nosso cardápio'),
                           ('/entrar/', 'Acessar meu painel')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, texto)
                self.assertContains(response, 'lang="pt-BR"')

    def test_cozinha_exige_login_e_perfil(self):
        self.assertRedirects(self.client.get('/cozinha/'), '/entrar/?next=/cozinha/')
        self.client.force_login(self.garcom)
        self.assertEqual(self.client.get('/cozinha/').status_code, 403)
        self.client.force_login(self.cozinha)
        self.assertContains(self.client.get('/cozinha/'), 'Disponibilidade dos produtos')
        self.assertRedirects(self.client.get('/painel/'), '/cozinha/')

    def test_csrf_e_logout_por_post(self):
        self.client.force_login(self.cozinha)
        self.assertEqual(self.client.get('/sair/').status_code, 405)
        self.assertRedirects(self.client.post('/sair/'), '/')

    def test_mesa_inativa_nao_abre_cardapio(self):
        self.mesa.ativa = False
        self.mesa.save()
        self.assertEqual(self.client.get(reverse('cliente', args=[self.mesa.token_uuid])).status_code, 404)

    def test_client_deep_links_open_one_screen_and_keep_table_context(self):
        class Screens(HTMLParser):
            def __init__(self):
                super().__init__()
                self.visible = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if 'data-client-screen' in attrs and 'hidden' not in attrs:
                    self.visible.append(attrs['data-client-screen'])

        for name, screen in [('cliente', 'cardapio'), ('cliente-carrinho', 'carrinho'),
                             ('cliente-pedidos', 'pedidos'), ('cliente-conta', 'conta')]:
            with self.subTest(screen=screen):
                response = self.client.get(reverse(name, args=[self.mesa.token_uuid]))
                self.assertEqual(response.status_code, 200)
                parser = Screens()
                parser.feed(response.content.decode())
                self.assertEqual(parser.visible, [screen])
                self.assertEqual(response['Cache-Control'], 'no-store')
                self.assertIn(str(self.mesa.token_uuid), self.client.session['mesas'])

    def test_inactive_table_cannot_be_accessed_by_client_deep_links(self):
        self.mesa.ativa = False
        self.mesa.save()
        for name in ('cliente-carrinho', 'cliente-pedidos', 'cliente-conta'):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=[self.mesa.token_uuid])).status_code, 404)

    def test_staff_deep_links_keep_role_permissions(self):
        pages = [('/garcom/', self.garcom, self.cozinha, 'mesas'),
                 ('/garcom/entregas/', self.garcom, self.cozinha, 'entregas'),
                 ('/garcom/contas/', self.garcom, self.cozinha, 'contas'),
                 ('/cozinha/', self.cozinha, self.garcom, 'fila'),
                 ('/cozinha/disponibilidade/', self.cozinha, self.garcom, 'disponibilidade')]
        for path, allowed, denied, screen in pages:
            with self.subTest(path=path):
                self.client.logout()
                self.assertEqual(self.client.get(path).status_code, 302)
                self.client.force_login(denied)
                self.assertEqual(self.client.get(path).status_code, 403)
                self.client.force_login(allowed)
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'data-staff-view="{screen}"')
                self.assertEqual(response['Cache-Control'], 'no-store')
                self.assertNotContains(response, 'ESPAÇOS DO ADMINISTRADOR')

    def test_staff_login_destinations_are_unchanged(self):
        admin = User.objects.create_user('gestor')
        Perfil.objects.create(user=admin, role='ADMIN')
        for user, target in [(self.garcom, '/garcom/'), (self.cozinha, '/cozinha/'), (admin, '/admin/')]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertRedirects(self.client.get('/painel/'), target, fetch_redirect_response=False)

    def test_admin_home_exposes_existing_management_actions_to_manager(self):
        admin = User.objects.create_user('gestor-painel')
        Perfil.objects.create(user=admin, role='ADMIN')
        self.client.force_login(admin)
        response = self.client.get('/admin/')
        self.assertContains(response, 'Administração do restaurante')
        for url in ('/admin/restaurante/mesa/', '/admin/restaurante/produto/',
                    '/admin/auth/user/', '/admin/restaurante/pedido/'):
            self.assertContains(response, f'href="{url}"')
        self.client.force_login(self.garcom)
        self.assertEqual(self.client.get('/admin/').status_code, 302)
