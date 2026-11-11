from .support import conferencia
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.contrib.auth.models import User
from django.db import connection, connections
from django.test import TransactionTestCase
from django.http import Http404
from rest_framework.exceptions import APIException
from ..models import Mesa, SessaoMesa, Perfil, Pedido, HistoricoStatusPedido, Produto, Categoria, Conta
from .. import services


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
            except (APIException, Http404):
                return 'rejeitado'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(functions)) as executor:
            return list(executor.map(worker, functions))

    def test_only_one_concurrent_open_succeeds(self):
        results = self.race([lambda: services.abrir(self.mesa.pk, self.admin)] * 2)
        self.assertCountEqual(results, ['ok', 'rejeitado'])
        self.assertEqual(SessaoMesa.objects.filter(ativa=True).count(), 1)

    def test_simultaneous_first_orders_open_one_session(self):
        from uuid import uuid4
        product = Produto.objects.create(categoria=Categoria.objects.create(nome='Auto'), nome='Item', preco='10.00')
        payloads = [{'mesa_uuid': self.mesa.token_uuid, 'sessao_id': None, 'chave_envio': uuid4(),
            'itens': [{'produto_id': product.pk, 'quantidade': 1}]} for _ in range(2)]
        generation = str(uuid4())
        Mesa.objects.filter(pk=self.mesa.pk).update(responsavel_uuid=generation)
        self.assertEqual(self.race([lambda: services.criar(payloads[0], self.admin, geracao=generation),
                                   lambda: services.criar(payloads[1], self.admin, geracao=generation)]), ['ok', 'ok'])
        self.assertEqual(SessaoMesa.objects.filter(mesa=self.mesa, ativa=True).count(), 1)
        self.assertEqual(Pedido.objects.count(), 2)

    def test_simultaneous_first_order_retries_create_one_order(self):
        from uuid import uuid4
        product = Produto.objects.create(categoria=Categoria.objects.create(nome='Auto'), nome='Item', preco='10.00')
        data = {'mesa_uuid': self.mesa.token_uuid, 'sessao_id': None, 'chave_envio': uuid4(),
            'itens': [{'produto_id': product.pk, 'quantidade': 1}]}
        generation = str(uuid4())
        Mesa.objects.filter(pk=self.mesa.pk).update(responsavel_uuid=generation)
        self.assertEqual(self.race([lambda: services.criar(data, self.admin, geracao=generation)] * 2), ['ok', 'ok'])
        self.assertEqual(SessaoMesa.objects.filter(mesa=self.mesa, ativa=True).count(), 1)
        self.assertEqual(Pedido.objects.count(), 1)

    def test_another_family_cannot_create_account_during_simultaneous_orders(self):
        from uuid import uuid4
        product = Produto.objects.create(categoria=Categoria.objects.create(nome='Auto'), nome='Item', preco='10.00')
        data = {'mesa_uuid': self.mesa.token_uuid, 'sessao_id': None,
            'itens': [{'produto_id': product.pk, 'quantidade': 1}]}
        keys = [str(uuid4()), str(uuid4())]
        Mesa.objects.filter(pk=self.mesa.pk).update(responsavel_uuid=keys[0])
        self.assertEqual(self.race([lambda: services.criar(data, self.admin, geracao=keys[0]),
                                   lambda: services.criar(data, self.admin, geracao=keys[1])]), ['ok', 'rejeitado'])
        self.assertEqual(SessaoMesa.objects.filter(mesa=self.mesa, ativa=True).count(), 1)
        self.assertEqual(Pedido.objects.values('sessao_id').distinct().count(), 1)

    def test_same_transition_runs_once_with_one_audit_event(self):
        pedido = Pedido.objects.create(sessao=services.abrir(self.mesa.pk, self.admin))
        results = self.race([lambda: services.transitar(pedido.pk, 'EM_PREPARACAO', self.admin)] * 2)
        self.assertCountEqual(results, ['ok', 'rejeitado'])
        self.assertEqual(HistoricoStatusPedido.objects.filter(pedido=pedido).count(), 1)

    def test_order_racing_payment_cannot_create_unpaid_order_in_closed_session(self):
        sessao = services.abrir(self.mesa.pk, self.admin)
        product = Produto.objects.create(categoria=Categoria.objects.create(nome='Lanches'), nome='Item', preco='10.00')
        data = {'mesa_uuid': self.mesa.token_uuid, 'sessao_id': sessao.pk, 'itens': [{'produto_id': product.pk, 'quantidade': 1}]}
        snapshot = conferencia(sessao)
        results = self.race([lambda: services.criar(data, self.admin), lambda: services.pagar(sessao.pk, 'PIX', self.admin, **snapshot)])
        self.assertCountEqual(results, ['ok', 'rejeitado'])
        sessao.refresh_from_db()
        if not sessao.ativa:
            self.assertTrue(Conta.objects.get(sessao=sessao).pago)
            self.assertFalse(sessao.pedidos.exists())
        else:
            self.assertFalse(Conta.objects.exists())
            self.assertEqual(sessao.pedidos.count(), 1)

    def test_request_account_racing_payment_never_reopens_paid_session(self):
        sessao = services.abrir(self.mesa.pk, self.admin)
        snapshot = conferencia(sessao)
        results = self.race([
            lambda: services.pedir_conta(self.mesa.token_uuid, sessao.pk),
            lambda: services.pagar(sessao.pk, 'PIX', self.admin, **snapshot),
        ])
        self.assertIn('ok', results)
        sessao.refresh_from_db()
        if sessao.ativa:
            services.pagar(sessao.pk, 'PIX', self.admin, **conferencia(sessao))
            sessao.refresh_from_db()
        self.assertFalse(sessao.ativa)
        self.assertFalse(sessao.conta_solicitada)
        self.assertTrue(Conta.objects.get(sessao=sessao).pago)

    def test_duplicate_submission_race_creates_one_order_and_one_initial_event(self):
        from uuid import uuid4
        sessao = services.abrir(self.mesa.pk, self.admin)
        product = Produto.objects.create(categoria=Categoria.objects.create(nome='Lanches'), nome='Item', preco='10.00')
        data = {'mesa_uuid': self.mesa.token_uuid, 'sessao_id': sessao.pk, 'chave_envio': uuid4(),
                'itens': [{'produto_id': product.pk, 'quantidade': 1}]}
        self.assertEqual(self.race([lambda: services.criar(data, self.admin)] * 2), ['ok', 'ok'])
        self.assertEqual(Pedido.objects.filter(sessao=sessao).count(), 1)
        self.assertEqual(HistoricoStatusPedido.objects.count(), 1)

    def test_login_limit_is_atomic_across_workers(self):
        from django.test import RequestFactory
        from rest_framework.exceptions import PermissionDenied
        from .middleware import LoginRateLimit

        def attempt():
            request = RequestFactory().post('/entrar/', {'username': 'concorrencia'})
            response = LoginRateLimit(lambda request: None).process_view(request, None, (), {})
            if response is not None and response.status_code == 429:
                raise PermissionDenied()

        with self.settings(LOGIN_RATE_LIMIT_ACCOUNT=1, LOGIN_RATE_LIMIT_IP=10):
            self.assertCountEqual(self.race([attempt, attempt]), ['ok', 'rejeitado'])
