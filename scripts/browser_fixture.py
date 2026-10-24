import os
import secrets
import json
from pathlib import Path
from urllib.parse import urlsplit
import environ
import psycopg
from psycopg import sql

root = Path(__file__).resolve().parents[1]
environ.Env.read_env(root / '.env')
if urlsplit(os.environ['DATABASE_URL']).hostname not in ('127.0.0.1', 'localhost'):
    raise SystemExit('Use somente um servidor PostgreSQL local de desenvolvimento.')
database = 'mesafacil_browser_' + secrets.token_hex(4)
original = os.environ['DATABASE_URL']
with psycopg.connect(original, dbname='postgres', autocommit=True) as c:
    c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
url = urlsplit(original)._replace(path='/' + database).geturl()
os.environ['DATABASE_URL'] = url
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
os.environ['DEBUG'] = 'True'
import sys
sys.path.insert(0, str(root))
import django
django.setup()
from django.conf import settings
settings.MEDIA_ROOT = root / '.tmp/browser-media'
from django.core.management import call_command
from django.contrib.auth.models import User
from restaurante.models import Mesa, Perfil, Produto
from io import StringIO
call_command('migrate', verbosity=0)
call_command('seed_data', demo_images=True, stdout=StringIO())
password = secrets.token_urlsafe(20)
for role in ('COZINHA', 'GARCOM', 'ADMIN'):
    user = User.objects.create_user('browser_' + role.lower(), password=password)
    Perfil.objects.create(user=user, role=role)
fixture = {'database_url': url, 'database': database, 'password': password,
    'table_uuid': str(Mesa.objects.get(numero=1).token_uuid), 'table_id': Mesa.objects.get(numero=1).pk,
    'product_id': Produto.objects.get(nome='Hambúrguer Clássico').pk}
(root / '.tmp/browser-fixture.json').write_text(json.dumps(fixture), encoding='utf-8')
print('Banco de navegador isolado preparado; credenciais mantidas apenas em .tmp.')
