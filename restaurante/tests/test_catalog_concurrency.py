"""Regressão de lock entre envio de pedido e edição de adicional no PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest import skipUnless

from django.contrib.auth.models import User
from django.db import connection, connections
from django.db.models.signals import post_save
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from restaurante import services
from restaurante.models import Adicional, Categoria, Mesa, Perfil, Produto, SessaoMesa


@skipUnless(connection.vendor == 'postgresql', 'Prova de locks exige PostgreSQL')
class CatalogConcurrencyTests(TransactionTestCase):
    def test_editing_addon_during_order_keeps_fk_and_snapshots_consistent(self):
        admin = User.objects.create_user('gestor-locks-forense')
        Perfil.objects.create(user=admin, role='ADMIN')
        mesa = Mesa.objects.create(numero=1)
        sessao = services.abrir(mesa.pk, admin)
        categoria = Categoria.objects.create(nome='Forense')
        a = Produto.objects.create(categoria=categoria, nome='A', preco='10.00')
        b = Produto.objects.create(categoria=categoria, nome='B', preco='10.00')
        adicional = Adicional.objects.create(produto=a, nome='Extra', preco='1.00')
        client = APIClient()
        client.force_login(admin)
        products_locked, addon_updated = Event(), Event()
        uid = 'forense-lock-adicional'

        def addon_saved(sender, instance, **kwargs):
            if instance.pk == adicional.pk:
                addon_updated.set()

        def hook(execute, sql, params, many, context):
            result = execute(sql, params, many, context)
            if 'FROM "restaurante_produto"' in sql and ('FOR UPDATE' in sql or 'FOR NO KEY UPDATE' in sql):
                products_locked.set()
                if not addon_updated.wait(15):
                    raise TimeoutError('A edição não chegou ao UPDATE do adicional.')
            return result

        def order():
            connections.close_all()
            try:
                with connection.execute_wrapper(hook):
                    services.criar({'mesa_uuid': mesa.token_uuid, 'sessao_id': sessao.pk,
                        'itens': [{'produto_id': a.pk, 'quantidade': 1, 'adicionais_ids': [adicional.pk]},
                                  {'produto_id': b.pk, 'quantidade': 1}]}, admin)
                return 'ok'
            except Exception as exc:
                return f'{type(exc).__name__}: {exc}'
            finally:
                connections.close_all()

        def edit():
            connections.close_all()
            try:
                if not products_locked.wait(15):
                    raise TimeoutError('O pedido não adquiriu os locks de produto.')
                response = client.post(f'/admin/cadastro/adicionais/{adicional.pk}/',
                    {'produto': b.pk, 'nome': adicional.nome, 'preco': '1.00'})
                return 'ok' if response.status_code == 302 else f'http:{response.status_code}'
            except Exception as exc:
                return f'{type(exc).__name__}: {exc}'
            finally:
                connections.close_all()

        post_save.connect(addon_saved, sender=Adicional, dispatch_uid=uid, weak=False)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(order), pool.submit(edit)]
                results = [future.result(timeout=30) for future in futures]
        finally:
            post_save.disconnect(sender=Adicional, dispatch_uid=uid)
        self.assertEqual(results[1], 'ok', results)
        self.assertTrue(results[0].startswith('Http404:'), results)
        adicional.refresh_from_db()
        self.assertEqual(adicional.produto_id, b.pk)
        self.assertFalse(sessao.pedidos.exists())
