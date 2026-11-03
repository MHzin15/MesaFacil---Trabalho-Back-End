from django.middleware.csrf import get_token
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ParseError, PermissionDenied, ValidationError
from uuid import UUID
from rest_framework.parsers import JSONParser


def usuario_garcom(user):
    return user.is_authenticated and getattr(getattr(user, 'perfil', None), 'role', None) == 'GARCOM'


def equipe_mesa(user):
    return user.is_authenticated and getattr(getattr(user, 'perfil', None), 'role', None) in ('ADMIN', 'GARCOM')


class SafeJSONParser(JSONParser):
    """Preserva o limite de bytes do DRF e trata excesso de profundidade."""

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return super().parse(stream, media_type, parser_context)
        except RecursionError:
            raise ParseError('JSON com aninhamento excessivo.') from None


class CsrfSessionAuthentication(SessionAuthentication):
    """A mesma proteção CSRF para equipe autenticada e cliente sem login."""
    def authenticate(self, request):
        self.enforce_csrf(request)
        return super().authenticate(request)


def chave_comanda(request, mesa):
    return request.session.get('comandas_privadas', {}).get(str(mesa.token_uuid))


def comanda_cliente(request, mesa, chave=None):
    from .models import SessaoMesa
    chave = chave or chave_comanda(request, mesa)
    return SessaoMesa.objects.filter(mesa=mesa, acesso_uuid=chave).first() if chave else None


def guardar_comanda(request, mesa, chave):
    from .models import SessaoMesa
    token = str(mesa.token_uuid)
    atuais = request.session.get('comandas_privadas', {})
    acessos = request.session.get('acessos_comandas', {})
    anteriores = set(acessos.get(token, []))
    antiga = atuais.get(token)
    if antiga:
        anteriores.add(antiga)
    # Rascunhos também são capacidades privadas: uma aba pode continuar seu envio
    # mesmo que outra aba selecione uma comanda diferente.
    anteriores.add(str(chave))
    atuais[token] = str(chave)
    acessos[token] = sorted(anteriores)
    request.session['comandas_privadas'] = atuais
    request.session['acessos_comandas'] = acessos


def vincular_mesa(request, mesa, *, novo=False):
    """O QR cria somente um rascunho privado, nunca concede contas da mesa."""
    from uuid import uuid4
    chave = chave_comanda(request, mesa)
    if novo or not chave:
        guardar_comanda(request, mesa, uuid4())
    get_token(request)
    return comanda_cliente(request, mesa)


def comandas_acessiveis(request, mesa):
    from .models import SessaoMesa
    chaves = request.session.get('acessos_comandas', {}).get(str(mesa.token_uuid), [])
    chaves = set(chaves) | {chave_comanda(request, mesa)}
    chaves.discard(None)
    return SessaoMesa.objects.filter(mesa=mesa, acesso_uuid__in=chaves, ativa=True).order_by('pk')


def acesso_mesa(request, mesa):
    sessao = comanda_cliente(request, mesa)
    return bool(chave_comanda(request, mesa)) and (not sessao or sessao.ativa)


def destino_comanda(request, mesa, atendimento_id=None):
    chave = atendimento_id or request.query_params.get('atendimento_id') or chave_comanda(request, mesa)
    if not chave:
        raise PermissionDenied('Abra o cardápio da mesa para iniciar sua comanda.')
    try:
        chave = str(UUID(str(chave)))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError({'erro': 'Atualize a página para identificar sua comanda.'}) from None
    acessos = set(request.session.get('acessos_comandas', {}).get(str(mesa.token_uuid), []))
    acessos.add(chave_comanda(request, mesa))
    if chave not in acessos:
        raise PermissionDenied('Esta comanda não pertence a este navegador.')
    return chave


def validar_mesa(request, mesa, sessao_id=None, *, atendimento_id=None):
    chave = destino_comanda(request, mesa, atendimento_id)
    sessao = comanda_cliente(request, mesa, chave)
    if sessao and not sessao.ativa:
        raise PermissionDenied('Esta comanda foi encerrada. Comece uma nova comanda para pedir novamente.')
    if sessao_id is not None and (not sessao or sessao.pk != sessao_id):
        raise PermissionDenied('Este pedido pertence a outra comanda.')
    return sessao


def visao_equipe(request):
    if request.query_params.get('equipe') != '1':
        return False
    if not equipe_mesa(request.user):
        raise PermissionDenied('A consulta de comandas da mesa é restrita à equipe.')
    return True


from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CsrfSessionSchemaExtension(OpenApiAuthenticationExtension):
    target_class = 'restaurante.security.CsrfSessionAuthentication'
    name = 'cookieAuth'

    def get_security_definition(self, auto_schema):
        from django.conf import settings
        return {'type': 'apiKey', 'in': 'cookie', 'name': settings.SESSION_COOKIE_NAME}
