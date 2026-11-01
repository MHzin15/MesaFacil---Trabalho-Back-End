"""Regressões da auditoria de segurança e dos limites de consultas."""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from .models import (
    Adicional, Categoria, Conta, ItemPedido, ItemPedidoAdicional, LoginRateBucket,
    Mesa, Pedido, Produto, SessaoMesa,
)
from .serializers import MesaSerializer, PedidoSerializer, ProdutoSerializer


class PasswordPolicyTests(SimpleTestCase):
    def test_weak_passwords_are_rejected_and_long_password_is_accepted(self):
        for password in ('admin123', '123456789012', 'abc'):
            with self.subTest(password=password), self.assertRaises(ValidationError):
                validate_password(password)
        validate_password('Restaurante!8vQ-7nM-2xZ')


class AuditSecurityTests(TestCase):
    @override_settings(DEBUG=False)
    def test_production_seed_rejects_demo_accounts_before_writing(self):
        with self.assertRaises(CommandError):
            call_command('seed_data', demo_users=True, stdout=StringIO())
        self.assertFalse(User.objects.exists())
        self.assertFalse(Mesa.objects.exists())

    def test_existing_password_still_authenticates(self):
        User.objects.create_user('legado', password='admin123')
        self.assertTrue(self.client.login(username='legado', password='admin123'))

    @override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=256)
    def test_large_json_rejected_before_creating_order(self):
        response = APIClient().post('/api/pedidos/criar/', {'observacao': 'a' * 257}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Pedido.objects.exists())

    def test_deeply_nested_json_is_a_client_error(self):
        response = APIClient().post('/api/pedidos/criar/',
                                    '[' * 2000 + '0' + ']' * 2000, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_images_use_content_mime_and_legacy_html_cannot_execute(self):
        temp_root = Path(__file__).resolve().parents[1] / '.tmp'
        temp_root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=temp_root) as directory, self.settings(MEDIA_ROOT=Path(directory)):
            self.assertTrue(Path(directory).resolve().is_relative_to(temp_root.resolve()))
            media = Path(directory) / 'produtos'
            media.mkdir()
            content = BytesIO()
            Image.new('RGB', (2, 2)).save(content, format='PNG')
            data = content.getvalue() + b'<script>alert(document.domain)</script>'
            (media / 'legado.html').write_bytes(data)
            response = self.client.get('/media/produtos/legado.html')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
            self.assertIn('sandbox', response['Content-Security-Policy'])
            self.assertEqual(b''.join(response.streaming_content), data)
            (media / 'invalida.png').write_text('<script>alert(1)</script>')
            self.assertEqual(self.client.get('/media/produtos/invalida.png').status_code, 404)
            self.assertEqual(self.client.get('/media/produtos/../privado.txt').status_code, 400)

    def test_current_upload_validation_already_rejects_html_extension(self):
        category = Categoria.objects.create(nome='Fotos')
        content = BytesIO()
        Image.new('RGB', (2, 2)).save(content, format='PNG')
        serializer = ProdutoSerializer(data={
            'categoria': category.pk, 'nome': 'Foto', 'preco': '1.00',
            'foto': SimpleUploadedFile('foto.html', content.getvalue(), content_type='image/png'),
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('foto', serializer.errors)


@override_settings(LOGIN_RATE_LIMIT_ACCOUNT=2, LOGIN_RATE_LIMIT_IP=4)
class LoginRateTests(TestCase):
    def test_both_logins_share_account_limit_and_do_not_store_identifiers(self):
        self.assertEqual(self.client.post('/entrar/', {'username': 'alvo', 'password': 'errada'}).status_code, 200)
        self.assertEqual(self.client.post('/admin/login/', {'username': 'ALVO', 'password': 'errada'}).status_code, 200)
        response = self.client.post('/entrar/', {'username': 'ａｌｖｏ', 'password': 'errada'}, REMOTE_ADDR='192.0.2.2')
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertTrue(all(len(key) == 64 and 'alvo' not in key for key in LoginRateBucket.objects.values_list('key', flat=True)))

    def test_ip_limit_covers_many_usernames_and_ignores_forwarded_header(self):
        for number in range(4):
            self.assertEqual(self.client.post('/entrar/', {'username': f'user{number}', 'password': 'x'},
                                              HTTP_X_FORWARDED_FOR=f'192.0.2.{number}').status_code, 200)
        response = self.client.post('/admin/login/', {'username': 'outro', 'password': 'x'}, HTTP_X_FORWARDED_FOR='198.51.100.1')
        self.assertEqual(response.status_code, 429)

    def test_limit_expires_and_normal_login_keeps_redirect(self):
        User.objects.create_user('equipe', password='senha-de-teste')
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        with patch('restaurante.middleware.timezone.now', return_value=now):
            for _ in range(2):
                self.client.post('/entrar/', {'username': 'equipe', 'password': 'errada'})
            self.assertEqual(self.client.post('/entrar/', {'username': 'equipe', 'password': 'senha-de-teste'}).status_code, 429)
        with patch('restaurante.middleware.timezone.now', return_value=now + timedelta(minutes=6)):
            self.assertRedirects(self.client.post('/entrar/', {'username': 'equipe', 'password': 'senha-de-teste'}),
                                 '/painel/', fetch_redirect_response=False)
        self.assertFalse(LoginRateBucket.objects.filter(expires_at__lte=now + timedelta(minutes=6)).exists())

    def test_csrf_rejection_does_not_consume_login_quota(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post('/entrar/', {'username': 'alvo', 'password': 'x'}).status_code, 403)
        self.assertFalse(LoginRateBucket.objects.exists())


class QueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Produto.objects.create(categoria=Categoria.objects.create(nome='Teste'), nome='Produto', preco='90.00')
        cls.extra = Adicional.objects.create(produto=cls.product, nome='Extra', preco='70.00')
        cls.sessions = []
        for number in range(1, 11):
            table = Mesa.objects.create(numero=number)
            SessaoMesa.objects.create(mesa=table, ativa=False)
            session = SessaoMesa.objects.create(mesa=table, conta_solicitada=number == 1)
            cls.sessions.append(session)
            for status in ('ENTREGUE', 'CANCELADO'):
                order = Pedido.objects.create(sessao=session, status=status)
                for _ in range(3):
                    item = ItemPedido.objects.create(pedido=order, produto=cls.product, quantidade=2, preco_unitario='10.10')
                    for _ in range(2):
                        ItemPedidoAdicional.objects.create(item_pedido=item, adicional=cls.extra, preco='0.25')

    def test_table_serialization_has_constant_query_count(self):
        with self.assertNumQueries(2):
            result = MesaSerializer(Mesa.objects.com_sessao_ativa(), many=True).data
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0]['status'], 'aguardando_conta')
        self.assertEqual(result[1]['sessao_ativa_id'], self.sessions[1].pk)

    def test_order_serialization_has_constant_query_count_and_historical_prices(self):
        with self.assertNumQueries(3):
            result = PedidoSerializer(Pedido.objects.para_exibicao(), many=True).data
        self.assertEqual(len(result), 20)
        self.assertTrue(all(order['valor_total'] == '63.60' for order in result))

    def test_bill_total_uses_two_queries_without_double_counting_addons(self):
        bill = Conta(sessao=self.sessions[0])
        with self.assertNumQueries(2):
            self.assertEqual(bill.calcular_total(), Decimal('63.60'))
        empty = SessaoMesa.objects.create(mesa=Mesa.objects.create(numero=11))
        self.assertEqual(empty.total_consumo(), Decimal('0.00'))

    def test_session_cache_does_not_leak_to_transactional_reads(self):
        session = self.sessions[0]
        table = Mesa.objects.com_sessao_ativa().get(pk=session.mesa_id)
        self.assertEqual(table.sessao_ativa.pk, session.pk)
        SessaoMesa.objects.filter(pk=session.pk).update(ativa=False)
        self.assertIsNone(Mesa.objects.get(pk=table.pk).sessao_ativa)
