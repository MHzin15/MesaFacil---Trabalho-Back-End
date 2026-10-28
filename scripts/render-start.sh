#!/usr/bin/env bash
set -euo pipefail

# O plano Free não oferece pre-deploy command nem acesso ao shell.
python manage.py migrate --noinput
python manage.py preparar_render
exec python -m gunicorn core.wsgi:application \
    --bind "0.0.0.0:${PORT:-10000}" \
    --workers 1 \
    --threads 2 \
    --access-logfile - \
    --error-logfile -
