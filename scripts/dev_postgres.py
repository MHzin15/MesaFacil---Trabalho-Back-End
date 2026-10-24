"""Cluster de desenvolvimento exclusivo deste projeto, sem modificar serviços Windows."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import unquote, urlsplit

import environ
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['start', 'stop'])
parser.add_argument('--bin', default=os.environ.get('PG_BIN', r'C:\Program Files\PostgreSQL\18\bin'))
args = parser.parse_args()
environ.Env.read_env(ROOT / '.env')
url = urlsplit(os.environ['DATABASE_URL'])
if url.hostname not in ('localhost', '127.0.0.1'):
    parser.error('Este utilitário só inicia PostgreSQL em localhost.')
data = ROOT / '.local/postgres'
binary = Path(args.bin)
ctl = str(binary / 'pg_ctl.exe') if (binary / 'pg_ctl.exe').exists() else shutil.which('pg_ctl')
initdb = str(binary / 'initdb.exe') if (binary / 'initdb.exe').exists() else shutil.which('initdb')
if not ctl or not initdb:
    parser.error('Instale PostgreSQL e informe --bin com a pasta de binários.')
if args.action == 'stop':
    subprocess.run([ctl, '-D', str(data), '-m', 'fast', '-w', 'stop'], check=True)
else:
    data.parent.mkdir(exist_ok=True)
    if not (data / 'PG_VERSION').exists():
        password_file = data.parent / 'pg-password'
        password_file.write_text(unquote(url.password or ''), encoding='utf-8')
        try:
            subprocess.run([initdb, '-D', str(data), '-U', unquote(url.username), '-A', 'scram-sha-256',
                            '--pwfile=' + str(password_file), '-E', 'UTF8', '--locale=C'], check=True)
        finally:
            password_file.unlink(missing_ok=True)
    running = subprocess.run([ctl, '-D', str(data), 'status'], capture_output=True).returncode == 0
    if not running:
        subprocess.run([ctl, '-D', str(data), '-l', str(data.parent / 'postgres.log'),
                        '-o', f'-p {url.port or 5432} -h 127.0.0.1', '-w', 'start'], check=True)
    database = unquote(url.path.lstrip('/'))
    with psycopg.connect(os.environ['DATABASE_URL'], dbname='postgres', autocommit=True) as connection:
        if not connection.execute('SELECT 1 FROM pg_database WHERE datname = %s', (database,)).fetchone():
            connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    print('PostgreSQL do projeto pronto; nenhuma senha foi exibida.')
