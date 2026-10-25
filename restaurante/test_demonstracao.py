from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from .models import Adicional, Categoria, Mesa, Perfil, Produto


@override_settings(PUBLIC_BASE_URL='http://localhost:8000', ALLOWED_HOSTS=['localhost'],
                   CSRF_TRUSTED_ORIGINS=['http://localhost:8000'])
class DemonstracaoTests(TestCase):
    def setUp(self):
        Mesa.objects.create(numero=1)
        self.produto = Produto.objects.create(categoria=Categoria.objects.create(nome='Lanches'),
            nome='Lanche', descricao='Descrição do lanche', preco='32.90', foto='produtos/lanche.png')
        Adicional.objects.create(produto=self.produto, nome='Bacon', preco='5.00')
        User.objects.create_superuser('gestor', password='senha-de-teste-segura')
        for nome, role in [('preparo', 'COZINHA'), ('salao', 'GARCOM')]:
            user = User.objects.create_user(nome, password='senha-de-teste-segura')
            Perfil.objects.create(user=user, role=role)

    def executar(self, **options):
        saida = StringIO()
        self.saida = saida
        # A suíte rápida usa SQLite explicitamente; só o gate de infraestrutura é
        # simulado aqui. A suíte final repete os cenários em PostgreSQL real.
        with patch.object(connection, 'vendor', 'postgresql'), patch(
            'django.core.files.storage.FileSystemStorage.exists', return_value=True
        ):
            call_command('verificar_demonstracao', stdout=saida, **options)
        return saida.getvalue()

    def test_local_check_passes_without_writing_or_leaking_credentials(self):
        with CaptureQueriesContext(connection) as queries:
            saida = self.executar()
        self.assertIn('Pré-checagem aprovada', saida)
        self.assertIn('não valida acesso ou instalação pelo celular', saida)
        self.assertNotIn('senha-de-teste-segura', saida)
        self.assertNotIn('produtos/lanche.png', saida)
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP')) for q in queries))

    def test_inactive_waiter_does_not_count_as_team_ready(self):
        User.objects.filter(username='salao').update(is_active=False)
        with self.assertRaisesMessage(CommandError, 'pendência'):
            self.executar()

    def test_missing_photo_does_not_pass_precheck(self):
        self.produto.foto = ''
        self.produto.save()
        with self.assertRaisesMessage(CommandError, 'pendência'):
            self.executar()

    def test_pending_migrations_skip_queries_to_application_tables(self):
        with patch('restaurante.management.commands.verificar_demonstracao.MigrationExecutor') as executor:
            executor.return_value.migration_plan.return_value = [('migration', False)]
            with patch.object(Mesa.objects, 'filter', side_effect=AssertionError('Não consultar tabelas antes de migrar')):
                with self.assertRaisesMessage(CommandError, 'pendência'):
                    self.executar()

    @override_settings(CSRF_TRUSTED_ORIGINS=['http://outro-host:8000'])
    def test_wrong_origin_is_reported(self):
        with self.assertRaisesMessage(CommandError, 'pendência'):
            self.executar()
        self.assertIn('PENDENTE: Incluir a origem', self.saida.getvalue())

    def test_localhost_cannot_pass_as_physical_phone_ready(self):
        with self.assertRaisesMessage(CommandError, 'pendência'):
            self.executar(celular=True)
        self.assertIn('PENDENTE: Usar HTTPS', self.saida.getvalue())

    @override_settings(PUBLIC_BASE_URL='https://mesa.example.org', ALLOWED_HOSTS=['mesa.example.org'],
        CSRF_TRUSTED_ORIGINS=['https://mesa.example.org'], DEBUG=False,
        SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_https_configuration_requires_changed_demo_credentials(self):
        user = User.objects.create_user('cozinha', password='cozinha123')
        with self.assertRaisesMessage(CommandError, 'pendência'):
            self.executar(celular=True)
        user.set_password('senha-de-teste-alterada')
        user.save()
        self.assertIn('Pré-checagem aprovada', self.executar(celular=True))

    @override_settings(PUBLIC_BASE_URL='https://usuario:segredo@mesa.example.org:errada')
    def test_malformed_url_is_reported_without_printing_it(self):
        with self.assertRaisesMessage(CommandError, 'pendência') as erro:
            self.executar()
        self.assertNotIn('segredo', self.saida.getvalue() + str(erro.exception))
