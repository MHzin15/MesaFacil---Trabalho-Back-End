from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Mesa, SessaoMesa, Categoria, Produto, Adicional, Pedido, ItemPedido, Conta, Perfil
from . import services


class WaiterTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1)
        self.admin = User.objects.create_user('gestor')
        Perfil.objects.create(user=self.admin, role='ADMIN')
        self.garcom = User.objects.create_user('garcom')
        Perfil.objects.create(user=self.garcom, role='GARCOM')
        self.cozinha = User.objects.create_user('cozinha')
        Perfil.objects.create(user=self.cozinha, role='COZINHA')
        self.produto = Produto.objects.create(categoria=Categoria.objects.create(nome='Lanches'), nome='Hambúrguer', preco='32.90')
        self.addon = Adicional.objects.create(produto=self.produto, nome='Bacon', preco='5.00')
        self.client = APIClient()

    def test_waiter_page_and_staff_bill_require_correct_profile(self):
        sessao = services.abrir(self.mesa.pk, self.garcom)
        self.assertEqual(self.client.get('/garcom/').status_code, 302)
        self.client.force_login(self.cozinha)
        self.assertEqual(self.client.get('/garcom/').status_code, 403)
        self.assertEqual(self.client.get(f'/api/sessoes/{sessao.pk}/conta/').status_code, 403)
        self.client.force_login(self.garcom)
        self.assertContains(self.client.get('/garcom/'), 'Confirmar pagamento simulado')
        self.assertEqual(self.client.get('/painel/')['Location'], '/garcom/')
        self.assertEqual(self.client.get(f'/api/sessoes/{sessao.pk}/conta/').status_code, 200)

    def test_complete_guest_kitchen_waiter_checkout_flow(self):
        self.client.force_authenticate(self.garcom)
        opened = self.client.post(f'/api/mesas/{self.mesa.pk}/abrir-sessao/')
        self.assertEqual(opened.status_code, 201)
        guest = APIClient(enforce_csrf_checks=True)
        guest.get(f'/api/mesa/{self.mesa.token_uuid}/')
        csrf = {'HTTP_X_CSRFTOKEN': guest.cookies['csrftoken'].value}
        created = guest.post('/api/pedidos/criar/', {'mesa_uuid': str(self.mesa.token_uuid), 'sessao_id': opened.data['id'],
            'itens': [{'produto_id': self.produto.pk, 'quantidade': 2, 'adicionais_ids': [self.addon.pk]}]}, format='json', **csrf)
        self.assertEqual(created.status_code, 201)
        pedido_id = created.data['id']
        self.client.force_authenticate(self.cozinha)
        self.assertEqual(self.client.get('/api/cozinha/').data['RECEBIDO'][0]['id'], pedido_id)
        for state in ('EM_PREPARACAO', 'PRONTO'):
            self.assertEqual(self.client.patch(f'/api/pedidos/{pedido_id}/status/', {'status': state}, format='json').status_code, 200)
        self.client.force_authenticate(self.garcom)
        self.assertEqual(self.client.get('/api/garcom/').data['pedidos_prontos'][0]['id'], pedido_id)
        for state in ('A_CAMINHO', 'ENTREGUE'):
            self.assertEqual(self.client.patch(f'/api/pedidos/{pedido_id}/status/', {'status': state}, format='json').status_code, 200)
        self.assertEqual(guest.post(f'/api/mesa/{self.mesa.token_uuid}/solicitar-conta/', **csrf).status_code, 200)
        self.assertEqual(self.client.get('/api/garcom/').data['mesas_aguardando_conta'][0]['id'], self.mesa.pk)
        bill = self.client.get(f'/api/sessoes/{opened.data["id"]}/conta/')
        self.assertEqual(bill.data['valor_total'], '75.80')
        paid = self.client.post(f'/api/sessoes/{opened.data["id"]}/pagamento/', {'meio_pagamento': 'PIX'}, format='json')
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(self.client.get('/api/garcom/mapa-mesas/').data[0]['status'], 'livre')
        self.assertFalse(SessaoMesa.objects.get(pk=opened.data['id']).ativa)

    def test_all_payment_methods_and_repeat_protection(self):
        self.client.force_authenticate(self.garcom)
        for number, method in enumerate(('PIX', 'CARTAO', 'DINHEIRO'), 2):
            with self.subTest(method=method):
                mesa = Mesa.objects.create(numero=number)
                sessao = services.abrir(mesa.pk, self.garcom)
                pedido = Pedido.objects.create(sessao=sessao, status='ENTREGUE')
                ItemPedido.objects.create(pedido=pedido, produto=self.produto, preco_unitario='32.90')
                cancelled = Pedido.objects.create(sessao=sessao, status='CANCELADO')
                ItemPedido.objects.create(pedido=cancelled, produto=self.produto, preco_unitario='90.00')
                url = f'/api/sessoes/{sessao.pk}/pagamento/'
                self.assertEqual(self.client.post(url, {'meio_pagamento': method}, format='json').status_code, 200)
                self.assertEqual(Conta.objects.get(sessao=sessao).valor_total, Decimal('32.90'))
                self.assertEqual(self.client.post(url, {'meio_pagamento': method}, format='json').status_code, 400)
                self.assertEqual(Conta.objects.filter(sessao=sessao).count(), 1)

    def test_every_pending_state_blocks_payment_and_invalid_method_is_rejected(self):
        sessao = services.abrir(self.mesa.pk, self.garcom)
        pedido = Pedido.objects.create(sessao=sessao)
        self.client.force_authenticate(self.garcom)
        url = f'/api/sessoes/{sessao.pk}/pagamento/'
        for state in ('RECEBIDO', 'EM_PREPARACAO', 'PRONTO', 'A_CAMINHO'):
            Pedido.objects.filter(pk=pedido.pk).update(status=state)
            self.assertEqual(self.client.post(url, {'meio_pagamento': 'PIX'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'meio_pagamento': 'BOLETO'}, format='json').status_code, 400)
        self.assertFalse(Conta.objects.exists())

    def test_zero_bill_close_and_request_by_waiter(self):
        self.client.force_authenticate(self.garcom)
        sessao = services.abrir(self.mesa.pk, self.garcom)
        self.assertEqual(self.client.post(f'/api/sessoes/{sessao.pk}/solicitar-conta/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/sessoes/{sessao.pk}/fechar/').status_code, 200)
        new = services.abrir(self.mesa.pk, self.garcom)
        Pedido.objects.create(sessao=new, status='CANCELADO')
        self.assertEqual(self.client.post(f'/api/sessoes/{new.pk}/fechar/').status_code, 200)

    def test_payment_failure_rolls_back_account_and_session(self):
        sessao = services.abrir(self.mesa.pk, self.garcom)
        with patch('restaurante.services.encerrar', side_effect=RuntimeError('falha simulada')):
            with self.assertRaises(RuntimeError):
                services.pagar(sessao.pk, 'PIX', self.garcom)
        sessao.refresh_from_db()
        self.assertTrue(sessao.ativa)
        self.assertFalse(Conta.objects.exists())
