"""Sondas públicas sem detalhes de configuração ou exceção."""
from django.db import DatabaseError, connection, transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET


def response(ok):
    result = JsonResponse({'status': 'ok' if ok else 'unavailable'}, status=200 if ok else 503)
    result['Cache-Control'] = 'no-store'
    return result


@require_GET
def live(request):
    return response(True)


@require_GET
def ready(request):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    cursor.execute("SET LOCAL statement_timeout = '2000ms'")
                    cursor.execute("SET LOCAL lock_timeout = '1000ms'")
                cursor.execute('SELECT 1')
                ok = cursor.fetchone() == (1,)
    except DatabaseError:
        ok = False
    return response(ok)
