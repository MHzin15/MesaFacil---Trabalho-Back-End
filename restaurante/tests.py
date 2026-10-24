from decimal import Decimal
from datetime import timedelta
from itertools import product
from unittest.mock import patch, PropertyMock
from uuid import uuid4
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from restaurante.models import (
    Perfil, Mesa, SessaoMesa, Categoria, Produto, Adicional,
    Pedido, ItemPedido, ItemPedidoAdicional, HistoricoStatusPedido, Conta,
)


class MesaFacilRegrasNegocioTestCase(TestCase):
    """
    Testes automatizados cobrindo as Regras de Negócio Críticas (RN01 a RN10)
    e requisitos não-funcionais de integridade (RNF08).
    """

    def setUp(self):
        self.client = APIClient()

        # Criação de usuários da equipe
        self.user_admin = User.objects.create_user(username='admin_test', first_name='Admin')
        Perfil.objects.create(user=self.user_admin, role='ADMIN')

        self.user_cozinha = User.objects.create_user(username='cozinha_test', first_name='Cozinheiro')
        Perfil.objects.create(user=self.user_cozinha, role='COZINHA')

        self.user_garcom = User.objects.create_user(username='garcom_test', first_name='Garçom')
        Perfil.objects.create(user=self.user_garcom, role='GARCOM')

        # Criação de Mesa
        self.mesa = Mesa.objects.create(numero=1, ativa=True)

        # Criação de Cardápio
        self.cat_lanches = Categoria.objects.create(nome='Lanches', ordem=1)
        self.produto_hamburguer = Produto.objects.create(
            categoria=self.cat_lanches,
            nome='Hambúrguer Clássico',
            descricao='Pão brioche e blend 180g',
            preco=Decimal('32.90'),
            disponivel=True,
        )
        self.adicional_bacon = Adicional.objects.create(
            produto=self.produto_hamburguer,
            nome='Bacon',
            preco=Decimal('5.00'),
        )
        self.adicional_queijo = Adicional.objects.create(
            produto=self.produto_hamburguer,
            nome='Queijo',
            preco=Decimal('4.00'),
        )

        self.produto_esgotado = Produto.objects.create(
            categoria=self.cat_lanches,
            nome='Lanche Esgotado',
            preco=Decimal('20.00'),
            disponivel=False,  # RF07 / RN08
        )

    # -------------------------------------------------------------
    # RN04 & RN05 — Sessões de Mesa
    # -------------------------------------------------------------
    def test_rn04_nao_permite_pedido_sem_sessao_aberta(self):
        """RN04: Só é possível enviar pedido para uma mesa com sessão aberta."""
        url = reverse('criar-pedido')
        payload = {
            'mesa_uuid': str(self.mesa.token_uuid),
            'sessao_id': self.mesa.sessao_ativa.pk if self.mesa.sessao_ativa else None,
            'itens': [
                {'produto_id': self.produto_hamburguer.id, 'quantidade': 1}
            ]
        }
        self.client.get(reverse('mesa-por-uuid', args=[self.mesa.token_uuid]))
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('não possui uma sessão aberta', response.data.get('erro', ''))

    def test_rn05_uma_mesa_nao_pode_ter_duas_sessoes_abertas(self):
        """RN05: Uma mesa não pode ter duas sessões abertas ao mesmo tempo."""
        self.client.force_authenticate(user=self.user_garcom)
        url_abrir = reverse('abrir-sessao', kwargs={'mesa_id': self.mesa.id})

        # Primeira abertura (deve ser sucesso)
        resp1 = self.client.post(url_abrir)
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

        # Segunda abertura para a mesma mesa (deve ser bloqueada)
        resp2 = self.client.post(url_abrir)
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('já possui uma sessão aberta', resp2.data.get('erro', ''))

    # -------------------------------------------------------------
    # RN06 & RN07 — Cálculo de Valores e Adicionais
    # -------------------------------------------------------------
    def test_rn06_rn07_calculo_valor_item_e_adicionais(self):
        """
        RN06 & RN07: Valor do item = (preço do produto + adicionais) × quantidade.
        Exemplo de referência: hambúrguer R$ 32,90 + bacon R$ 5,00 + queijo R$ 4,00 = R$ 41,90.
        """
        sessao = SessaoMesa.objects.create(mesa=self.mesa, aberta_por=self.user_garcom)

        url = reverse('criar-pedido')
        payload = {
            'mesa_uuid': str(self.mesa.token_uuid),
            'sessao_id': self.mesa.sessao_ativa.pk if self.mesa.sessao_ativa else None,
            'itens': [
                {
                    'produto_id': self.produto_hamburguer.id,
                    'quantidade': 2,
                    'adicionais_ids': [self.adicional_bacon.id, self.adicional_queijo.id],
                    'observacao': 'Sem cebola'
                }
            ]
        }
        self.client.get(reverse('mesa-por-uuid', args=[self.mesa.token_uuid]))
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        pedido = Pedido.objects.get(id=response.data['id'])
        item = pedido.itens.first()

        # (32.90 + 5.00 + 4.00) = 41.90
        # 41.90 * 2 = 83.80
        esperado_unitario = Decimal('32.90')
        esperado_adicionais = Decimal('9.00')
        esperado_subtotal = (esperado_unitario + esperado_adicionais) * 2

        self.assertEqual(item.preco_unitario, esperado_unitario)
        self.assertEqual(item.total_adicionais, esperado_adicionais)
        self.assertEqual(item.subtotal, esperado_subtotal)
        self.assertEqual(pedido.valor_total, esperado_subtotal)

    # -------------------------------------------------------------
    # RN08 — Produto Indisponível
    # -------------------------------------------------------------
    def test_rn08_produto_indisponivel_bloqueado_no_pedido(self):
        """RN08: Produto indisponível não pode entrar no pedido."""
        SessaoMesa.objects.create(mesa=self.mesa, aberta_por=self.user_garcom)

        url = reverse('criar-pedido')
        payload = {
            'mesa_uuid': str(self.mesa.token_uuid),
            'sessao_id': self.mesa.sessao_ativa.pk if self.mesa.sessao_ativa else None,
            'itens': [
                {'produto_id': self.produto_esgotado.id, 'quantidade': 1}
            ]
        }
        self.client.get(reverse('mesa-por-uuid', args=[self.mesa.token_uuid]))
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------
    # RNF08 — Integridade de Valores Históricos
    # -------------------------------------------------------------
    def test_rnf08_integridade_valores_historicos(self):
        """RNF08: Mudar o cardápio depois não pode alterar pedidos antigos."""
        sessao = SessaoMesa.objects.create(mesa=self.mesa, aberta_por=self.user_garcom)
        pedido = Pedido.objects.create(sessao=sessao)
        item = ItemPedido.objects.create(
            pedido=pedido,
            produto=self.produto_hamburguer,
            quantidade=1,
            preco_unitario=self.produto_hamburguer.preco,  # R$ 32,90
        )
        ItemPedidoAdicional.objects.create(
            item_pedido=item,
            adicional=self.adicional_bacon,
            preco=self.adicional_bacon.preco,  # R$ 5,00
        )

        # Alterando os preços no cardápio
        self.produto_hamburguer.preco = Decimal('50.00')
        self.produto_hamburguer.save()
        self.adicional_bacon.preco = Decimal('10.00')
        self.adicional_bacon.save()

        # Recarrega o item e valida se mantém o preço gravado
        item.refresh_from_db()
        self.assertEqual(item.preco_unitario, Decimal('32.90'))
        self.assertEqual(item.subtotal, Decimal('37.90'))

    # -------------------------------------------------------------
    # RN01, RN02, RN03 — Fluxo de Status, Cancelamento e Auditoria
    # -------------------------------------------------------------
    def test_rn01_sequencia_status_valida(self):
        """RN01: Pedido segue RECEBIDO -> EM_PREPARACAO -> PRONTO -> A_CAMINHO -> ENTREGUE."""
        sessao = SessaoMesa.objects.create(mesa=self.mesa, aberta_por=self.user_garcom)
        pedido = Pedido.objects.create(sessao=sessao, status='RECEBIDO')

        self.client.force_authenticate(user=self.user_cozinha)
        url_status = reverse('alterar-status-pedido', kwargs={'pedido_id': pedido.id})

        # Tentativa inválida: Pular de RECEBIDO direto para PRONTO
        resp_invalido = self.client.patch(url_status, {'status': 'PRONTO'}, format='json')
        self.assertEqual(resp_invalido.status_code, status.HTTP_400_BAD_REQUEST)

        # Transição válida 1: RECEBIDO -> EM_PREPARACAO
        resp = self.client.patch(url_status, {'status': 'EM_PREPARACAO'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Transição válida 2: EM_PREPARACAO -> PRONTO
        resp = self.client.patch(url_status, {'status': 'PRONTO'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Garçom assume: PRONTO -> A_CAMINHO
        self.client.force_authenticate(user=self.user_garcom)
        resp = self.client.patch(url_status, {'status': 'A_CAMINHO'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Transição válida 4: A_CAMINHO -> ENTREGUE
        resp = self.client.patch(url_status, {'status': 'ENTREGUE'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Tentativa inválida: Retroceder de ENTREGUE para EM_PREPARACAO
        resp_retrocesso = self.client.patch(url_status, {'status': 'EM_PREPARACAO'}, format='json')
        self.assertEqual(resp_retrocesso.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rn02_cancelamento_apenas_antes_da_preparacao(self):
        """RN02: Um pedido só pode ser cancelado antes de entrar em preparação."""
        sessao = SessaoMesa.objects.create(mesa=self.mesa, aberta_por=self.user_garcom)
        self.client.force_authenticate(user=self.user_admin)

        # Pedido 1: Está RECEBIDO -> Pode cancelar
        pedido1 = Pedido.objects.create(sessao=sessao, status='RECEBIDO')
        url_p1 = reverse('alterar-status-pedido', kwargs={'pedido_id': pedido1.id})
        resp1 = self.client.patch(url_p1, {'status': 'CANCELADO'}, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        pedido1.refresh_from_db()
        self.assertEqual(pedido1.status, 'CANCELADO')

        # Pedido 2: Está EM_PREPARACAO -> NÃO pode cancelar
        pedido2 = Pedido.objects.create(sessao=sessao, status='EM_PREPARACAO')
        url_p2 = reverse('alterar-status-pedido', kwargs={'pedido_id': pedido2.id})
        resp2 = self.client.patch(url_p2, {'status': 'CANCELADO'}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rn03_auditoria_historico_status(self):
        """RN03: Cada mudança de status deve ficar registrada com data, hora e quem a fez."""
        sessao = SessaoMesa.objects.create(mesa=self.mesa, aberta_por=self.user_garcom)
        pedido = Pedido.objects.create(sessao=sessao, status='RECEBIDO')

        self.client.force_authenticate(user=self.user_cozinha)
        url_status = reverse('alterar-status-pedido', kwargs={'pedido_id': pedido.id})
        self.client.patch(url_status, {'status': 'EM_PREPARACAO'}, format='json')

        historico = HistoricoStatusPedido.objects.filter(pedido=pedido).latest('alterado_em')
        self.assertEqual(historico.status_anterior, 'RECEBIDO')
        self.assertEqual(historico.status_novo, 'EM_PREPARACAO')
        self.assertEqual(historico.alterado_por, self.user_cozinha)

    # -------------------------------------------------------------
    # RN09 & RN10 — Fechamento da Conta e Encerramento de Sessão
    # -------------------------------------------------------------
    def test_rn09_fechamento_apenas_com_todos_pedidos_entregues_ou_cancelados(self):
        """RN09: A conta só pode ser fechada quando todos os pedidos estiverem entregues ou cancelados."""
        sessao = SessaoMesa.objects.create(mesa=self.mesa, aberta_por=self.user_garcom)
        Pedido.objects.create(sessao=sessao, status='EM_PREPARACAO')

        self.client.force_authenticate(user=self.user_garcom)
        url_pagamento = reverse('processar-pagamento', kwargs={'sessao_id': sessao.id})

        # Tentativa de fechar conta com pedido em preparação (deve falhar)
        resp = self.client.post(url_pagamento, {'meio_pagamento': 'PIX'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Todos os pedidos devem estar entregues ou cancelados', resp.data.get('erro', ''))

    def test_rn10_sessao_encerrada_nao_aceita_novos_pedidos(self):
        """RN10: Após o fechamento, a sessão encerrada não aceita novos pedidos."""
        sessao = SessaoMesa.objects.create(mesa=self.mesa, aberta_por=self.user_garcom, ativa=False)

        url = reverse('criar-pedido')
        payload = {
            'mesa_uuid': str(self.mesa.token_uuid),
            'sessao_id': self.mesa.sessao_ativa.pk if self.mesa.sessao_ativa else None,
            'itens': [{'produto_id': self.produto_hamburguer.id, 'quantidade': 1}]
        }
        # Como a sessão não está ativa, mesa.sessao_ativa é None (RN04)
        self.client.get(reverse('mesa-por-uuid', args=[self.mesa.token_uuid]))
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def abrir_sessao_teste(self):
        return SessaoMesa.objects.create(mesa=self.mesa, aberta_por=self.user_garcom)

    def enviar_pedido(self, itens=None, **campos):
        payload = {
            'mesa_uuid': str(self.mesa.token_uuid),
            'sessao_id': self.mesa.sessao_ativa.pk if self.mesa.sessao_ativa else None,
            'itens': itens if itens is not None else [{
                'produto_id': self.produto_hamburguer.id, 'quantidade': 1,
            }],
            **campos,
        }
        self.client.get(reverse('mesa-por-uuid', args=[self.mesa.token_uuid]))
        return self.client.post(reverse('criar-pedido'), payload, format='json')

    def mudar_status(self, pedido, status_novo):
        return self.client.patch(
            reverse('alterar-status-pedido', args=[pedido.id]),
            {'status': status_novo}, format='json',
        )

    def assert_sem_pedido_parcial(self):
        for model in (Pedido, ItemPedido, ItemPedidoAdicional, HistoricoStatusPedido):
            self.assertEqual(model.objects.count(), 0, model.__name__)

    def test_rn01_rn02_matriz_completa_de_transicoes(self):
        """As 36 combinações incluem saltos, retrocessos, repetição e estados finais."""
        sessao = self.abrir_sessao_teste()
        self.client.force_authenticate(self.user_admin)
        # Oráculo independente da constante de implementação.
        permitidas = {
            ('RECEBIDO', 'EM_PREPARACAO'), ('RECEBIDO', 'CANCELADO'),
            ('EM_PREPARACAO', 'PRONTO'), ('PRONTO', 'A_CAMINHO'),
            ('A_CAMINHO', 'ENTREGUE'),
        }
        estados = ['RECEBIDO', 'EM_PREPARACAO', 'PRONTO', 'A_CAMINHO', 'ENTREGUE', 'CANCELADO']
        for anterior, novo in product(estados, repeat=2):
            with self.subTest(anterior=anterior, novo=novo):
                pedido = Pedido.objects.create(sessao=sessao, status=anterior)
                atualizado_em = pedido.updated_at
                antes = timezone.now()
                response = self.mudar_status(pedido, novo)
                pedido.refresh_from_db()
                if (anterior, novo) in permitidas:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(pedido.status, novo)
                    self.assertEqual(response.data['status'], novo)
                    historico = pedido.historico_status.get()
                    self.assertEqual(historico.status_anterior, anterior)
                    self.assertEqual(historico.status_novo, novo)
                    self.assertEqual(historico.alterado_por, self.user_admin)
                    self.assertTrue(timezone.is_aware(historico.alterado_em))
                    self.assertLessEqual(antes, historico.alterado_em)
                    self.assertLessEqual(historico.alterado_em, timezone.now())
                else:
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(pedido.status, anterior)
                    self.assertEqual(pedido.updated_at, atualizado_em)
                    self.assertFalse(pedido.historico_status.exists())

    def test_rn01_status_invalido_ausente_ou_nulo(self):
        pedido = Pedido.objects.create(sessao=self.abrir_sessao_teste())
        self.client.force_authenticate(self.user_cozinha)
        for payload in ({}, {'status': None}, {'status': ''}, {'status': 'DESCONHECIDO'}):
            with self.subTest(payload=payload):
                response = self.client.patch(
                    reverse('alterar-status-pedido', args=[pedido.id]), payload, format='json',
                )
                self.assertEqual(response.status_code, 400)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, 'RECEBIDO')
        self.assertFalse(pedido.historico_status.exists())

    def test_rn03_auditoria_inicial_anonima_e_autenticada(self):
        self.abrir_sessao_teste()
        for user in (None, self.user_admin):
            with self.subTest(user=user):
                self.client.force_authenticate(user)
                antes = timezone.now()
                response = self.enviar_pedido()
                self.assertEqual(response.status_code, 201)
                historico = HistoricoStatusPedido.objects.get(pedido_id=response.data['id'])
                self.assertEqual(historico.status_anterior, '')
                self.assertEqual(historico.status_novo, 'RECEBIDO')
                self.assertEqual(historico.alterado_por, user)
                self.assertLessEqual(antes, historico.alterado_em)
                self.assertLessEqual(historico.alterado_em, timezone.now())

    def test_rn03_fluxo_completo_preserva_autoria_e_ordem(self):
        self.abrir_sessao_teste()
        response = self.enviar_pedido()
        pedido = Pedido.objects.get(pk=response.data['id'])
        etapas = [
            (self.user_cozinha, 'EM_PREPARACAO'), (self.user_cozinha, 'PRONTO'),
            (self.user_garcom, 'A_CAMINHO'), (self.user_garcom, 'ENTREGUE'),
        ]
        for user, novo in etapas:
            self.client.force_authenticate(user)
            self.assertEqual(self.mudar_status(pedido, novo).status_code, 200)
        historico = list(pedido.historico_status.all())
        self.assertEqual([h.status_novo for h in historico], [
            'RECEBIDO', 'EM_PREPARACAO', 'PRONTO', 'A_CAMINHO', 'ENTREGUE',
        ])
        self.assertEqual([h.status_anterior for h in historico], [
            '', 'RECEBIDO', 'EM_PREPARACAO', 'PRONTO', 'A_CAMINHO',
        ])
        self.assertEqual([h.alterado_por for h in historico], [
            None, self.user_cozinha, self.user_cozinha, self.user_garcom, self.user_garcom,
        ])

    def test_rn03_falha_na_auditoria_reverte_status(self):
        pedido = Pedido.objects.create(sessao=self.abrir_sessao_teste())
        atualizado_em = pedido.updated_at
        self.client.force_authenticate(self.user_cozinha)
        with patch('restaurante.views.HistoricoStatusPedido.objects.create', side_effect=RuntimeError('falha de auditoria')):
            with self.assertRaisesMessage(RuntimeError, 'falha de auditoria'):
                self.mudar_status(pedido, 'EM_PREPARACAO')
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, 'RECEBIDO')
        self.assertEqual(pedido.updated_at, atualizado_em)
        self.assertFalse(pedido.historico_status.exists())

    def test_rn03_falha_na_auditoria_inicial_reverte_criacao(self):
        self.abrir_sessao_teste()
        with patch('restaurante.views.HistoricoStatusPedido.objects.create', side_effect=RuntimeError('falha de auditoria')):
            with self.assertRaisesMessage(RuntimeError, 'falha de auditoria'):
                self.enviar_pedido()
        self.assert_sem_pedido_parcial()

    def test_rn04_sessao_de_outra_mesa_nao_autoriza_pedido(self):
        outra_mesa = Mesa.objects.create(numero=2)
        SessaoMesa.objects.create(mesa=outra_mesa)
        self.assertEqual(self.enviar_pedido().status_code, 400)
        self.assert_sem_pedido_parcial()

    def test_rn04_mesa_inativa_uuid_invalido_ou_inexistente(self):
        self.abrir_sessao_teste()
        self.mesa.ativa = False
        self.mesa.save()
        for token, esperado in ((str(self.mesa.token_uuid), 404), (str(uuid4()), 404), ('invalido', 400)):
            with self.subTest(token=token):
                self.assertEqual(self.enviar_pedido(mesa_uuid=token).status_code, esperado)
                self.assert_sem_pedido_parcial()

    def test_rn05_restricao_no_banco_impede_sessao_duplicada(self):
        sessao = self.abrir_sessao_teste()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SessaoMesa.objects.create(mesa=self.mesa)
        self.assertEqual(list(self.mesa.sessoes.filter(ativa=True)), [sessao])

    def test_rn05_conflito_na_gravacao_retorna_400(self):
        """Simula a consulta desatualizada de abertura concorrente; o banco decide."""
        self.abrir_sessao_teste()
        self.client.force_authenticate(self.user_garcom)
        with patch.object(Mesa, 'sessao_ativa', new_callable=PropertyMock, return_value=None):
            response = self.client.post(reverse('abrir-sessao', args=[self.mesa.id]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.mesa.sessoes.filter(ativa=True).count(), 1)

    def test_rn05_reabertura_e_sessoes_independentes(self):
        antiga = self.abrir_sessao_teste()
        antiga.ativa = False
        antiga.fechada_em = timezone.now()
        antiga.save()
        self.client.force_authenticate(self.user_garcom)
        nova = self.client.post(reverse('abrir-sessao', args=[self.mesa.id]))
        self.assertEqual(nova.status_code, 201)
        self.assertNotEqual(nova.data['id'], antiga.id)
        self.assertEqual(nova.data['aberta_por'], self.user_garcom.id)
        outra_mesa = Mesa.objects.create(numero=2)
        self.assertEqual(self.client.post(reverse('abrir-sessao', args=[outra_mesa.id])).status_code, 201)
        self.assertEqual(self.mesa.sessoes.filter(ativa=True).count(), 1)
        # Mais de uma sessão encerrada é permitida para preservar o histórico.
        SessaoMesa.objects.create(mesa=self.mesa, ativa=False)

    def test_rn05_pedido_associado_somente_a_sessao_atual(self):
        antiga = SessaoMesa.objects.create(mesa=self.mesa, ativa=False)
        atual = self.abrir_sessao_teste()
        response = self.enviar_pedido()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['sessao'], atual.id)
        self.assertFalse(antiga.pedidos.exists())

    def test_rn06_rn07_valores_de_referencia_com_e_sem_adicionais(self):
        self.abrir_sessao_teste()
        casos = [
            (1, [], '32.90'), (2, [], '65.80'),
            (1, [self.adicional_bacon.id], '37.90'),
            (1, [self.adicional_bacon.id, self.adicional_queijo.id], '41.90'),
            (3, [self.adicional_bacon.id, self.adicional_queijo.id], '125.70'),
        ]
        for quantidade, adicionais, esperado in casos:
            with self.subTest(quantidade=quantidade, adicionais=adicionais):
                response = self.enviar_pedido([{
                    'produto_id': self.produto_hamburguer.id, 'quantidade': quantidade,
                    'adicionais_ids': adicionais,
                }])
                self.assertEqual(response.status_code, 201)
                pedido = Pedido.objects.get(pk=response.data['id'])
                item = pedido.itens.get()
                self.assertEqual(item.subtotal, Decimal(esperado))
                self.assertEqual(pedido.valor_total, Decimal(esperado))
                self.assertEqual(Decimal(str(response.data['valor_total'])), Decimal(esperado))
                self.assertEqual(Decimal(str(response.data['itens'][0]['subtotal'])), Decimal(esperado))

    def test_rn06_soma_multiplos_itens_e_ignora_precos_do_cliente(self):
        self.abrir_sessao_teste()
        response = self.enviar_pedido([
            {'produto_id': self.produto_hamburguer.id, 'quantidade': 2,
             'adicionais_ids': [self.adicional_bacon.id, self.adicional_queijo.id],
             'preco_unitario': '0.01', 'subtotal': '0.01'},
            {'produto_id': self.produto_hamburguer.id, 'preco_unitario': '0.01'},
        ], valor_total='0.01', status='ENTREGUE')
        self.assertEqual(response.status_code, 201)
        pedido = Pedido.objects.get(pk=response.data['id'])
        self.assertEqual(pedido.valor_total, Decimal('116.70'))
        self.assertEqual(pedido.status, 'RECEBIDO')
        self.assertEqual(pedido.itens.count(), 2)
        self.assertEqual(pedido.itens.last().quantidade, 1)

    def test_rn06_rejeita_quantidades_invalidas_e_pedido_vazio(self):
        self.abrir_sessao_teste()
        casos = [[], *[
            [{'produto_id': self.produto_hamburguer.id, 'quantidade': quantidade}]
            for quantidade in (0, -1, 1.5, None, 'abc')
        ]]
        for itens in casos:
            with self.subTest(itens=itens):
                self.assertEqual(self.enviar_pedido(itens).status_code, 400)
                self.assert_sem_pedido_parcial()

    def test_rn07_adicional_de_outro_produto_ou_inexistente_reverte_pedido(self):
        self.abrir_sessao_teste()
        alheio = Adicional.objects.create(produto=self.produto_esgotado, nome='Extra', preco='1.00')
        for adicional_id in (alheio.id, 999999):
            with self.subTest(adicional_id=adicional_id):
                response = self.enviar_pedido([
                    {'produto_id': self.produto_hamburguer.id, 'adicionais_ids': [self.adicional_bacon.id]},
                    {'produto_id': self.produto_hamburguer.id, 'adicionais_ids': [adicional_id]},
                ])
                self.assertEqual(response.status_code, 404)
                self.assert_sem_pedido_parcial()

    def test_rn07_adicionais_repetidos_sao_rejeitados(self):
        self.abrir_sessao_teste()
        response = self.enviar_pedido([{
            'produto_id': self.produto_hamburguer.id,
            'adicionais_ids': [self.adicional_bacon.id, self.adicional_bacon.id],
        }])
        self.assertEqual(response.status_code, 400)
        self.assert_sem_pedido_parcial()

    def test_observacao_do_item_respeita_limite_do_banco(self):
        self.abrir_sessao_teste()
        response = self.enviar_pedido([{
            'produto_id': self.produto_hamburguer.id, 'observacao': 'a' * 256,
        }])
        self.assertEqual(response.status_code, 400)
        self.assert_sem_pedido_parcial()
        response = self.enviar_pedido([{
            'produto_id': self.produto_hamburguer.id, 'observacao': 'a' * 255,
        }])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['itens'][0]['observacao'], 'a' * 255)

    def test_rn08_item_invalido_reverte_todos_os_itens_e_historico(self):
        self.abrir_sessao_teste()
        for produto_id, esperado in ((self.produto_esgotado.id, 400), (999999, 404)):
            with self.subTest(produto_id=produto_id):
                response = self.enviar_pedido([
                    {'produto_id': self.produto_hamburguer.id, 'adicionais_ids': [self.adicional_bacon.id]},
                    {'produto_id': produto_id},
                ])
                self.assertEqual(response.status_code, esperado)
                self.assert_sem_pedido_parcial()

    def test_rnf08_precos_historicos_via_api_e_novos_pedidos(self):
        self.abrir_sessao_teste()
        itens = [{'produto_id': self.produto_hamburguer.id, 'quantidade': 2,
                  'adicionais_ids': [self.adicional_bacon.id, self.adicional_queijo.id]}]
        antigo = self.enviar_pedido(itens)
        self.assertEqual(antigo.status_code, 201)
        Produto.objects.filter(pk=self.produto_hamburguer.id).update(preco='50.00')
        Adicional.objects.filter(pk=self.adicional_bacon.id).update(preco='10.00')
        Adicional.objects.filter(pk=self.adicional_queijo.id).update(preco='6.00')
        # Busca nova no banco, sem aproveitar cache da resposta de criação.
        pedido = Pedido.objects.get(pk=antigo.data['id'])
        item = pedido.itens.get()
        self.assertEqual(item.preco_unitario, Decimal('32.90'))
        self.assertEqual(sorted(item.itens_adicionais.values_list('preco', flat=True)), [Decimal('4.00'), Decimal('5.00')])
        self.assertEqual(item.subtotal, Decimal('83.80'))
        self.assertEqual(pedido.valor_total, Decimal('83.80'))
        consulta = self.client.get(reverse('pedidos-da-mesa', args=[self.mesa.token_uuid]))
        self.assertEqual(Decimal(str(consulta.data[0]['valor_total'])), Decimal('83.80'))
        novo = self.enviar_pedido(itens)
        self.assertEqual(novo.status_code, 201)
        self.assertEqual(Decimal(str(novo.data['valor_total'])), Decimal('132.00'))

    def test_cozinha_colunas_vazias(self):
        self.client.force_authenticate(self.user_cozinha)
        response = self.client.get(reverse('painel-cozinha'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'RECEBIDO': [], 'EM_PREPARACAO': [], 'PRONTO': []})

    def test_cozinha_agrupa_status_e_prioriza_pedidos_antigos(self):
        sessao = self.abrir_sessao_teste()
        primeiro = Pedido.objects.create(sessao=sessao)
        segundo = Pedido.objects.create(sessao=sessao)
        Pedido.objects.filter(pk=segundo.id).update(created_at=primeiro.created_at - timedelta(minutes=10))
        preparo = Pedido.objects.create(sessao=sessao, status='EM_PREPARACAO')
        pronto = Pedido.objects.create(sessao=sessao, status='PRONTO')
        for estado in ('A_CAMINHO', 'ENTREGUE', 'CANCELADO'):
            Pedido.objects.create(sessao=sessao, status=estado)
        self.client.force_authenticate(self.user_cozinha)
        data = self.client.get(reverse('painel-cozinha')).data
        self.assertEqual([p['id'] for p in data['RECEBIDO']], [segundo.id, primeiro.id])
        self.assertEqual([p['id'] for p in data['EM_PREPARACAO']], [preparo.id])
        self.assertEqual([p['id'] for p in data['PRONTO']], [pronto.id])
        self.assertEqual(data['RECEBIDO'][0]['proximo_status'], 'EM_PREPARACAO')
        self.assertEqual(data['EM_PREPARACAO'][0]['proximo_status'], 'PRONTO')
        self.assertIsNone(data['PRONTO'][0]['proximo_status'])

    def test_cozinha_detalhes_do_cartao_e_atualizacao_por_polling(self):
        self.abrir_sessao_teste()
        response = self.enviar_pedido([{
            'produto_id': self.produto_hamburguer.id, 'quantidade': 2,
            'adicionais_ids': [self.adicional_bacon.id, self.adicional_queijo.id],
            'observacao': 'Sem cebola',
        }], observacao='Alergia a amendoim')
        self.assertEqual(response.status_code, 201)
        pedido = Pedido.objects.get(pk=response.data['id'])
        self.client.force_authenticate(self.user_cozinha)
        url = reverse('painel-cozinha')
        card = self.client.get(url).data['RECEBIDO'][0]
        self.assertEqual(card['mesa_numero'], self.mesa.numero)
        self.assertEqual(card['observacao'], 'Alergia a amendoim')
        self.assertEqual(card['created_at'], response.data['created_at'])
        self.assertEqual(card['status_display'], 'Recebido')
        self.assertEqual(card['itens'][0]['quantidade'], 2)
        self.assertEqual(card['itens'][0]['produto_nome'], self.produto_hamburguer.nome)
        self.assertEqual(card['itens'][0]['observacao'], 'Sem cebola')
        self.assertEqual({a['nome'] for a in card['itens'][0]['itens_adicionais']}, {'Bacon', 'Queijo'})
        for novo, anterior in (('EM_PREPARACAO', 'RECEBIDO'), ('PRONTO', 'EM_PREPARACAO')):
            self.assertEqual(self.mudar_status(pedido, novo).status_code, 200)
            painel = self.client.get(url).data
            self.assertEqual(painel[anterior], [])
            self.assertEqual(painel[novo][0]['id'], pedido.id)
        self.client.force_authenticate(self.user_garcom)
        self.assertEqual(self.mudar_status(pedido, 'A_CAMINHO').status_code, 200)
        self.client.force_authenticate(self.user_cozinha)
        self.assertEqual(self.client.get(url).data['PRONTO'], [])

    def test_cozinha_quantidade_de_consultas_nao_cresce_com_pedidos(self):
        self.abrir_sessao_teste()
        self.enviar_pedido()
        self.client.force_authenticate(self.user_cozinha)
        self.user_cozinha.perfil  # Resolve a permissão antes de medir os dados do painel.
        with CaptureQueriesContext(connection) as poucas:
            self.assertEqual(self.client.get(reverse('painel-cozinha')).status_code, 200)
        for _ in range(5):
            self.enviar_pedido()
        with CaptureQueriesContext(connection) as muitas:
            self.assertEqual(self.client.get(reverse('painel-cozinha')).status_code, 200)
        self.assertEqual(len(poucas), len(muitas))
        self.assertLessEqual(len(muitas), 6)

    def test_cozinha_disponibilidade_reflete_cardapio_e_novos_pedidos(self):
        self.abrir_sessao_teste()
        self.client.force_authenticate(self.user_cozinha)
        url = reverse('disponibilidade-produto', args=[self.produto_hamburguer.id])
        for disponivel in (False, True):
            with self.subTest(disponivel=disponivel):
                response = self.client.patch(url, {'disponivel': disponivel}, format='json')
                self.assertEqual(response.status_code, 200)
                self.assertIs(response.data['disponivel'], disponivel)
                self.produto_hamburguer.refresh_from_db()
                self.assertIs(self.produto_hamburguer.disponivel, disponivel)
                self.client.force_authenticate(None)
                cardapio = self.client.get(reverse('cardapio')).data
                produto = next(p for c in cardapio for p in c['produtos'] if p['id'] == self.produto_hamburguer.id)
                self.assertIs(produto['disponivel'], disponivel)
                self.assertEqual(self.enviar_pedido().status_code, 201 if disponivel else 400)
                self.client.force_authenticate(self.user_cozinha)

    def test_cozinha_disponibilidade_rejeita_booleanos_invalidos(self):
        self.client.force_authenticate(self.user_cozinha)
        url = reverse('disponibilidade-produto', args=[self.produto_hamburguer.id])
        for payload in ({}, *[{'disponivel': v} for v in (None, 'false', 'true', 'abc', 0, 1, [], {})]):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.patch(url, payload, format='json').status_code, 400)
                self.produto_hamburguer.refresh_from_db()
                self.assertTrue(self.produto_hamburguer.disponivel)

    def test_permissoes_do_painel_e_disponibilidade(self):
        sem_perfil = User.objects.create_user(username='sem_perfil')
        for user, esperado in ((None, 403), (sem_perfil, 403), (self.user_garcom, 403),
                               (self.user_cozinha, 200), (self.user_admin, 200)):
            with self.subTest(user=user):
                self.client.force_authenticate(user)
                self.assertEqual(self.client.get(reverse('painel-cozinha')).status_code, esperado)
                response = self.client.patch(
                    reverse('disponibilidade-produto', args=[self.produto_hamburguer.id]),
                    {'disponivel': False}, format='json',
                )
                self.assertEqual(response.status_code, esperado)

    def test_permissoes_de_status_e_abertura_de_sessao(self):
        pedido = Pedido.objects.create(sessao=self.abrir_sessao_teste())
        outra_mesa = Mesa.objects.create(numero=2)
        sem_perfil = User.objects.create_user(username='sem_perfil')
        for user in (None, sem_perfil):
            with self.subTest(user=user):
                self.client.force_authenticate(user)
                self.assertEqual(self.mudar_status(pedido, 'EM_PREPARACAO').status_code, 403)
                self.assertEqual(self.client.post(reverse('abrir-sessao', args=[outra_mesa.id])).status_code, 403)
        self.client.force_authenticate(self.user_cozinha)
        self.assertEqual(self.client.post(reverse('abrir-sessao', args=[outra_mesa.id])).status_code, 403)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, 'RECEBIDO')
        self.assertFalse(pedido.historico_status.exists())
        self.assertFalse(outra_mesa.sessoes.exists())

    def test_recursos_inexistentes_retornam_404(self):
        self.client.force_authenticate(self.user_admin)
        self.assertEqual(self.client.patch(reverse('alterar-status-pedido', args=[999999]), {'status': 'PRONTO'}, format='json').status_code, 404)
        self.assertEqual(self.client.patch(reverse('disponibilidade-produto', args=[999999]), {'disponivel': False}, format='json').status_code, 404)
        self.assertEqual(self.client.post(reverse('abrir-sessao', args=[999999])).status_code, 404)
