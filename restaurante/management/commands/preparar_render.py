"""Prepara os dados e o primeiro acesso do ambiente de testes no Render."""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Prepara o cardápio de teste e cria o primeiro admin, sem redefinir acessos existentes.'

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin').strip()
        if not username:
            raise CommandError('Defina DJANGO_SUPERUSER_USERNAME no Render.')

        user = user_model.objects.filter(username=username).first()
        if user is not None and not user.is_superuser:
            raise CommandError('O nome do admin já pertence a um usuário comum. Escolha outro nome no Render.')
        if user is None:
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
            if not password:
                raise CommandError('Defina DJANGO_SUPERUSER_PASSWORD no Render para criar o primeiro admin.')
            user = user_model(username=username, email=os.environ.get('DJANGO_SUPERUSER_EMAIL', ''))
            try:
                validate_password(password, user)
            except ValidationError:
                raise CommandError('A senha inicial é fraca. Use uma senha longa, única e diferente do usuário.') from None
            user_model.objects.create_superuser(username=username, email=user.email, password=password)
            self.stdout.write(self.style.SUCCESS('Primeiro administrador criado.'))
        else:
            self.stdout.write('Administrador existente preservado; senha não alterada.')

        call_command('seed_data', demo_images=True, stdout=self.stdout)
        call_command('sync_roles', stdout=self.stdout)
