"""Inicialização repetível e configuração HTTPS do deploy de teste."""
import json
import os
from io import StringIO
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from .demo_images import criar_imagens
from .models import Mesa, Produto


class RenderBootstrapTests(TestCase):
    def setUp(self):
        temp_root = Path(__file__).resolve().parents[1] / '.tmp'
        temp_root.mkdir(exist_ok=True)
        directory = TemporaryDirectory(dir=temp_root)
        self.assertTrue(Path(directory.name).resolve().is_relative_to(temp_root.resolve()))
        self.addCleanup(directory.cleanup)
        self.settings_override = self.settings(MEDIA_ROOT=Path(directory.name))
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        environment = patch.dict(os.environ, {
            'DJANGO_SUPERUSER_USERNAME': 'render-admin',
            'DJANGO_SUPERUSER_PASSWORD': 'Teste-Render-8Zq!mR2vW7',
        })
        environment.start()
        self.addCleanup(environment.stop)

    def prepare(self):
        output = StringIO()
        call_command('preparar_render', stdout=output)
        return output.getvalue()

    def test_first_start_creates_admin_catalog_and_images_without_demo_users(self):
        output = self.prepare()
        admin = get_user_model().objects.get(username='render-admin')
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password(os.environ['DJANGO_SUPERUSER_PASSWORD']))
        self.assertEqual(admin.perfil.role, 'ADMIN')
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(Mesa.objects.count(), 10)
        self.assertEqual(Produto.objects.count(), 15)
        self.assertTrue(all(p.foto and p.foto.storage.exists(p.foto.name) for p in Produto.objects.all()))
        self.assertNotIn(os.environ['DJANGO_SUPERUSER_PASSWORD'], output)

    def test_restart_preserves_password_prices_and_table_identifiers(self):
        self.prepare()
        admin = get_user_model().objects.get(username='render-admin')
        admin.set_password('Senha-alterada-no-admin-9vQ!')
        admin.save()
        produto = Produto.objects.first()
        produto.preco = '87.65'
        produto.save()
        identifiers = list(Mesa.objects.values_list('token_uuid', flat=True))
        with patch.dict(os.environ, {'DJANGO_SUPERUSER_PASSWORD': ''}):
            self.prepare()
        admin.refresh_from_db()
        produto.refresh_from_db()
        self.assertTrue(admin.check_password('Senha-alterada-no-admin-9vQ!'))
        self.assertEqual(str(produto.preco), '87.65')
        self.assertEqual(list(Mesa.objects.values_list('token_uuid', flat=True)), identifiers)
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_missing_or_weak_initial_password_stops_without_creating_data(self):
        for password in ('', 'admin123'):
            with self.subTest(password=password), patch.dict(os.environ, {'DJANGO_SUPERUSER_PASSWORD': password}):
                with self.assertRaises(CommandError):
                    self.prepare()
                self.assertFalse(get_user_model().objects.exists())
                self.assertFalse(Produto.objects.exists())

    def test_existing_regular_user_is_not_promoted(self):
        user = get_user_model().objects.create_user('render-admin', password='Senha-de-usuario-8vQ!')
        with self.assertRaises(CommandError):
            self.prepare()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('Senha-de-usuario-8vQ!'))

    def test_restart_recreates_lost_demo_image_with_same_path(self):
        self.prepare()
        produto = Produto.objects.first()
        name = produto.foto.name
        produto.foto.storage.delete(name)
        self.assertFalse(produto.foto.storage.exists(name))
        self.prepare()
        produto.refresh_from_db()
        self.assertEqual(produto.foto.name, name)
        self.assertTrue(produto.foto.storage.exists(name))

    def test_custom_upload_is_preserved_even_when_its_file_is_missing(self):
        self.prepare()
        produto = Produto.objects.first()
        produto.foto.save('foto-do-restaurante.png', ContentFile(b'foto-enviada'))
        name = produto.foto.name
        criar_imagens()
        with produto.foto.storage.open(name) as uploaded:
            self.assertEqual(uploaded.read(), b'foto-enviada')
        produto.foto.storage.delete(name)
        criar_imagens()
        produto.refresh_from_db()
        self.assertEqual(produto.foto.name, name)
        self.assertFalse(produto.foto.storage.exists(name))


class RenderSettingsTests(SimpleTestCase):
    def load_settings(self, **overrides):
        environment = os.environ.copy()
        for key in ('RENDER', 'RENDER_EXTERNAL_HOSTNAME', 'PUBLIC_BASE_URL', 'ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS'):
            environment.pop(key, None)
        environment.update({
            'SECRET_KEY': 'test-only-render-settings',
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'DEBUG': 'False',
            **overrides,
        })
        # Ignora o .env pessoal para conferir os padrões reais de uma publicação.
        script = """
import importlib, json
from unittest.mock import patch
with patch('environ.Env.read_env'):
    settings = importlib.import_module('core.settings')
print(json.dumps({key: getattr(settings, key, None) for key in (
    'ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS', 'PUBLIC_BASE_URL',
    'SECURE_PROXY_SSL_HEADER', 'SECURE_SSL_REDIRECT', 'SESSION_COOKIE_SECURE',
    'CSRF_COOKIE_SECURE', 'DATABASES')}))
"""
        result = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1],
                                env=environment, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_render_uses_its_https_domain_for_hosts_csrf_and_qr_codes(self):
        settings = self.load_settings(RENDER='true', RENDER_EXTERNAL_HOSTNAME='mesafacil-test.onrender.com')
        self.assertIn('mesafacil-test.onrender.com', settings['ALLOWED_HOSTS'])
        self.assertNotIn('*', settings['ALLOWED_HOSTS'])
        self.assertIn('https://mesafacil-test.onrender.com', settings['CSRF_TRUSTED_ORIGINS'])
        self.assertEqual(settings['PUBLIC_BASE_URL'], 'https://mesafacil-test.onrender.com')
        self.assertEqual(settings['SECURE_PROXY_SSL_HEADER'], ['HTTP_X_FORWARDED_PROTO', 'https'])
        self.assertTrue(settings['SECURE_SSL_REDIRECT'])
        self.assertTrue(settings['SESSION_COOKIE_SECURE'])
        self.assertTrue(settings['CSRF_COOKIE_SECURE'])
        self.assertEqual(settings['DATABASES']['default']['ENGINE'], 'django.db.backends.postgresql')

    def test_custom_domain_and_explicit_origins_are_preserved(self):
        settings = self.load_settings(
            RENDER='true', RENDER_EXTERNAL_HOSTNAME='mesafacil-test.onrender.com',
            PUBLIC_BASE_URL='https://mesa.example.com/', ALLOWED_HOSTS='mesa.example.com',
            CSRF_TRUSTED_ORIGINS='https://mesa.example.com',
        )
        self.assertEqual(settings['PUBLIC_BASE_URL'], 'https://mesa.example.com')
        self.assertEqual(settings['ALLOWED_HOSTS'], ['mesa.example.com', 'mesafacil-test.onrender.com'])
        self.assertEqual(settings['CSRF_TRUSTED_ORIGINS'], ['https://mesa.example.com', 'https://mesafacil-test.onrender.com'])

    def test_local_development_keeps_local_url_and_does_not_trust_proxy_headers(self):
        settings = self.load_settings(DEBUG='True')
        self.assertEqual(settings['PUBLIC_BASE_URL'], 'http://localhost:8000')
        self.assertIsNone(settings['SECURE_PROXY_SSL_HEADER'])
        self.assertFalse(settings['SESSION_COOKIE_SECURE'])
