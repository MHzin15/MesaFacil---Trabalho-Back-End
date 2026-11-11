"""Escolhas, conferência operacional e continuidade de edição da UI real."""
import json
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .. import services
from ..models import Adicional, Categoria, ItemPedido, ItemPedidoAdicional, Mesa, Pedido, Perfil, Produto, SessaoMesa
from ..opcoes import escolhas_exemplo, validar_grupos_opcoes


class EscolhasEOperacaoTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1)
        self.produto = Produto.objects.create(nome='Água Mineral', preco='5.90',
            categoria=Categoria.objects.create(nome='Bebidas'), grupos_opcoes=escolhas_exemplo('Água Mineral'))
        self.gestor = User.objects.create_user('gestor-ux')
        Perfil.objects.create(user=self.gestor, role='ADMIN')
        self.garcom = User.objects.create_user('garcom-ux')
        Perfil.objects.create(user=self.garcom, role='GARCOM')
        self.api = APIClient()
        self.api.get(f'/mesa/{self.mesa.token_uuid}/')
        self.base = f'/api/mesa/{self.mesa.token_uuid}/'
        self.contexto = self.api.get(self.base).data

    def escolher(self, produto=None):
        group = (produto or self.produto).grupos_opcoes[0]
        return {'grupo_id': group['id'], 'opcao_id': group['opcoes'][0]['id']}

    def dados(self, **item):
        return {'mesa_uuid': str(self.mesa.token_uuid), 'sessao_id': None,
                'atendimento_id': self.contexto['atendimento_id'], 'chave_envio': str(uuid4()),
                'total_esperado': '5.90', 'itens': [{'produto_id': self.produto.pk, 'quantidade': 1,
                'opcoes': [self.escolher()], 'opcoes_versao': self.produto.opcoes_versao, **item}]}

    def test_choice_required_foreign_unknown_or_duplicate_rolls_back_first_order(self):
        foreign = self.escolher()
        foreign['opcao_id'] = str(uuid4())
        for choices in ([], [foreign], [self.escolher(), self.escolher()],
                        [{'grupo_id': str(uuid4()), 'opcao_id': str(uuid4())}]):
            with self.subTest(choices=choices):
                response = self.api.post('/api/pedidos/criar/', self.dados(opcoes=choices), format='json')
                self.assertEqual(response.status_code, 400, response.data)
                self.assertFalse(Pedido.objects.exists())
                self.assertFalse(SessaoMesa.objects.exists())

    def test_snapshot_and_idempotency_survive_catalog_change_without_new_cost(self):
        data = self.dados()
        response = self.api.post('/api/pedidos/criar/', data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['itens'][0]['opcoes'][0]['opcao'], 'Sem gás')
        self.assertEqual(response.data['valor_total'], '5.90')
        self.produto.grupos_opcoes = []
        self.produto.preco = '9.00'
        self.produto.save()
        replay = self.api.post('/api/pedidos/criar/', data, format='json')
        self.assertIn(replay.status_code, (200, 201), replay.data)
        self.assertEqual(replay.data['id'], response.data['id'])
        self.assertEqual(replay.data['itens'][0]['opcoes'], response.data['itens'][0]['opcoes'])
        self.assertEqual(Pedido.objects.count(), 1)

    def test_optional_group_and_unconfigured_product_keep_existing_order_flow(self):
        self.produto.grupos_opcoes[0]['obrigatorio'] = False
        self.produto.save()
        self.assertEqual(self.api.post('/api/pedidos/criar/', self.dados(opcoes=[]), format='json').status_code, 201)

    def test_renamed_choice_after_review_requires_new_review_even_at_same_price(self):
        data = self.dados()
        self.produto.grupos_opcoes[0]['opcoes'][0]['nome'] = 'Água com gás'
        self.produto.save()
        response = self.api.post('/api/pedidos/criar/', data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(SessaoMesa.objects.exists())

    def test_options_configuration_rejects_unbounded_and_invalid_payloads(self):
        for payload in ({}, [{'id': str(uuid4())}], self.produto.grupos_opcoes * 7,
                        [{'id': str(uuid4()), 'nome': 'Tipo', 'obrigatorio': True, 'opcoes': []}]):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                validar_grupos_opcoes(payload)
        self.api.force_authenticate(self.gestor)
        self.assertEqual(self.api.patch(f'/api/produtos/{self.produto.pk}/', {'grupos_opcoes': [{}]}, format='json').status_code, 400)

    def test_bill_queue_aggregates_without_multiplying_base_and_tracks_request_time(self):
        sessao = SessaoMesa.objects.create(mesa=self.mesa)
        order = Pedido.objects.create(sessao=sessao, status='ENTREGUE')
        item = ItemPedido.objects.create(pedido=order, produto=self.produto, quantidade=2, preco_unitario='5.90')
        for name, price in [('A', '1.00'), ('B', '2.00')]:
            extra = Adicional.objects.create(produto=self.produto, nome=name, preco=price)
            ItemPedidoAdicional.objects.create(item_pedido=item, adicional=extra, preco=price)
        Pedido.objects.create(sessao=sessao, status='RECEBIDO')
        requested = services.pedir_conta(self.mesa.token_uuid, sessao.pk)
        date = requested.conta_solicitada_em
        self.assertIsNotNone(date)
        self.assertEqual(services.pedir_conta(self.mesa.token_uuid, sessao.pk).conta_solicitada_em, date)
        summary = SessaoMesa.objects.com_resumo().get(pk=sessao.pk)
        self.assertEqual(summary.valor_total, Decimal('17.80'))
        self.assertEqual(summary.pedidos_pendentes, 1)
        self.api.force_authenticate(self.garcom)
        entry = self.api.get('/api/garcom/').data['comandas_aguardando_conta'][0]
        self.assertEqual((entry['valor_total'], entry['pedidos_pendentes']), ('17.80', 1))
        services.retomar(sessao.pk, self.garcom)
        sessao.refresh_from_db()
        self.assertIsNone(sessao.conta_solicitada_em)

    def test_product_editor_and_price_return_to_filtered_list_without_open_redirect(self):
        self.client.force_login(self.gestor)
        next_url = '/admin/cardapio/?q=%C3%81gua&categoria=1&page=2'
        url = f'/admin/cardapio/{self.produto.pk}/preco/'
        response = self.client.post(url, {'preco': '6.90', 'anterior': '5.90', 'retorno': next_url})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], next_url + f'#produto-{self.produto.pk}')
        for bad in ('https://example.org/', '//example.org/', '/admin/equipe/', 'http://[bad'):
            result = self.client.post(url, {'preco': '6.90', 'anterior': '6.90', 'retorno': bad})
            self.assertEqual(result['Location'], '/admin/cardapio/')
        response = self.client.get(f'/admin/cadastro/produtos/{self.produto.pk}/')
        self.assertContains(response, 'data-photo-preview')
        self.assertContains(response, 'data-options-editor')
        groups = self.produto.grupos_opcoes
        data = {'nome': self.produto.nome, 'categoria': self.produto.categoria_id,
                'preco': '6.90', 'preco_anterior': '6.90', 'disponivel': 'on'}
        self.assertEqual(self.client.post(f'/admin/cadastro/produtos/{self.produto.pk}/', data).status_code, 302)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.grupos_opcoes, groups)
        data['grupos_opcoes'] = json.dumps([])
        self.client.post(f'/admin/cadastro/produtos/{self.produto.pk}/', data)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.grupos_opcoes, [])
