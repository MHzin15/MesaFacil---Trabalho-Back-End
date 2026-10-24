from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from io import BytesIO
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient
from .models import Mesa, SessaoMesa, Categoria, Produto, Pedido, HistoricoStatusPedido, Perfil


class AcceptanceTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1)
        self.sessao = SessaoMesa.objects.create(mesa=self.mesa)
        self.produto = Produto.objects.create(categoria=Categoria.objects.create(nome='Lanches'), nome='Hambúrguer', preco='32.90')
        self.admin = User.objects.create_superuser('aceite', password='senha-local-de-teste')
        self.client = APIClient()
        self.client.get(f'/api/mesa/{self.mesa.token_uuid}/')

    def test_price_change_requires_confirmation_and_rolls_back_unconfirmed_order(self):
        payload = {'mesa_uuid': str(self.mesa.token_uuid), 'sessao_id': self.sessao.pk,
            'total_esperado': '32.90', 'itens': [{'produto_id': self.produto.pk, 'quantidade': 1}]}
        Produto.objects.filter(pk=self.produto.pk).update(preco='39.90')
        response = self.client.post('/api/pedidos/criar/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(HistoricoStatusPedido.objects.exists())
        payload['total_esperado'] = '39.90'
        self.assertEqual(self.client.post('/api/pedidos/criar/', payload, format='json').status_code, 201)
        self.assertEqual(Pedido.objects.get().valor_total, Decimal('39.90'))

    def test_occupied_table_cannot_be_disabled_from_api_or_admin(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/mesas/{self.mesa.pk}/', {'ativa': False}, format='json').status_code, 400)
        self.client.force_authenticate(None)
        self.client.force_login(self.admin)
        response = self.client.post(f'/admin/restaurante/mesa/{self.mesa.pk}/change/', {'numero':1, '_save':'Salvar'})
        self.assertEqual(response.status_code, 200)
        self.mesa.refresh_from_db()
        self.assertTrue(self.mesa.ativa)

    def test_photos_work_with_debug_false_and_qr_directory_stays_private(self):
        temp_root = Path(__file__).resolve().parents[1] / '.tmp'
        temp_root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=temp_root) as directory, override_settings(MEDIA_ROOT=Path(directory), DEBUG=False):
            self.assertTrue(Path(directory).resolve().is_relative_to(temp_root.resolve()))
            content = BytesIO()
            Image.new('RGB', (10, 10), '#ae452c').save(content, format='PNG')
            self.produto.foto.save('foto.png', SimpleUploadedFile('foto.png', content.getvalue(), content_type='image/png'))
            response = self.client.get(self.produto.foto.url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'image/png')
            self.assertTrue(b''.join(response.streaming_content))
            self.assertEqual(self.client.get('/media/qrcodes/mesa_1_qrcode.png').status_code, 404)

    def test_admin_cannot_move_existing_profile_to_another_user(self):
        other = User.objects.create_user('outro-usuario')
        self.client.force_login(self.admin)
        profile = self.admin.perfil
        self.client.post(f'/admin/restaurante/perfil/{profile.pk}/change/',
                         {'user': other.pk, 'role': 'ADMIN', '_save': 'Salvar'})
        profile.refresh_from_db()
        self.assertEqual(profile.user_id, self.admin.pk)
        other.refresh_from_db()
        self.assertFalse(other.is_staff)

    def test_regular_admin_can_create_team_user_without_privilege_escalation(self):
        manager = User.objects.create_user('administrador-comum', password='senha-local-de-teste')
        Perfil.objects.create(user=manager, role='ADMIN')
        self.client.force_login(manager)
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'nova-cozinha', 'password1': 'CozinhaEquipe!2026', 'password2': 'CozinhaEquipe!2026',
            'usable_password': 'true', 'perfil-TOTAL_FORMS': '1', 'perfil-INITIAL_FORMS': '0',
            'perfil-MIN_NUM_FORMS': '0', 'perfil-MAX_NUM_FORMS': '1', 'perfil-0-role': 'COZINHA',
            'is_superuser': 'on', 'is_staff': 'on', '_save': 'Salvar',
        })
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(username='nova-cozinha')
        self.assertEqual(created.perfil.role, 'COZINHA')
        self.assertTrue(created.check_password('CozinhaEquipe!2026'))
        self.assertFalse(created.is_superuser)
        self.assertFalse(created.is_staff)
        self.assertRedirects(self.client.get(f'/admin/auth/user/{self.admin.pk}/change/'), '/admin/', fetch_redirect_response=False)
        self.assertRedirects(self.client.get(f'/admin/restaurante/perfil/{self.admin.perfil.pk}/change/'), '/admin/', fetch_redirect_response=False)
