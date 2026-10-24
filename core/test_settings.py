"""Testes rápidos explícitos; nunca use este módulo para servir o restaurante."""
import os

os.environ.setdefault('SECRET_KEY', 'somente-testes-sem-uso-na-aplicacao')
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')
from .settings import *  # noqa: E402,F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
DEBUG = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
