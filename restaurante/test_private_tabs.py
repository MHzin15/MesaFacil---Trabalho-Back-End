"""Contratos reais entre navegadores independentes: sem autorizações de fixture."""
from datetime import timedelta
from uuid import uuid4
from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from . import services
from .models import Categoria, ConviteComanda, Mesa, Pedido, Perfil, Produto, SessaoMesa
from .test_support import conferencia


class PrivateTabsTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1)
        self.produto = Produto.objects.create(categoria=Categoria.objects.create(nome='Teste'), nome='Item', preco='10.00')
        self.staff = User.objects.create_user('equipe-comandas')
        Perfil.objects.create(user=self.staff, role='GARCOM')
        self.base = f'/api/mesa/{self.mesa.token_uuid}/'
        self.a = self.visitante()
        self.b = self.visitante()

    def visitante(self):
        client = APIClient(enforce_csrf_checks=True)
        client.get(f'/mesa/{self.mesa.token_uuid}/')
        return client

    def post(self, client, url, data=None):
        return client.post(url, data or {}, format='json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)

    def pedir(self, client, **extra):
        ctx = client.get(self.base).data
        return self.post(client, '/api/pedidos/criar/', {
            'mesa_uuid': str(self.mesa.token_uuid), 'sessao_id': ctx['sessao_id'],
            'chave_envio': str(uuid4()), 'itens': [{'produto_id': self.produto.pk, 'quantidade': 1}], **extra})

    def convite(self, client):
        response = self.post(client, self.base + 'compartilhar/')
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def entrar(self, client, invite):
        url = urlparse(invite['url']).path
        self.assertEqual(client.get(url).status_code, 200)
        response = self.post(client, url)
        self.assertEqual(response.status_code, 302)

    def test_same_table_qr_creates_separate_accounts_and_never_exposes_others(self):
        a = self.pedir(self.a)
        b = self.pedir(self.b)
        self.assertEqual((a.status_code, b.status_code), (201, 201))
        self.assertNotEqual(a.data['sessao'], b.data['sessao'])
        self.assertEqual(SessaoMesa.objects.filter(mesa=self.mesa, ativa=True).count(), 2)
        for client, own, foreign in ((self.a, a, b), (self.b, b, a)):
            client.get(f'/mesa/{self.mesa.token_uuid}/conta/')
            self.assertEqual([p['id'] for p in client.get(self.base + 'pedidos/').data], [own.data['id']])
            bill = client.get(self.base + 'conta/').data
            self.assertEqual(bill['valor_total'], '10.00')
            self.assertEqual(bill['sessao_id'], own.data['sessao'])
            self.assertEqual(self.pedir(client, sessao_id=foreign.data['sessao']).status_code, 403)
        stranger = self.visitante()
        self.assertIsNone(stranger.get(self.base).data['sessao_id'])
        self.assertEqual(stranger.get(self.base + 'pedidos/').data, [])
        self.assertEqual(stranger.get(self.base + 'conta/').status_code, 404)

    def test_invitation_explicitly_joins_only_the_shared_account(self):
        first = self.pedir(self.a)
        invite = self.convite(self.a)
        path = urlparse(invite['url']).path
        self.assertEqual(self.b.get(path).status_code, 200)
        self.assertIsNone(self.b.get(self.base).data['sessao_id'])
        self.assertEqual(self.b.post(path).status_code, 403)
        self.entrar(self.b, invite)
        second = self.pedir(self.b)
        self.assertEqual(second.data['sessao'], first.data['sessao'])
        self.assertEqual(self.a.get(self.base + 'conta/').data['valor_total'], '20.00')
        self.assertEqual(SessaoMesa.objects.count(), 1)

    def test_previous_account_remains_accessible_after_joining_and_cannot_select_stranger(self):
        a = self.pedir(self.a)
        b = self.pedir(self.b)
        self.entrar(self.b, self.convite(self.a))
        self.assertEqual(self.b.get(self.base).data['sessao_id'], a.data['sessao'])
        self.assertEqual({c['id'] for c in self.b.get(self.base).data['comandas']}, {a.data['sessao'], b.data['sessao']})
        self.assertEqual(self.post(self.b, self.base + 'selecionar-comanda/', {'comanda_id': b.data['sessao']}).status_code, 200)
        self.assertEqual(self.b.get(self.base).data['sessao_id'], b.data['sessao'])
        outsider = self.visitante()
        self.assertEqual(self.post(outsider, self.base + 'selecionar-comanda/', {'comanda_id': a.data['sessao']}).status_code, 404)

    def test_payment_closes_only_one_account_and_old_device_never_enters_other_family(self):
        a = self.pedir(self.a)
        b = self.pedir(self.b)
        invite = self.convite(self.a)
        self.entrar(self.b, invite)
        manager = User.objects.create_user('gerente-comandas')
        Perfil.objects.create(user=manager, role='ADMIN')
        for status in ('EM_PREPARACAO', 'PRONTO', 'A_CAMINHO', 'ENTREGUE'):
            services.transitar(a.data['id'], status, manager)
        sessao = SessaoMesa.objects.get(pk=a.data['sessao'])
        services.pagar(sessao.pk, 'PIX', self.staff, **conferencia(sessao))
        self.assertTrue(SessaoMesa.objects.get(pk=b.data['sessao']).ativa)
        self.assertEqual(Mesa.objects.get(pk=self.mesa.pk).status_display, 'ocupada')
        for client in (self.a, self.b):
            client.get(f'/mesa/{self.mesa.token_uuid}/')
            self.assertTrue(client.get(self.base).data['atendimento_encerrado'])
            self.assertEqual(client.get(self.base + 'pedidos/').status_code, 403)
        outsider = self.visitante()
        self.assertEqual(outsider.get(urlparse(invite['url']).path).status_code, 410)
        self.post(self.a, self.base + 'novo-atendimento/')
        self.assertIsNone(self.a.get(self.base).data['sessao_id'])
        self.assertEqual(self.a.get(self.base + 'pedidos/').data, [])
        third = self.pedir(self.a)
        self.assertNotIn(third.data['sessao'], (a.data['sessao'], b.data['sessao']))

    def test_expired_invitation_and_qr_cannot_grant_access(self):
        self.pedir(self.a)
        invite = self.convite(self.a)
        ConviteComanda.objects.update(expira_em=timezone.now() - timedelta(seconds=1))
        path = urlparse(invite['url']).path
        self.assertEqual(self.b.get(path).status_code, 410)
        self.assertEqual(self.post(self.b, path).status_code, 410)
        self.assertIsNone(self.b.get(self.base).data['sessao_id'])
        self.assertEqual(self.a.get(invite['qr_url']).status_code, 404)

    def test_share_requires_csrf_and_owner_and_qr_is_private_png(self):
        self.assertEqual(self.post(self.a, self.base + 'compartilhar/').status_code, 400)
        self.pedir(self.a)
        self.assertEqual(self.a.post(self.base + 'compartilhar/').status_code, 403)
        invite = self.convite(self.a)
        self.assertEqual(self.convite(self.a)['url'], invite['url'])
        response = self.a.get(invite['qr_url'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertTrue(response.content.startswith(b'\x89PNG'))
        self.assertEqual(self.b.get(invite['qr_url']).status_code, 404)
        self.assertEqual(self.b.post(urlparse(invite['url']).path, {}, HTTP_X_CSRFTOKEN=self.b.cookies['csrftoken'].value,
                                    HTTP_ORIGIN='https://example.invalid').status_code, 403)
        landing = self.b.get(urlparse(invite['url']).path)
        self.assertEqual(landing['Referrer-Policy'], 'same-origin')
        self.assertEqual(landing['Cache-Control'], 'no-store')
        self.assertNotContains(landing, self.produto.nome)

    def test_waiter_view_lists_all_commands_but_does_not_expose_access_credentials(self):
        a = self.pedir(self.a)
        b = self.pedir(self.b)
        self.post(self.a, self.base + 'solicitar-conta/')
        self.post(self.b, self.base + 'solicitar-conta/')
        staff = APIClient()
        staff.force_authenticate(self.staff)
        table = staff.get('/api/garcom/mapa-mesas/').data[0]
        self.assertEqual({c['id'] for c in table['comandas_abertas']}, {a.data['sessao'], b.data['sessao']})
        self.assertEqual(len(staff.get('/api/garcom/').data['comandas_aguardando_conta']), 2)
        orders = staff.get(self.base + 'pedidos/?equipe=1').data
        self.assertEqual(len(orders), 2)
        self.assertEqual(staff.get(self.base + 'conta/?equipe=1').data['valor_total'], '20.00')
        secret = str(SessaoMesa.objects.get(pk=a.data['sessao']).acesso_uuid)
        self.assertNotIn(secret, str(table))
        self.assertNotIn(secret, str(staff.get('/api/sessoes/').data))
        self.assertEqual(self.a.get(self.base + '?equipe=1').status_code, 403)
        admin = User.objects.create_user('gestao-comandas')
        Perfil.objects.create(user=admin, role='ADMIN')
        staff.force_authenticate(user=None)
        staff.force_login(admin)
        self.assertEqual(staff.get('/admin/').context['ocupadas'], 1)

    def test_closing_one_command_does_not_block_new_orders_in_another(self):
        a = self.pedir(self.a)
        b = self.pedir(self.b)
        self.post(self.a, self.base + 'solicitar-conta/')
        self.assertEqual(self.pedir(self.a).status_code, 400)
        self.assertEqual(self.pedir(self.b).status_code, 201)
        self.assertNotEqual(a.data['sessao'], b.data['sessao'])

    def test_new_draft_does_not_reveal_foreign_command_or_create_empty_session(self):
        a = self.pedir(self.a)
        before = SessaoMesa.objects.count()
        self.post(self.b, self.base + 'novo-atendimento/')
        self.assertEqual(SessaoMesa.objects.count(), before)
        self.assertNotIn(a.data['sessao'], [c['id'] for c in self.b.get(self.base).data['comandas']])
        self.assertNotEqual(self.a.get(self.base).data['atendimento_id'], self.b.get(self.base).data['atendimento_id'])
