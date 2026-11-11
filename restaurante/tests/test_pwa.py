from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.test import TestCase
from PIL import Image


class PwaTests(TestCase):
    def test_manifest_exposes_root_scope_and_valid_icons(self):
        response = self.client.get('/manifest.webmanifest')
        self.assertEqual(response['Content-Type'], 'application/manifest+json')
        manifest = response.json()
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(manifest['scope'], '/')
        self.assertEqual(manifest['lang'], 'pt-BR')
        # URLs podem conter hashes no ambiente de produção.
        for name, size in [('icon-192.png', 192), ('icon-512.png', 512), ('maskable-512.png', 512)]:
            image = Image.open(finders.find('icons/' + name))
            self.assertEqual(image.size, (size, size))
            image.verify()

    def test_offline_page_is_identical_for_guest_and_logged_in_user(self):
        guest = self.client.get('/offline/').content
        user = User.objects.create_user('nome-que-nao-pode-ir-ao-cache')
        self.client.force_login(user)
        authenticated = self.client.get('/offline/')
        self.assertEqual(authenticated.content, guest)
        self.assertNotContains(authenticated, user.username)
        self.assertNotContains(authenticated, 'csrf-token')
        self.assertContains(authenticated, 'Nenhum envio será feito automaticamente')

    def test_service_worker_has_correct_mime_scope_and_refresh_policy(self):
        response = self.client.get('/service-worker.js')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertEqual(response['Service-Worker-Allowed'], '/')
        self.assertEqual(response['Cache-Control'], 'no-cache')
        self.assertNotIn(b'{% static', response.content)

    def test_root_includes_installation_resources(self):
        response = self.client.get('/')
        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, 'id="install-app"')
        self.assertContains(response, 'js/pwa.')
