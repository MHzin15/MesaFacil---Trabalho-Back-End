from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Perfil


@receiver(post_save, sender=get_user_model())
def perfil_superusuario(sender, instance, created, **kwargs):
    if created and instance.is_superuser:
        Perfil.objects.get_or_create(user=instance, defaults={'role': 'ADMIN'})


@receiver(post_save, sender=Perfil)
def sincronizar_perfil(sender, instance, **kwargs):
    user = instance.user
    group, _ = Group.objects.get_or_create(name='Administradores MesaFácil')
    permissions = Permission.objects.filter(content_type__app_label='restaurante') | Permission.objects.filter(
        content_type__app_label='auth', codename__in=['add_user', 'change_user', 'view_user'])
    group.permissions.set(permissions)
    if instance.role == 'ADMIN':
        user.groups.add(group)
    else:
        user.groups.remove(group)
    staff = user.is_superuser or instance.role == 'ADMIN'
    if user.is_staff != staff:
        user.is_staff = staff
        user.save(update_fields=['is_staff'])
