"""Backup verificado; restauração permitida somente em destino vazio."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.utils import timezone


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fingerprint(db):
    result = {}
    with db.cursor() as cursor:
        for model in apps.get_app_config('restaurante').get_models():
            table = model._meta.db_table
            cursor.execute(f'SELECT * FROM {db.ops.quote_name(table)} ORDER BY {db.ops.quote_name(model._meta.pk.column)}')
            sha, count = hashlib.sha256(), 0
            while rows := cursor.fetchmany(500):
                for row in rows:
                    sha.update(json.dumps(row, default=str, ensure_ascii=False).encode('utf-8') + b'\n')
                    count += 1
            result[table] = {'rows': count, 'sha256': sha.hexdigest()}
    return result


class Command(BaseCommand):
    help = 'Cria snapshot consistente ou restaura em PostgreSQL e mídia vazios. Veja docs/RECUPERACAO.md.'

    def add_arguments(self, parser):
        parser.add_argument('acao', choices=['criar', 'restaurar'])
        parser.add_argument('diretorio', type=Path)
        parser.add_argument('--database', default='default')
        parser.add_argument('--confirmar-banco', help='Nome exato do banco vazio de destino da restauração.')
        parser.add_argument('--pg-bin', type=Path, help='Pasta com pg_dump e pg_restore da versão do PostgreSQL.')

    def pg(self, executable, db, options, args):
        folder = Path(options['pg_bin']) if options.get('pg_bin') else None
        name = executable + ('.exe' if os.name == 'nt' else '')
        binary = str(folder / name) if folder else shutil.which(name)
        if not binary or (folder and not Path(binary).is_file()):
            raise CommandError(f'Instale {executable} e informe --pg-bin com os binários PostgreSQL.')
        cfg = db.settings_dict
        env = os.environ.copy()
        # Senha somente no ambiente do subprocesso; nunca em argumento/log/manifesto.
        env['PGPASSWORD'] = str(cfg.get('PASSWORD') or '')
        env['PGCONNECT_TIMEOUT'] = '5'
        for option, value in cfg.get('OPTIONS', {}).items():
            if option in ('sslmode', 'sslrootcert', 'sslcert', 'sslkey'):
                env['PG' + option.upper()] = str(value)
        command = [binary, '--host', str(cfg.get('HOST') or 'localhost'),
                   '--port', str(cfg.get('PORT') or 5432), '--username', cfg['USER'],
                   '--no-password', *args]
        run = subprocess.run(command, env=env, capture_output=True, check=False)
        if run.returncode:
            raise CommandError(f'{executable} falhou. Confira versão, rede e permissões; nenhum segredo foi exibido.')

    def handle(self, *args, **options):
        db = connections[options['database']]
        if db.vendor != 'postgresql':
            raise CommandError('Snapshot exige PostgreSQL.')
        folder = options['diretorio'].resolve()
        media = Path(settings.MEDIA_ROOT).resolve()
        if options['acao'] == 'criar':
            if folder.is_relative_to(media):
                raise CommandError('Escolha um destino fora de MEDIA_ROOT para não arquivar o próprio backup.')
            if folder.exists():
                raise CommandError('Escolha um diretório novo; backups existentes nunca são sobrescritos.')
            folder.mkdir(parents=True, mode=0o700)
            with transaction.atomic(using=db.alias):
                with db.cursor() as cursor:
                    cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                    cursor.execute('SELECT pg_export_snapshot()')
                    snapshot = cursor.fetchone()[0]
                expected = fingerprint(db)
                self.pg('pg_dump', db, options, ['--format=custom', '--no-owner', '--no-privileges',
                    '--snapshot', snapshot, '--file', str(folder / 'database.dump'), '--dbname', db.settings_dict['NAME']])
                media_hashes = {}
                with tarfile.open(folder / 'media.tar.gz', 'w:gz') as archive:
                    if media.exists():
                        for path in sorted(media.rglob('*')):
                            if path.is_symlink():
                                raise CommandError('Mídia com link simbólico não é suportada no backup.')
                            if path.is_file():
                                name = path.relative_to(media).as_posix()
                                media_hashes[name] = digest(path)
                                archive.add(path, arcname=name, recursive=False)
                with tarfile.open(folder / 'media.tar.gz') as archive:
                    for member in archive.getmembers():
                        with archive.extractfile(member) as stream:
                            if hashlib.file_digest(stream, 'sha256').hexdigest() != media_hashes[member.name]:
                                raise CommandError('Uma foto mudou durante a cópia. Gere outro snapshot em diretório novo.')
                # Um arquivo referenciado ausente invalida o backup em vez de ocultar a perda.
                with db.cursor() as cursor:
                    cursor.execute("SELECT foto FROM restaurante_produto WHERE foto IS NOT NULL AND foto <> ''")
                    if any(row[0] not in media_hashes for row in cursor.fetchall()):
                        raise CommandError('Há fotos cadastradas ausentes no armazenamento. Recupere-as antes do backup.')
            manifest = {'version': 1, 'created_at': timezone.now().isoformat(), 'tables': expected,
                        'media': media_hashes, 'files': {name: digest(folder / name)
                        for name in ('database.dump', 'media.tar.gz')}}
            (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            self.stdout.write(self.style.SUCCESS('Snapshot consistente criado e verificado. Copie-o para armazenamento protegido fora da instância.'))
            return

        if options.get('confirmar_banco') != db.settings_dict['NAME']:
            raise CommandError('Informe --confirmar-banco com o nome exato do destino vazio.')
        if db.introspection.table_names():
            raise CommandError('Restauração recusada: o banco de destino contém tabelas. Use outro banco vazio.')
        if media.exists() and any(media.iterdir()):
            raise CommandError('Restauração recusada: MEDIA_ROOT não está vazio. Use diretório novo.')
        try:
            manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
            if manifest['version'] != 1 or set(manifest['files']) != {'database.dump', 'media.tar.gz'}:
                raise ValueError
            if any(digest(folder / name) != expected for name, expected in manifest['files'].items()):
                raise ValueError
            with tarfile.open(folder / 'media.tar.gz') as archive:
                members = archive.getmembers()
                for member in members:
                    target = (media / member.name).resolve()
                    if not member.isfile() or not target.is_relative_to(media):
                        raise ValueError
                if len({m.name for m in members}) != len(members) or {m.name for m in members} != set(manifest['media']):
                    raise ValueError
                # Validar antes de executar SQL ou criar arquivos no destino.
                for member in members:
                    with archive.extractfile(member) as stream:
                        if hashlib.file_digest(stream, 'sha256').hexdigest() != manifest['media'][member.name]:
                            raise ValueError
        except (OSError, KeyError, ValueError, tarfile.TarError) as exc:
            raise CommandError('Snapshot ausente, inválido ou corrompido; destino preservado.') from exc
        self.pg('pg_restore', db, options, ['--no-owner', '--no-privileges', '--exit-on-error',
            '--single-transaction', '--dbname', db.settings_dict['NAME'], str(folder / 'database.dump')])
        with tarfile.open(folder / 'media.tar.gz') as archive:
            media.mkdir(parents=True, exist_ok=True)
            archive.extractall(media, filter='data')
        if fingerprint(db) != manifest['tables'] or any(digest(media / name) != sha for name, sha in manifest['media'].items()):
            raise CommandError('Restauração não passou na comparação. Preserve o destino para diagnóstico e não o publique.')
        self.stdout.write(self.style.SUCCESS('Restauração verificada: registros, valores e fotos conferem com o snapshot.'))
