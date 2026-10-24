import json
import os
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
fixture = json.loads((root / '.tmp/browser-fixture.json').read_text())
os.environ.update(DATABASE_URL=fixture['database_url'], DJANGO_SETTINGS_MODULE='core.settings',
    DEBUG='True', PUBLIC_BASE_URL='http://127.0.0.1:8765')
sys.path.insert(0, str(root))
import django
django.setup()
from django.conf import settings
settings.MEDIA_ROOT = root / '.tmp/browser-media'
from django.core.management import call_command
call_command('runserver', '127.0.0.1:8765', use_reloader=False)
