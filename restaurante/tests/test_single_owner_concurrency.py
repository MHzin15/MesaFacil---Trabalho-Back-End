"""Dois leitores simultâneos não podem assumir a mesma mesa."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from ..models import Mesa, SessaoMesa


@skipUnless(connection.vendor == 'postgresql', 'Locks reais exigem PostgreSQL')
class SingleOwnerConcurrencyTests(TransactionTestCase):
    def test_simultaneous_qr_readers_get_exactly_one_owner(self):
        mesa = Mesa.objects.create(numero=1)
        barrier = Barrier(2)
        def visit(_):
            connections.close_all()
            try:
                client = APIClient()
                barrier.wait(timeout=10)
                result = client.get(f'/mesa/{mesa.token_uuid}/')
                assert result.status_code == 200
                data = client.get(f'/api/mesa/{mesa.token_uuid}/').data
                return data['acesso_liberado'], data['mesa_em_uso'], data['atendimento_id']
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(visit, range(2)))
        self.assertEqual(sum(r[0] for r in results),1)
        self.assertEqual(sum(r[1] for r in results),1)
        mesa.refresh_from_db()
        self.assertEqual([r[2] for r in results if r[0]], [str(mesa.responsavel_uuid)])
        self.assertEqual(SessaoMesa.objects.count(),0)
