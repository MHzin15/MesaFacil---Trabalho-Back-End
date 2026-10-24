"""Validação técnica no PostgreSQL configurado no .env; interrompe na primeira falha."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
commands = [
    ['manage.py', 'check'],
    ['manage.py', 'makemigrations', '--check', '--dry-run'],
    ['manage.py', 'collectstatic', '--noinput'],
    ['manage.py', 'test', '--verbosity=1'],
    ['manage.py', 'spectacular', '--file', 'docs/openapi.yaml', '--validate', '--fail-on-warn'],
    ['-m', 'pip', 'check'],
]
for command in commands:
    print('Validando: python ' + ' '.join(command), flush=True)
    subprocess.run([sys.executable, *command], cwd=root, check=True)
print('Validação técnica concluída em PostgreSQL.', flush=True)
