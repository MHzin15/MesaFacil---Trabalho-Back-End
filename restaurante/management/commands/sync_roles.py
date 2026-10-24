from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from restaurante.models import Perfil


class Command(BaseCommand):
    help = 'Sincroniza perfis existentes com o acesso ao admin sem promover superusuários.'

    def handle(self, *args, **options):
        for user in get_user_model().objects.filter(is_superuser=True):
            Perfil.objects.get_or_create(user=user, defaults={'role': 'ADMIN'})
        for profile in Perfil.objects.select_related('user'):
            profile.save()
        self.stdout.write(self.style.SUCCESS('Perfis e permissões sincronizados.'))
