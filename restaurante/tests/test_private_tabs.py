"""Responsável único, expiração, transferência e isolamento entre famílias."""
from datetime import timedelta
from uuid import uuid4
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied
from .. import services
from ..models import Categoria, ConviteComanda, Mesa, Pedido, Perfil, Produto, SessaoMesa, TrocaResponsavel
from .support import conferencia


class PrivateTabsTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1)
        self.produto = Produto.objects.create(categoria=Categoria.objects.create(nome='Teste'), nome='Item', preco='10.00')
        self.staff = User.objects.create_user('equipe-atendimento')
        Perfil.objects.create(user=self.staff, role='GARCOM')
        self.base = f'/api/mesa/{self.mesa.token_uuid}/'
        self.a = self.visitante()
        self.b = self.visitante()

    def visitante(self):
        client = APIClient(enforce_csrf_checks=True)
        client.get(f'/mesa/{self.mesa.token_uuid}/')
        return client

    def post(self, client, url, data=None):
        return client.post(url, data or {}, format='json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)

    def pedir(self, client, **extra):
        ctx = client.get(self.base).data
        return self.post(client, '/api/pedidos/criar/', {'mesa_uuid': str(self.mesa.token_uuid),
            'sessao_id': ctx['sessao_id'], 'atendimento_id': ctx['atendimento_id'], 'chave_envio': str(uuid4()),
            'itens': [{'produto_id': self.produto.pk, 'quantidade': 1}], **extra})

    def troca(self, client):
        result = self.post(client, self.base + 'transferencia/')
        self.assertEqual(result.status_code, 200, result.data)
        return result.data

    def test_first_reader_reserves_and_other_browser_cannot_view_or_order(self):
        a, b = self.a.get(self.base).data, self.b.get(self.base).data
        self.assertTrue(a['acesso_liberado'])
        self.assertFalse(b['acesso_liberado'])
        self.assertTrue(b['mesa_em_uso'])
        self.assertIsNone(b['atendimento_id'])
        self.assertIsNone(b['sessao_id'])
        self.assertEqual(SessaoMesa.objects.count(), 0)
        blocked = self.b.get(f'/mesa/{self.mesa.token_uuid}/')
        self.assertContains(blocked, 'Esta mesa já está em atendimento')
        self.assertNotContains(blocked, 'id="cart-items"')
        self.assertEqual(self.post(self.b, self.base + 'novo-atendimento/').status_code, 403)
        order = self.pedir(self.a)
        self.assertEqual(order.status_code, 201, order.data)
        for path in ('pedidos/', 'conta/'):
            self.assertEqual(self.b.get(self.base + path).status_code, 403)
        self.assertEqual(self.post(self.b, '/api/pedidos/criar/', {'mesa_uuid': str(self.mesa.token_uuid),
            'atendimento_id': a['atendimento_id'], 'sessao_id': order.data['sessao'],
            'itens': [{'produto_id': self.produto.pk, 'quantidade': 1}]}).status_code, 403)

    def test_polling_does_not_renew_idle_reservation_but_real_activity_does(self):
        self.mesa.refresh_from_db(); before = self.mesa.reserva_ate
        self.a.get(self.base)
        self.mesa.refresh_from_db(); self.assertEqual(self.mesa.reserva_ate, before)
        self.assertEqual(self.post(self.a, self.base + 'atividade/').status_code, 200)
        self.mesa.refresh_from_db(); self.assertGreater(self.mesa.reserva_ate, before)
        self.assertEqual(self.post(self.b, self.base + 'atividade/').status_code, 403)

    def test_expired_empty_reservation_is_free_and_old_device_cannot_take_new_owner(self):
        old = self.a.get(self.base).data['atendimento_id']
        Mesa.objects.filter(pk=self.mesa.pk).update(reserva_ate=timezone.now()-timedelta(seconds=1))
        self.assertTrue(self.a.get(self.base).data['reserva_expirada'])
        self.assertFalse(self.a.get(self.base).data['acesso_liberado'])
        self.assertEqual(self.mesa.__class__.objects.get(pk=self.mesa.pk).status_display, 'livre')
        self.b.get(f'/mesa/{self.mesa.token_uuid}/')
        self.assertTrue(self.b.get(self.base).data['acesso_liberado'])
        self.assertNotEqual(old, self.b.get(self.base).data['atendimento_id'])
        self.assertFalse(self.a.get(self.base).data['acesso_liberado'])
        self.assertEqual(self.post(self.a, self.base + 'atividade/').status_code, 403)

    def test_sent_orders_never_expire_on_inactivity(self):
        order = self.pedir(self.a)
        self.mesa.refresh_from_db()
        self.assertIsNone(self.mesa.reserva_ate)
        self.assertTrue(self.mesa.sessoes.get(pk=order.data['sessao']).ativa)
        self.assertFalse(self.b.get(self.base).data['acesso_liberado'])

    def test_staff_transfer_revokes_old_phone_and_preserves_order_and_session(self):
        order = self.pedir(self.a)
        old = self.a.get(self.base).data['atendimento_id']
        request = self.troca(self.b)
        url = f'/api/garcom/trocas-responsavel/{request["id"]}/autorizar/'
        self.assertEqual(self.post(self.b, url).status_code, 403)
        self.assertFalse(self.b.get(self.base).data['acesso_liberado'])
        cozinha = User.objects.create_user('cozinha-transferencia')
        Perfil.objects.create(user=cozinha, role='COZINHA')
        staff = APIClient(); staff.force_authenticate(cozinha)
        self.assertEqual(staff.post(url).status_code, 403)
        staff.force_authenticate(self.staff)
        table = staff.get('/api/garcom/mapa-mesas/').data[0]
        self.assertEqual(table['transferencias_pendentes'][0]['codigo'], request['codigo'])
        self.assertNotIn(old, str(table))
        self.assertEqual(staff.post(url).status_code, 200)
        self.assertEqual(staff.post(url).status_code, 404)
        context = self.b.get(self.base).data
        self.assertTrue(context['acesso_liberado'])
        self.assertEqual(context['sessao_id'], order.data['sessao'])
        self.assertEqual(self.b.get(self.base+'conta/').data['valor_total'], '10.00')
        self.assertEqual(self.a.get(self.base+'pedidos/').status_code, 403)
        self.assertEqual(self.post(self.a,self.base+'solicitar-conta/').status_code,403)
        # Mesmo uma requisição validada antes da transferência é recusada
        # quando adquire o bloqueio do atendimento com a capacidade antiga.
        with self.assertRaises(PermissionDenied):
            services.pedir_conta(self.mesa.token_uuid, order.data['sessao'], geracao=old)
        self.assertEqual(self.post(self.a, self.base+'novo-atendimento/').status_code, 403)
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(self.pedir(self.b).data['sessao'], order.data['sessao'])

    def test_expired_transfer_and_old_invites_never_grant_access(self):
        self.pedir(self.a)
        request = self.troca(self.b)
        TrocaResponsavel.objects.filter(pk=request['id']).update(expira_em=timezone.now()-timedelta(seconds=1))
        staff = APIClient(); staff.force_authenticate(self.staff)
        self.assertEqual(staff.post(f'/api/garcom/trocas-responsavel/{request["id"]}/autorizar/').status_code, 404)
        invite = ConviteComanda.objects.create(sessao=SessaoMesa.objects.get(), expira_em=timezone.now()+timedelta(hours=1))
        path = f'/convite/{invite.token}/'
        self.assertEqual(self.b.get(path).status_code, 410)
        self.assertEqual(self.post(self.b,path).status_code, 410)
        self.assertEqual(self.post(self.a,self.base+'compartilhar/').status_code, 410)
        self.assertEqual(self.post(self.a,self.base+'selecionar-comanda/', {'comanda_id': invite.sessao_id}).status_code, 410)
        self.assertFalse(self.b.get(self.base).data['acesso_liberado'])

    def test_payment_releases_table_but_previous_phone_never_sees_new_family(self):
        first = self.pedir(self.a)
        admin = User.objects.create_user('gestor-finalizacao'); Perfil.objects.create(user=admin,role='ADMIN')
        for status in ('EM_PREPARACAO','PRONTO','A_CAMINHO','ENTREGUE'):
            services.transitar(first.data['id'],status,admin)
        sessao = SessaoMesa.objects.get(pk=first.data['sessao'])
        services.pagar(sessao.pk,'PIX',self.staff,**conferencia(sessao))
        self.b.get(f'/mesa/{self.mesa.token_uuid}/')
        second = self.pedir(self.b)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(second.data['sessao'], first.data['sessao'])
        self.a.get(f'/mesa/{self.mesa.token_uuid}/')
        self.assertTrue(self.a.get(self.base).data['atendimento_encerrado'])
        self.assertFalse(self.a.get(self.base).data['acesso_liberado'])
        self.assertEqual(self.a.get(self.base+'pedidos/').status_code,403)
        self.assertEqual(self.b.get(self.base+'conta/').data['valor_total'],'10.00')

    def test_legacy_multiple_accounts_are_preserved_and_transfer_refused(self):
        first = self.pedir(self.a)
        legacy = SessaoMesa.objects.create(mesa=self.mesa)
        request = self.troca(self.b)
        staff = APIClient(); staff.force_authenticate(self.staff)
        self.assertEqual(staff.post(f'/api/garcom/trocas-responsavel/{request["id"]}/autorizar/').status_code,400)
        self.assertTrue(SessaoMesa.objects.get(pk=legacy.pk).ativa)
        self.assertTrue(Pedido.objects.filter(pk=first.data['id']).exists())

    def test_pending_transfer_cannot_take_over_the_next_family(self):
        order = self.pedir(self.a)
        request = self.troca(self.b)
        admin = User.objects.create_user('gestor-nova-familia'); Perfil.objects.create(user=admin,role='ADMIN')
        for status in ('EM_PREPARACAO','PRONTO','A_CAMINHO','ENTREGUE'):
            services.transitar(order.data['id'],status,admin)
        sessao = SessaoMesa.objects.get(pk=order.data['sessao'])
        services.pagar(sessao.pk,'PIX',self.staff,**conferencia(sessao))
        next_family = self.visitante()
        self.assertTrue(next_family.get(self.base).data['acesso_liberado'])
        staff = APIClient(); staff.force_authenticate(self.staff)
        self.assertEqual(staff.post(f'/api/garcom/trocas-responsavel/{request["id"]}/autorizar/').status_code,400)
        self.assertTrue(next_family.get(self.base).data['acesso_liberado'])
        self.assertFalse(self.b.get(self.base).data['acesso_liberado'])
