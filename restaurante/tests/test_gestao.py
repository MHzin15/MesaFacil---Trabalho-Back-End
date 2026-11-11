"""Fluxos reais da gestão e suas fronteiras de acesso e integridade."""
from decimal import Decimal
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from ..models import Adicional, Categoria, Conta, ItemPedido, Mesa, Pedido, Perfil, Produto, SessaoMesa


class GestaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.gestor = User.objects.create_user('gestor', password='Acesso-Gestor-9z!mV')
        Perfil.objects.create(user=cls.gestor, role='ADMIN')
        cls.garcom = User.objects.create_user('garcom', first_name='João')
        Perfil.objects.create(user=cls.garcom, role='GARCOM')
        cls.root = User.objects.create_superuser('responsavel', password='Sistema-9mV!zR')
        cls.categoria = Categoria.objects.create(nome='Pratos')
        cls.produto = Produto.objects.create(categoria=cls.categoria, nome='Prato', preco='25.00')
        cls.mesa = Mesa.objects.create(numero=1)
        cls.sessao = SessaoMesa.objects.create(mesa=cls.mesa)
        cls.pedido = Pedido.objects.create(sessao=cls.sessao)
        ItemPedido.objects.create(pedido=cls.pedido, produto=cls.produto, quantidade=2, preco_unitario='25.00')

    def setUp(self):
        self.client.force_login(self.gestor)

    def staff_data(self, **overrides):
        return {'username': 'ana.salao', 'first_name': 'Ana', 'last_name': 'Silva',
                'role': 'GARCOM', 'is_active': 'on', 'senha': 'Senha-Ana-9v!Mz',
                'confirmar_senha': 'Senha-Ana-9v!Mz', **overrides}

    def test_all_management_screens_render_without_django_admin_forms(self):
        urls = ['/admin/', '/admin/equipe/', '/admin/equipe/novo/', f'/admin/equipe/{self.garcom.pk}/',
                f'/admin/equipe/{self.garcom.pk}/senha/', '/admin/mesas/', '/admin/cardapio/',
                '/admin/categorias/', '/admin/adicionais/', '/admin/pedidos/', '/admin/relatorios/',
                '/admin/atividades/', f'/admin/cardapio/{self.produto.pk}/preco/',
                f'/admin/pedidos/{self.pedido.pk}/', f'/admin/pedidos/{self.pedido.pk}/cancelar/']
        for tipo, pk in [('mesas', self.mesa.pk), ('produtos', self.produto.pk), ('categorias', self.categoria.pk)]:
            urls.extend([f'/admin/cadastro/{tipo}/novo/', f'/admin/cadastro/{tipo}/{pk}/'])
        urls.append('/admin/cadastro/adicionais/novo/')
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, static('css/gestao.css'))
                self.assertEqual(response['Cache-Control'], 'no-store')
                self.assertNotContains(response, 'id="nav-sidebar"')

    def test_roles_and_anonymous_cannot_read_or_write_management(self):
        for user in (self.garcom, None):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for path in ('/admin/', '/admin/equipe/', '/admin/equipe/novo/', '/admin/relatorios/', '/admin/atividades/'):
                with self.subTest(user=user, path=path):
                    self.assertEqual(self.client.get(path).status_code, 403 if user else 302)
            self.assertIn(self.client.post('/admin/equipe/novo/', self.staff_data()).status_code, (302, 403))
        self.assertFalse(User.objects.filter(username='ana.salao').exists())

    def test_staff_creation_ignores_escalation_fields_and_records_event(self):
        response = self.client.post('/admin/equipe/novo/', self.staff_data(is_superuser='on', is_staff='on'))
        self.assertRedirects(response, reverse('gestao:equipe'))
        user = User.objects.get(username='ana.salao')
        self.assertTrue(user.check_password('Senha-Ana-9v!Mz'))
        self.assertEqual(user.perfil.role, 'GARCOM')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(LogEntry.objects.filter(user=self.gestor, object_id=str(user.pk)).exists())
        self.assertNotIn('Senha-Ana', LogEntry.objects.latest('id').change_message)

    def test_weak_mismatched_duplicate_or_unknown_role_does_not_create_account(self):
        for changes in ({'senha': '123', 'confirmar_senha': '123'}, {'confirmar_senha': 'diferente'},
                        {'username': self.gestor.username}, {'role': 'SUPERUSER'}):
            with self.subTest(changes=changes):
                count = User.objects.count()
                response = self.client.post('/admin/equipe/novo/', self.staff_data(**changes))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Não foi possível salvar')
                self.assertEqual(User.objects.count(), count)

    def test_suspend_user_keeps_orders_and_audit(self):
        self.client.post(f'/admin/equipe/{self.garcom.pk}/', {'username': 'garcom', 'first_name': 'João', 'role': 'GARCOM'})
        self.garcom.refresh_from_db()
        self.assertFalse(self.garcom.is_active)
        self.assertTrue(Pedido.objects.filter(pk=self.pedido.pk).exists())

    def test_manager_can_grant_and_revoke_admin_role(self):
        path = f'/admin/equipe/{self.garcom.pk}/'
        data = {'username': 'garcom', 'first_name': 'João', 'role': 'ADMIN', 'is_active': 'on'}
        self.assertEqual(self.client.post(path, data).status_code, 302)
        user = User.objects.get(pk=self.garcom.pk)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.has_perm('restaurante.change_produto'))
        data['role'] = 'GARCOM'
        self.client.post(path, data)
        user = User.objects.get(pk=self.garcom.pk)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.has_perm('restaurante.change_produto'))

    def test_cannot_remove_own_access_or_edit_superuser(self):
        response = self.client.post(f'/admin/equipe/{self.gestor.pk}/',
                                    {'username': 'gestor', 'first_name': 'Gestor', 'role': 'GARCOM'})
        self.assertContains(response, 'próprio acesso')
        self.gestor.refresh_from_db()
        self.assertTrue(self.gestor.is_active)
        self.assertEqual(self.gestor.perfil.role, 'ADMIN')
        for suffix in ('', 'senha/'):
            self.assertEqual(self.client.get(f'/admin/equipe/{self.root.pk}/{suffix}').status_code, 404)
        self.assertNotContains(self.client.get('/admin/equipe/'), 'responsavel')

    def test_password_reset_needs_manager_password_and_invalidates_old_session(self):
        from django.test import Client
        old_session = Client()
        old_session.force_login(self.garcom)
        path = f'/admin/equipe/{self.garcom.pk}/senha/'
        data = {'new_password1': 'Nova-Senha-8vQ!Mz', 'new_password2': 'Nova-Senha-8vQ!Mz', 'senha_gestor': 'errada'}
        self.assertContains(self.client.post(path, data), 'senha de gestor não confere')
        data['senha_gestor'] = 'Acesso-Gestor-9z!mV'
        self.assertEqual(self.client.post(path, data).status_code, 302)
        user = User.objects.get(pk=self.garcom.pk)
        self.assertTrue(user.check_password(data['new_password1']))
        self.assertRedirects(old_session.get('/garcom/'), '/entrar/?next=/garcom/')
        self.assertNotIn(data['new_password1'], LogEntry.objects.latest('id').change_message)

    def test_csrf_is_required_for_management_writes(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.gestor)
        self.assertEqual(client.post('/admin/equipe/novo/', self.staff_data()).status_code, 403)

    def test_cannot_deactivate_an_occupied_table_and_qr_is_preserved(self):
        token = self.mesa.token_uuid
        response = self.client.post(f'/admin/cadastro/mesas/{self.mesa.pk}/', {'numero': 1})
        self.assertContains(response, 'Encerre a sessão')
        self.mesa.refresh_from_db()
        self.assertTrue(self.mesa.ativa)
        self.assertEqual(self.mesa.token_uuid, token)
        self.assertEqual(self.client.get(f'/api/mesas/{self.mesa.pk}/qr-code/').status_code, 200)

    def test_create_table_open_session_and_duplicate_is_rejected(self):
        self.assertEqual(self.client.post('/admin/cadastro/mesas/novo/', {'numero': 2, 'ativa': 'on'}).status_code, 302)
        table = Mesa.objects.get(numero=2)
        self.client.post(f'/admin/mesas/{table.pk}/abrir/')
        self.client.post(f'/admin/mesas/{table.pk}/abrir/')
        self.assertEqual(SessaoMesa.objects.filter(mesa=table, ativa=True).count(), 1)
        self.assertEqual(self.client.post('/admin/cadastro/mesas/novo/', {'numero': 2, 'ativa': 'on'}).status_code, 200)

    def test_price_change_preserves_existing_order_and_rejects_stale_edit(self):
        path = f'/admin/cardapio/{self.produto.pk}/preco/'
        self.assertEqual(self.client.post(path, {'preco': '31.90', 'anterior': '25.00'}).status_code, 302)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.valor_total, Decimal('50.00'))
        self.assertContains(self.client.post(path, {'preco': '40.00', 'anterior': '25.00'}), 'Outra pessoa alterou')
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.preco, Decimal('31.90'))
        self.assertEqual(self.client.post(path, {'preco': '-1', 'anterior': '31.90'}).status_code, 200)

    def test_create_product_category_addon_and_pause_product(self):
        self.client.post('/admin/cadastro/categorias/novo/', {'nome': 'Bebidas', 'ordem': 2})
        category = Categoria.objects.get(nome='Bebidas')
        self.assertEqual(self.client.post('/admin/cadastro/produtos/novo/',
                         {'nome': 'Suco', 'categoria': category.pk, 'descricao': 'Natural', 'preco': '12.90', 'disponivel': 'on'}).status_code, 302)
        product = Produto.objects.get(nome='Suco')
        self.assertEqual(self.client.post('/admin/cadastro/adicionais/novo/',
                         {'produto': product.pk, 'nome': 'Gelo', 'preco': '0.00'}).status_code, 302)
        self.assertTrue(Adicional.objects.filter(produto=product, nome='Gelo').exists())
        self.assertEqual(self.client.get(f'/admin/cardapio/{product.pk}/disponibilidade/').status_code, 405)
        self.client.post(f'/admin/cardapio/{product.pk}/disponibilidade/', {'disponivel': '0'})
        product.refresh_from_db()
        self.assertFalse(product.disponivel)

    def test_invalid_upload_does_not_save_product(self):
        response = self.client.post('/admin/cadastro/produtos/novo/',
            {'nome': 'Foto falsa', 'categoria': self.categoria.pk, 'preco': '1.00',
             'foto': SimpleUploadedFile('foto.png', b'nao-e-imagem', content_type='image/png')})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Produto.objects.filter(nome='Foto falsa').exists())

    def test_product_editor_logs_prices_and_keeps_order_snapshot(self):
        response = self.client.post(f'/admin/cadastro/produtos/{self.produto.pk}/',
            {'nome': 'Prato', 'categoria': self.categoria.pk, 'preco': '28,50', 'preco_anterior': '25.00', 'disponivel': 'on'})
        self.assertEqual(response.status_code, 302)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.preco, Decimal('28.50'))
        self.assertEqual(self.pedido.valor_total, Decimal('50.00'))
        message = LogEntry.objects.latest('id').change_message
        self.assertIn('25.00', message)
        self.assertIn('28.50', message)

    def test_prices_accept_brazilian_decimal_comma(self):
        response = self.client.post(f'/admin/cardapio/{self.produto.pk}/preco/', {'preco': '31,90', 'anterior': '25.00'})
        self.assertEqual(response.status_code, 302)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.preco, Decimal('31.90'))

    def test_resetting_own_password_preserves_manager_session(self):
        response = self.client.post(f'/admin/equipe/{self.gestor.pk}/senha/', {
            'new_password1': 'Nova-Senha-Gestor-9z!mV', 'new_password2': 'Nova-Senha-Gestor-9z!mV',
            'senha_gestor': 'Acesso-Gestor-9z!mV'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_report_totals_and_csv_include_only_paid_bills_in_period(self):
        Conta.objects.create(sessao=self.sessao, valor_total='50.00', pago=True, meio_pagamento='PIX', pago_em=timezone.now())
        today = timezone.localdate().isoformat()
        query = {'inicio': today, 'fim': today}
        response = self.client.get('/admin/relatorios/', query)
        self.assertEqual(response.context['resumo']['total'], Decimal('50.00'))
        self.assertEqual(response.context['resumo']['quantidade'], 1)
        query['exportar'] = 'csv'
        response = self.client.get('/admin/relatorios/', query)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('50,00', response.content.decode('utf-8-sig'))
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertContains(self.client.get('/admin/relatorios/', {'inicio': 'invalido'}), 'Informe uma data válida')

    def test_cancellation_uses_existing_transition_rules(self):
        self.client.post(f'/admin/pedidos/{self.pedido.pk}/cancelar/')
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'CANCELADO')
        self.assertEqual(self.pedido.historico_status.last().alterado_por, self.gestor)
        Pedido.objects.filter(pk=self.pedido.pk).update(status='EM_PREPARACAO')
        self.client.post(f'/admin/pedidos/{self.pedido.pk}/cancelar/')
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, 'EM_PREPARACAO')

    def test_empty_states_and_filters_are_useful(self):
        self.assertContains(self.client.get('/admin/equipe/', {'q': 'inexistente'}), 'Nenhuma pessoa encontrada')
        self.assertContains(self.client.get('/admin/cardapio/', {'q': 'inexistente'}), 'Nenhum produto encontrado')
        self.assertContains(self.client.get('/admin/mesas/', {'q': 'x' * 2000}), 'Nenhuma mesa encontrada')
        self.assertContains(self.client.get('/admin/pedidos/', {'inicio': '2030-01-01', 'fim': '2020-01-01'}), 'data inicial')
