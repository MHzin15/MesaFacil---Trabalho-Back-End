from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.contrib.auth.models import User
from django.db import connection, connections
from django.test import TransactionTestCase
from rest_framework.exceptions import APIException
from .models import Mesa, SessaoMesa, Perfil, Pedido, HistoricoStatusPedido, Produto, Categoria, Conta
from . import services


@skipUnless(connection.vendor == 'postgresql', 'Locks reais exigem PostgreSQL')
class ConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.admin = User.objects.create_user('concorrencia')
        Perfil.objects.create(user=self.admin, role='ADMIN')
        self.mesa = Mesa.objects.create(numero=1)

    def race(self, functions):
        barrier = Barrier(len(functions))
        def worker(function):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                function()
                return 'ok'
            except APIException:
                return 'rejeitado'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(functions)) as executor:
            return list(executor.map(worker, functions))

    def test_only_one_concurrent_open_succeeds(self):
        results = self.race([lambda: services.abrir(self.mesa.pk, self.admin)] * 2)
        self.assertCountEqual(results, ['ok', 'rejeitado'])
        self.assertEqual(SessaoMesa.objects.filter(ativa=True).count(), 1)

    def test_same_transition_runs_once_with_one_audit_event(self):
        pedido = Pedido.objects.create(sessao=services.abrir(self.mesa.pk, self.admin))
        results = self.race([lambda: services.transitar(pedido.pk, 'EM_PREPARACAO', self.admin)] * 2)
        self.assertCountEqual(results, ['ok', 'rejeitado'])
        self.assertEqual(HistoricoStatusPedido.objects.filter(pedido=pedido).count(), 1)

    def test_order_racing_payment_cannot_create_unpaid_order_in_closed_session(self):
        sessao = services.abrir(self.mesa.pk, self.admin)
        product = Produto.objects.create(categoria=Categoria.objects.create(nome='Lanches'), nome='Item', preco='10.00')
        data = {'mesa_uuid': self.mesa.token_uuid, 'sessao_id': sessao.pk, 'itens': [{'produto_id': product.pk, 'quantidade': 1}]}
        results = self.race([lambda: services.criar(data, self.admin), lambda: services.pagar(sessao.pk, 'PIX', self.admin)])
        self.assertCountEqual(results, ['ok', 'rejeitado'])
        sessao.refresh_from_db()
        if not sessao.ativa:
            self.assertTrue(Conta.objects.get(sessao=sessao).pago)
            self.assertFalse(sessao.pedidos.exists())
        else:
            self.assertFalse(Conta.objects.exists())
            self.assertEqual(sessao.pedidos.count(), 1)
