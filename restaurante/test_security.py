from io import BytesIO
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient
from .models import Mesa, SessaoMesa, Categoria, Produto, Pedido, ItemPedido, Conta, Perfil
from . import services


class SecurityTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1)
        self.sessao = SessaoMesa.objects.create(mesa=self.mesa)
        self.produto = Produto.objects.create(categoria=Categoria.objects.create(nome='Lanches'), nome='Hambúrguer', preco='32.90')
        self.admin = User.objects.create_superuser('gestor', password='local-test-password')
        self.client = APIClient(enforce_csrf_checks=True)

    def bootstrap(self):
        response = self.client.get(f'/api/mesa/{self.mesa.token_uuid}/')
        self.assertEqual(response.status_code, 200)
        return {'HTTP_X_CSRFTOKEN': self.client.cookies['csrftoken'].value}

    def payload(self):
        return {'mesa_uuid': str(self.mesa.token_uuid), 'sessao_id': self.sessao.pk,
                'itens': [{'produto_id': self.produto.pk, 'quantidade': 1}]}

    def test_anonymous_writes_require_csrf_even_with_table_context(self):
        headers = self.bootstrap()
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload(), format='json').status_code, 403)
        self.assertEqual(self.client.post(f'/api/mesa/{self.mesa.token_uuid}/solicitar-conta/').status_code, 403)
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload(), format='json', **headers).status_code, 201)
        self.assertEqual(self.client.post(f'/api/mesa/{self.mesa.token_uuid}/solicitar-conta/', **headers).status_code, 200)

    def test_csrf_rejects_wrong_token_and_foreign_origin(self):
        headers = self.bootstrap()
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload(), format='json', HTTP_X_CSRFTOKEN='a'*32).status_code, 403)
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload(), format='json', HTTP_ORIGIN='https://example.invalid', **headers).status_code, 403)
        self.assertFalse(Pedido.objects.exists())

    def test_other_table_and_stale_session_are_not_authorized(self):
        headers = self.bootstrap()
        other = Mesa.objects.create(numero=2)
        SessaoMesa.objects.create(mesa=other)
        self.assertEqual(self.client.get(f'/api/mesa/{other.token_uuid}/conta/').status_code, 403)
        services.fechar(self.sessao.pk, self.admin)
        nova = services.abrir(self.mesa.pk, self.admin)
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload(), format='json', **headers).status_code, 403)
        # Mesmo após atualizar o contexto, o pedido antigo não pode cair na sessão nova.
        headers = self.bootstrap()
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload(), format='json', **headers).status_code, 403)
        self.assertFalse(nova.pedidos.exists())

    def test_admin_cannot_edit_session_state_to_bypass_payment(self):
        Pedido.objects.create(sessao=self.sessao)
        client = APIClient()
        client.force_login(self.admin)
        client.post(f'/admin/restaurante/sessaomesa/{self.sessao.pk}/change/', {'ativa': '', 'mesa': self.mesa.pk, '_save': 'Salvar'})
        self.sessao.refresh_from_db()
        self.assertTrue(self.sessao.ativa)
        self.assertFalse(Conta.objects.exists())
        self.assertEqual(client.post(f'/api/sessoes/{self.sessao.pk}/fechar/').status_code, 400)

    def test_qr_download_is_private_png_and_not_saved_in_public_media(self):
        url = f'/api/mesas/{self.mesa.pk}/qr-code/'
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        Image.open(BytesIO(response.content)).verify()
        self.mesa.refresh_from_db()
        self.assertFalse(self.mesa.qr_code)
        self.assertEqual(self.client.get('/media/qrcodes/mesa_1_qrcode.png').status_code, 404)

    def test_negative_prices_rejected_by_api_and_database(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/produtos/', {'categoria': self.produto.categoria_id, 'nome': 'Inválido', 'preco': '-1.00'}, format='json')
        self.assertEqual(response.status_code, 400)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Produto.objects.filter(pk=self.produto.pk).update(preco=-1)

    def test_filters_reject_invalid_dates_and_reverse_interval(self):
        self.client.force_authenticate(self.admin)
        for query in ('data_inicio=nao-e-data', 'data_inicio=2026-10-25&data_fim=2026-10-20'):
            for endpoint in ('pedidos', 'contas'):
                self.assertEqual(self.client.get(f'/api/admin/{endpoint}/?{query}').status_code, 400)

    def test_request_account_after_payment_does_not_reactivate_session(self):
        services.pagar(self.sessao.pk, 'PIX', self.admin)
        from django.http import Http404
        with self.assertRaises(Http404):
            services.pedir_conta(self.mesa.token_uuid, self.sessao.pk)
        self.sessao.refresh_from_db()
        self.assertFalse(self.sessao.ativa)

    def test_admin_role_gets_staff_permissions_without_superuser_and_demotion_revokes(self):
        user = User.objects.create_user('administrador')
        profile = Perfil.objects.create(user=user, role='ADMIN')
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.has_perm('restaurante.change_produto'))
        profile.role = 'COZINHA'
        profile.save()
        user = User.objects.get(pk=user.pk)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.has_perm('restaurante.change_produto'))
