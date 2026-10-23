from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Permite acesso apenas a usuários com perfil ADMIN."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.role == 'ADMIN'
        )


class IsCozinha(permissions.BasePermission):
    """Permite acesso apenas a usuários com perfil COZINHA."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.role == 'COZINHA'
        )


class IsGarcom(permissions.BasePermission):
    """Permite acesso apenas a usuários com perfil GARCOM."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.role == 'GARCOM'
        )


class IsEquipe(permissions.BasePermission):
    """Permite acesso a qualquer membro da equipe (ADMIN, COZINHA ou GARCOM)."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.role in ('ADMIN', 'COZINHA', 'GARCOM')
        )


class IsCozinhaOuAdmin(permissions.BasePermission):
    """Permite acesso a COZINHA ou ADMIN."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.role in ('ADMIN', 'COZINHA')
        )


class IsGarcomOuAdmin(permissions.BasePermission):
    """Permite acesso a GARCOM ou ADMIN."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'perfil')
            and request.user.perfil.role in ('ADMIN', 'GARCOM')
        )
