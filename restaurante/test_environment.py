from io import StringIO
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from .models import Mesa, Produto


class SeedTests(TestCase):
    def test_seed_repeat_preserves_prices_users_and_tables(self):
        call_command('seed_data', stdout=StringIO())
        self.assertFalse(User.objects.exists())
        produto = Produto.objects.get(nome='Hambúrguer Clássico')
        produto.preco = '39.90'
        produto.save()
        call_command('seed_data', stdout=StringIO())
        produto.refresh_from_db()
        self.assertEqual(str(produto.preco), '39.90')
        self.assertEqual(Mesa.objects.count(), 10)
        self.assertEqual(Produto.objects.count(), 15)

    def test_demo_users_are_explicit_and_do_not_reset_passwords(self):
        call_command('seed_data', demo_users=True, stdout=StringIO())
        admin = User.objects.get(username='admin')
        admin.set_password('uma-senha-alterada')
        admin.save()
        call_command('seed_data', demo_users=True, stdout=StringIO())
        admin.refresh_from_db()
        self.assertTrue(admin.check_password('uma-senha-alterada'))
