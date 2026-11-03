#!/usr/bin/env bash
set -euo pipefail

# A migração para a frente preserva comandas privadas existentes.
python manage.py migrate --noinput
python manage.py preparar_render
exec python -m gunicorn core.wsgi:application \
    --config core/gunicorn.conf.py \
    --bind "0.0.0.0:${PORT:-10000}" \
    --workers 1 \
    --threads 2 \
    --access-logfile - \
    --error-logfile -
