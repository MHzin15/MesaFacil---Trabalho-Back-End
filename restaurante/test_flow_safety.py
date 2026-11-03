"""Regressões do isolamento por atendimento e conferência do fechamento."""
from decimal import Decimal
from uuid import uuid4
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient
from . import services
from .models import Categoria, Conta, Mesa, Pedido, Perfil, Produto
from .test_support import entrar_cliente, conferencia


class FlowSafetyTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('gestor-fluxos')
        Perfil.objects.create(user=self.admin, role='ADMIN')
        self.garcom = User.objects.create_user('garcom-fluxos')
        Perfil.objects.create(user=self.garcom, role='GARCOM')
        self.mesa = Mesa.objects.create(numero=1)
        self.sessao = services.abrir(self.mesa.pk, self.admin)
        self.produto = Produto.objects.create(categoria=Categoria.objects.create(nome='Teste'), nome='Item', preco='10.00')
        self.client = APIClient(enforce_csrf_checks=True)
        self.base = f'/api/mesa/{self.mesa.token_uuid}/'

    def payload(self):
        return {'mesa_uuid': str(self.mesa.token_uuid), 'sessao_id': self.sessao.pk,
            'chave_envio': uuid4(), 'itens': [{'produto_id': self.produto.pk, 'quantidade': 1}]}

    def test_first_visit_has_no_code_or_staff_approval(self):
        html = self.client.get(f'/mesa/{self.mesa.token_uuid}/')
        self.assertNotContains(html, 'codigo-atendimento')
        self.assertTrue(self.client.get(self.base).data['acesso_liberado'])
        self.assertEqual(self.client.get(self.base + 'conta/').status_code, 404)

    def test_closed_browser_does_not_migrate_until_explicit_new_visit(self):
        entrar_cliente(self.client, self.mesa)
        services.fechar(self.sessao.pk, self.admin)
        nova = services.abrir(self.mesa.pk, self.admin)
        for _ in range(2):
            self.client.get(f'/mesa/{self.mesa.token_uuid}/')
            context = self.client.get(self.base).data
            self.assertFalse(context['acesso_liberado'])
            self.assertTrue(context['atendimento_encerrado'])
            self.assertEqual(self.client.get(self.base + 'conta/').status_code, 403)
        self.sessao = nova
        headers = {'HTTP_X_CSRFTOKEN': self.client.cookies['csrftoken'].value}
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload(), format='json', **headers).status_code, 403)
        # Novo atendimento é uma escolha do cliente, sem envolver o garçom.
        self.assertEqual(self.client.post(self.base + 'novo-atendimento/').status_code, 403)
        self.assertEqual(self.client.post(self.base + 'novo-atendimento/', **headers).status_code, 200)
        self.assertTrue(self.client.get(self.base).data['acesso_liberado'])

    def test_first_order_opens_session_and_invalid_order_rolls_back_opening(self):
        services.fechar(self.sessao.pk, self.admin)
        self.client.get(f'/mesa/{self.mesa.token_uuid}/')
        headers = {'HTTP_X_CSRFTOKEN': self.client.cookies['csrftoken'].value}
        data = self.payload()
        data['sessao_id'] = None
        data['atendimento_id'] = self.client.get(self.base).data['atendimento_id']
        data['itens'][0]['produto_id'] = 9999999
        self.assertEqual(self.client.post('/api/pedidos/criar/', data, format='json', **headers).status_code, 404)
        self.assertIsNone(Mesa.objects.get(pk=self.mesa.pk).sessao_ativa)
        data['itens'][0]['produto_id'] = self.produto.pk
        response = self.client.post('/api/pedidos/criar/', data, format='json', **headers)
        self.assertEqual(response.status_code, 201)
        retry = self.client.post('/api/pedidos/criar/', data, format='json', **headers)
        self.assertEqual(retry.data['id'], response.data['id'])
        self.assertIsNone(Pedido.objects.get(pk=response.data['id']).sessao.aberta_por)

    def test_two_customers_start_separate_commands_without_invitation(self):
        services.fechar(self.sessao.pk, self.admin)
        other = APIClient(enforce_csrf_checks=True)
        for client in (self.client, other):
            client.get(f'/mesa/{self.mesa.token_uuid}/')
            self.assertTrue(client.get(self.base).data['acesso_liberado'])
            data = self.payload()
            data['sessao_id'] = None
            data['atendimento_id'] = client.get(self.base).data['atendimento_id']
            response = client.post('/api/pedidos/criar/', data, format='json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
            self.assertEqual(response.status_code, 201)
        self.assertEqual(Pedido.objects.values('sessao_id').distinct().count(), 2)

    def test_old_generation_cannot_open_new_session_from_service(self):
        generation = str(self.sessao.acesso_uuid)
        services.fechar(self.sessao.pk, self.admin)
        with self.assertRaises(ValidationError):
            services.criar(self.payload(), self.admin, geracao=generation)
        self.assertIsNone(Mesa.objects.get(pk=self.mesa.pk).sessao_ativa)

    def test_closing_blocks_new_orders_but_accepts_retry_of_received_order(self):
        data = self.payload()
        pedido = services.criar(data, self.admin)
        services.pedir_conta(self.mesa.token_uuid, self.sessao.pk)
        self.assertEqual(services.criar(data, self.admin).pk, pedido.pk)
        with self.assertRaises(ValidationError):
            services.criar(self.payload(), self.admin)
        self.assertEqual(Pedido.objects.count(), 1)
        staff = APIClient()
        staff.force_authenticate(self.garcom)
        self.assertEqual(staff.post(f'/api/sessoes/{self.sessao.pk}/retomar/').status_code, 200)
        services.criar(self.payload(), self.admin)
        self.assertEqual(Pedido.objects.count(), 2)
        self.assertIn('retomado', LogEntry.objects.latest('pk').change_message)

    def test_customer_cannot_resume_and_cannot_create_via_api_during_closing(self):
        entrar_cliente(self.client, self.mesa)
        services.pedir_conta(self.mesa.token_uuid, self.sessao.pk)
        headers = {'HTTP_X_CSRFTOKEN': self.client.cookies['csrftoken'].value}
        self.assertEqual(self.client.post(f'/api/sessoes/{self.sessao.pk}/retomar/', **headers).status_code, 403)
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload(), format='json', **headers).status_code, 400)

    def test_payment_requires_snapshot_and_rejects_changed_version_even_same_total(self):
        staff = APIClient()
        staff.force_authenticate(self.garcom)
        snapshot = conferencia(self.sessao)
        url = f'/api/sessoes/{self.sessao.pk}/pagamento/'
        self.assertEqual(staff.post(url, {'meio_pagamento': 'PIX'}, format='json').status_code, 400)
        services.pedir_conta(self.mesa.token_uuid, self.sessao.pk)
        self.assertEqual(staff.post(url, {'meio_pagamento': 'PIX', **snapshot}, format='json').status_code, 400)
        self.assertFalse(Conta.objects.exists())
        snapshot = conferencia(self.sessao)
        self.assertEqual(staff.post(url, {'meio_pagamento': 'PIX', **snapshot, 'total_esperado': '1.00'}, format='json').status_code, 400)
        response = staff.post(url, {'meio_pagamento': 'PIX', **snapshot}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Conta.objects.get(sessao=self.sessao).pago)

    def test_manager_exception_requires_reason_and_records_original_status(self):
        pedido = services.criar(self.payload(), self.admin)
        services.transitar(pedido.pk, 'EM_PREPARACAO', self.admin)
        with self.assertRaises(PermissionDenied):
            services.cancelar_excepcional(pedido.pk, 'Produto impróprio para consumo', self.garcom)
        with self.assertRaises(ValidationError):
            services.cancelar_excepcional(pedido.pk, 'erro', self.admin)
        services.cancelar_excepcional(pedido.pk, 'Produto impróprio para consumo', self.admin)
        pedido.refresh_from_db()
        evento = pedido.historico_status.latest('pk')
        self.assertEqual(pedido.status, 'CANCELADO')
        self.assertEqual(evento.status_anterior, 'EM_PREPARACAO')
        self.assertEqual(evento.alterado_por, self.admin)
        self.assertEqual(evento.motivo, 'Produto impróprio para consumo')
        self.assertEqual(self.sessao.total_consumo(), Decimal('0'))
        self.assertIn('Cancelamento excepcional', LogEntry.objects.latest('pk').change_message)

    def test_exception_cannot_change_paid_or_closed_account(self):
        pedido = services.criar(self.payload(), self.admin)
        for status in ('EM_PREPARACAO', 'PRONTO', 'A_CAMINHO', 'ENTREGUE'):
            services.transitar(pedido.pk, status, self.admin)
        services.pagar(self.sessao.pk, 'PIX', self.admin, **conferencia(self.sessao))
        with self.assertRaises(ValidationError):
            services.cancelar_excepcional(pedido.pk, 'Solicitação posterior ao pagamento', self.admin)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, 'ENTREGUE')

    def test_manager_exception_form_and_history_escape_reason(self):
        pedido = services.criar(self.payload(), self.admin)
        self.client.force_login(self.admin)
        url = f'/admin/pedidos/{pedido.pk}/cancelar-excepcional/'
        self.assertContains(self.client.get(url), 'Justificativa do cancelamento')
        self.assertEqual(self.client.post(url, {'motivo': '<script>alert(1)</script>'},
            HTTP_X_CSRFTOKEN=self.client.cookies['csrftoken'].value).status_code, 302)
        history = self.client.get(f'/admin/pedidos/{pedido.pk}/')
        self.assertContains(history, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.client.force_login(self.garcom)
        self.assertEqual(self.client.get(url).status_code, 403)
