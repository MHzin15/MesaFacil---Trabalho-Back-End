from datetime import datetime, timezone as datetime_timezone
import math
import unicodedata

from django.conf import settings
from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.deprecation import MiddlewareMixin

from .models import LoginRateBucket


class LoginRateLimit(MiddlewareMixin):
    """Limite atômico no banco para ambos os logins, após a validação CSRF."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method != 'POST' or request.path not in ('/entrar/', '/admin/login/'):
            return None
        now = timezone.now()
        window = settings.LOGIN_RATE_LIMIT_WINDOW
        bucket = int(now.timestamp()) // window
        expires = datetime.fromtimestamp((bucket + 1) * window, tz=datetime_timezone.utc)
        LoginRateBucket.objects.filter(expires_at__lte=now).delete()
        username = unicodedata.normalize('NFKC', request.POST.get('username', '').strip()).casefold()
        limits = (
            ('ip', request.META.get('REMOTE_ADDR', ''), settings.LOGIN_RATE_LIMIT_IP),
            ('account', username, settings.LOGIN_RATE_LIMIT_ACCOUNT),
        )
        for scope, identity, limit in limits:
            # Não confiar em X-Forwarded-For fornecido pelo cliente.
            key = salted_hmac('login-rate-limit', f'{bucket}:{scope}:{identity}', algorithm='sha256').hexdigest()
            counter, _ = LoginRateBucket.objects.get_or_create(key=key, defaults={'expires_at': expires})
            if not LoginRateBucket.objects.filter(pk=counter.pk, attempts__lt=limit).update(attempts=F('attempts') + 1):
                response = HttpResponse('Muitas tentativas de login. Aguarde alguns minutos e tente novamente.',
                                        status=429, content_type='text/plain; charset=utf-8')
                response['Retry-After'] = str(max(1, math.ceil((expires - now).total_seconds())))
                return response
        return None


class PrivateResponses:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(('/api/', '/mesa/', '/cozinha/', '/garcom/', '/admin/', '/entrar/', '/painel/')) and request.path != '/api/cardapio/':
            response['Cache-Control'] = 'no-store'
            response['Referrer-Policy'] = 'same-origin'
        return response
