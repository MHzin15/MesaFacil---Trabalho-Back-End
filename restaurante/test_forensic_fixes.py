"""Regressões dos defeitos reproduzidos na auditoria de 02/11."""
import logging
import os
import sys
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import User
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from .logging import PrivateTokenFilter, redact
from .models import Categoria, Mesa, Pedido, Perfil, Produto, SessaoMesa
from . import test_private_tabs as fixtures


class ImmutableOrderTests(TestCase):
    setUp = fixtures.PrivateTabsTests.setUp
    visitante = fixtures.PrivateTabsTests.visitante
    post = fixtures.PrivateTabsTests.post
    def test_retry_keeps_original_session_and_cannot_open_another_while_in_use(self):
        context = self.a.get(self.base).data
        data = {'mesa_uuid': str(self.mesa.token_uuid), 'sessao_id': None,
                'atendimento_id': context['atendimento_id'], 'chave_envio': str(uuid4()),
                'itens': [{'produto_id': self.produto.pk, 'quantidade': 1}]}
        first = self.post(self.a, '/api/pedidos/criar/', data)
        self.assertEqual(first.status_code, 201)
        self.post(self.a, self.base + 'novo-atendimento/')
        second_context = self.a.get(self.base).data
        self.assertEqual(context['atendimento_id'], second_context['atendimento_id'])
        retry = self.post(self.a, '/api/pedidos/criar/', data)
        self.assertEqual(retry.status_code, 201, retry.data)
        self.assertEqual(retry.data['id'], first.data['id'])
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(SessaoMesa.objects.count(), 1)
        # Consulta e fechamento também permanecem no destino indicado pela aba A.
        own = f"?atendimento_id={context['atendimento_id']}"
        self.assertEqual(self.a.get(self.base + 'conta/' + own).data['sessao_id'], first.data['sessao'])
        self.assertEqual(self.post(self.a, self.base + 'solicitar-conta/' + own).status_code, 200)
        self.assertTrue(SessaoMesa.objects.get().conta_solicitada)
        self.assertEqual(self.a.get(self.base).data['sessao_id'], first.data['sessao'])
        self.assertEqual(self.post(self.b, '/api/pedidos/criar/', data).status_code, 403)

    def test_old_first_order_without_immutable_identity_requires_reload(self):
        result = self.post(self.a, '/api/pedidos/criar/', {
            'mesa_uuid': str(self.mesa.token_uuid), 'sessao_id': None,
            'itens': [{'produto_id': self.produto.pk, 'quantidade': 1}]})
        self.assertEqual(result.status_code, 409)
        self.assertFalse(Pedido.objects.exists())


class ManagementFixesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user('gestor-correcao', password='Gestor-9Z!forte')
        Perfil.objects.create(user=cls.manager, role='ADMIN')
        cls.other = User.objects.create_user('cozinha-correcao', password='Cozinha-9Z!forte')
        Perfil.objects.create(user=cls.other, role='COZINHA')
        cls.category = Categoria.objects.create(nome='Teste')
        cls.product = Produto.objects.create(categoria=cls.category, nome='Prato', preco='10.00')

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.manager)

    def test_native_user_and_profile_urls_cannot_bypass_manager_guards(self):
        cases = [
            (f'/admin/auth/user/{self.other.pk}/password/', {'password1': 'Nova-8x!forte', 'password2': 'Nova-8x!forte'}),
            (f'/admin/auth/user/{self.manager.pk}/change/', {'username': self.manager.username}),
            (f'/admin/restaurante/perfil/{self.manager.perfil.pk}/change/', {'role': 'COZINHA'}),
        ]
        for url, data in cases:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, data).status_code, 403)
        self.other.refresh_from_db()
        self.manager.refresh_from_db()
        self.assertTrue(self.other.check_password('Cozinha-9Z!forte'))
        self.assertTrue(self.manager.is_active)
        self.assertEqual(self.manager.perfil.role, 'ADMIN')

    def test_old_full_editor_cannot_overwrite_a_quick_price_change(self):
        url = f'/admin/cadastro/produtos/{self.product.pk}/'
        form = self.client.get(url).context['form']
        old = str(form['preco_anterior'].value())
        self.client.post(f'/admin/cardapio/{self.product.pk}/preco/', {'preco': '12.00', 'anterior': old})
        response = self.client.post(url, {'nome': 'Prato', 'descricao': 'Nova descrição',
            'categoria': self.category.pk, 'preco': '10.00', 'preco_anterior': old, 'disponivel': 'on'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].non_field_errors())
        self.product.refresh_from_db()
        self.assertEqual(str(self.product.preco), '12.00')
        self.assertEqual(self.product.descricao, '')

    def test_table_delete_with_history_returns_conflict_and_keeps_records(self):
        table = Mesa.objects.create(numero=1)
        tab = SessaoMesa.objects.create(mesa=table, ativa=False)
        self.assertEqual(self.client.delete(f'/api/mesas/{table.pk}/').status_code, 409)
        self.assertTrue(Mesa.objects.filter(pk=table.pk).exists())
        self.assertTrue(SessaoMesa.objects.filter(pk=tab.pk).exists())
        empty = Mesa.objects.create(numero=2)
        self.assertEqual(self.client.delete(f'/api/mesas/{empty.pk}/').status_code, 204)

    def test_valid_oversized_photo_rejected_by_api_and_management(self):
        stream = BytesIO()
        Image.frombytes('RGB', (1536, 1536), os.urandom(1536 * 1536 * 3)).save(stream, 'PNG')
        data = stream.getvalue()
        self.assertGreater(len(data), 5 * 1024 * 1024)
        (settings.BASE_DIR / '.tmp').mkdir(exist_ok=True)
        with TemporaryDirectory(dir=settings.BASE_DIR / '.tmp') as root, override_settings(MEDIA_ROOT=root):
            for url in ('/api/produtos/', '/admin/cadastro/produtos/novo/'):
                upload = SimpleUploadedFile('foto.png', data, content_type='image/png')
                result = self.client.post(url, {'nome': 'Grande', 'categoria': self.category.pk,
                    'preco': '10.00', 'foto': upload}, format='multipart')
                self.assertIn(result.status_code, (200, 400))
                self.assertFalse(Produto.objects.filter(nome='Grande').exists())


class OperationalFixesTests(TestCase):
    def test_readiness_reports_db_failure_while_liveness_stays_up(self):
        self.assertEqual(self.client.get('/health/ready/').status_code, 200)
        with patch('restaurante.health.connection.cursor', side_effect=DatabaseError('synthetic-private-error')):
            response = self.client.get('/health/ready/')
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(b'synthetic-private-error', response.content)
            self.assertEqual(self.client.get('/health/live/').status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_invite_tokens_redacted_in_messages_paths_queries_and_tracebacks(self):
        token = str(uuid4())
        value = f'/convite/{token}/ /api/mesa/public/convites/{token}/qr/?atendimento_id={token}'
        self.assertNotIn(token, redact(value))
        record = logging.LogRecord('django.request', logging.ERROR, __file__, 1, 'Not Found: %s', (value,), None)
        self.assertTrue(PrivateTokenFilter().filter(record))
        self.assertNotIn(token, record.getMessage())
        try:
            raise ValueError(value)
        except ValueError:
            failure = logging.LogRecord('django.request', logging.ERROR, __file__, 1,
                                        'Falha em %s', (value,), sys.exc_info())
            PrivateTokenFilter().filter(failure)
        self.assertNotIn(token, failure.getMessage())
        self.assertIsNone(failure.exc_info)
