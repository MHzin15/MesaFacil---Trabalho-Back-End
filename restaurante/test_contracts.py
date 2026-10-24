from uuid import uuid4
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Mesa, SessaoMesa, Produto, Categoria, Pedido, HistoricoStatusPedido


class ContractTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1)
        self.sessao = SessaoMesa.objects.create(mesa=self.mesa)
        self.produto = Produto.objects.create(categoria=Categoria.objects.create(nome='Lanches'), nome='Item', preco='32.90')
        self.client = APIClient()
        self.client.get(f'/api/mesa/{self.mesa.token_uuid}/')
        self.payload = {'mesa_uuid': str(self.mesa.token_uuid), 'sessao_id': self.sessao.pk,
            'chave_envio': str(uuid4()), 'itens': [{'produto_id': self.produto.pk, 'quantidade': 1}]}

    def test_retry_same_key_returns_original_order_and_audit_once(self):
        first = self.client.post('/api/pedidos/criar/', self.payload, format='json')
        retry = self.client.post('/api/pedidos/criar/', self.payload, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data['id'], retry.data['id'])
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(HistoricoStatusPedido.objects.count(), 1)
        self.assertEqual(first.data['valor_total'], '32.90')
        self.assertEqual(first.data['itens'][0]['subtotal'], '32.90')

    def test_reusing_key_with_different_payload_is_rejected(self):
        self.client.post('/api/pedidos/criar/', self.payload, format='json')
        self.payload['itens'][0]['quantidade'] = 2
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload, format='json').status_code, 400)
        self.assertEqual(Pedido.objects.count(), 1)

    def test_new_key_allows_multiple_orders_in_same_session(self):
        self.client.post('/api/pedidos/criar/', self.payload, format='json')
        self.payload['chave_envio'] = str(uuid4())
        self.assertEqual(self.client.post('/api/pedidos/criar/', self.payload, format='json').status_code, 201)
        self.assertEqual(self.sessao.pedidos.count(), 2)

    def test_bill_includes_cancelled_orders_without_charging(self):
        response = self.client.post('/api/pedidos/criar/', self.payload, format='json')
        Pedido.objects.filter(pk=response.data['id']).update(status='CANCELADO')
        bill = self.client.get(f'/api/mesa/{self.mesa.token_uuid}/conta/')
        self.assertEqual(bill.data['pedidos'][0]['status'], 'CANCELADO')
        self.assertEqual(bill.data['valor_total'], '0.00')

    def test_no_session_always_returns_list_for_orders(self):
        self.sessao.ativa = False
        self.sessao.save()
        self.client.get(f'/api/mesa/{self.mesa.token_uuid}/')
        self.assertEqual(self.client.get(f'/api/mesa/{self.mesa.token_uuid}/pedidos/').data, [])
