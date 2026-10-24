from django.middleware.csrf import get_token
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied


class CsrfSessionAuthentication(SessionAuthentication):
    """A mesma proteção CSRF para equipe autenticada e cliente sem login."""
    def authenticate(self, request):
        self.enforce_csrf(request)
        return super().authenticate(request)


def vincular_mesa(request, mesa):
    sessao = mesa.sessao_ativa
    contextos = request.session.get('mesas', {})
    contextos[str(mesa.token_uuid)] = sessao.pk if sessao else None
    request.session['mesas'] = contextos
    get_token(request)
    return sessao


def validar_mesa(request, mesa, sessao_id=None):
    actual = mesa.sessao_ativa
    granted = request.session.get('mesas', {})
    token = str(mesa.token_uuid)
    if token not in granted or granted[token] != (actual.pk if actual else None):
        raise PermissionDenied('Acesse novamente o QR Code desta mesa para atualizar a sessão.')
    if sessao_id is not None and (not actual or actual.pk != sessao_id):
        raise PermissionDenied('Este pedido pertence a outra sessão da mesa.')
    return actual


from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CsrfSessionSchemaExtension(OpenApiAuthenticationExtension):
    target_class = 'restaurante.security.CsrfSessionAuthentication'
    name = 'cookieAuth'

    def get_security_definition(self, auto_schema):
        from django.conf import settings
        return {'type': 'apiKey', 'in': 'cookie', 'name': settings.SESSION_COOKIE_NAME}

