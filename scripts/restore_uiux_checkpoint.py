"""Retorno local da UI/UX: branch de segurança + restauração dos bytes originais.

Execute na raiz do projeto. Sem --restore, apenas verifica a cópia.
Recusa alterações não salvas; nunca remove arquivos ignorados, mídia ou banco.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


CHECKPOINT = '873e9f8'
BRANCH = 'codex/checkpoint-uiux-20261102'
SNAPSHOT = '.local/uiux-checkpoint-20261102-213732'


def git(*args):
    return subprocess.check_output(['git', *args], text=True, encoding='utf-8').strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true', help='Trocar para a branch de segurança e restaurar os bytes.')
    args = parser.parse_args()
    root = Path(git('rev-parse', '--show-toplevel')).resolve()
    snapshot = root / SNAPSHOT
    manifest = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8'))
    if Path(manifest['root']).resolve() != root:
        raise SystemExit('Esta cópia pertence a outro diretório. Nenhum arquivo alterado.')
    commit = git('rev-parse', CHECKPOINT)
    if git('rev-parse', BRANCH) != commit:
        raise SystemExit('A referência de segurança mudou. Nenhum arquivo alterado.')
    names = set(git('ls-tree', '-r', '--name-only', commit).splitlines())
    if names != set(manifest['files']):
        raise SystemExit('A lista da cópia não corresponde ao checkpoint. Nenhum arquivo alterado.')
    with zipfile.ZipFile(snapshot / 'source.zip') as archive:
        if set(archive.namelist()) != names:
            raise SystemExit('Conteúdo da cópia divergente. Nenhum arquivo alterado.')
        for name, digest in manifest['files'].items():
            path = (root / name).resolve()
            if not path.is_relative_to(root) or '.git' in Path(name).parts:
                raise SystemExit('Caminho inseguro na cópia. Nenhum arquivo alterado.')
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise SystemExit(f'Cópia corrompida: {name}. Nenhum arquivo alterado.')
        print(f'Cópia íntegra: {len(names)} arquivos; checkpoint {commit[:7]}.')
        if not args.restore:
            return
        if git('status', '--porcelain=v1', '--untracked-files=all'):
            raise SystemExit('Há alterações locais. Salve-as em um commit antes de retornar; nada foi alterado.')
        subprocess.run(['git', 'switch', BRANCH], check=True)
        for name in names:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))
        assert all(hashlib.sha256((root / n).read_bytes()).hexdigest() == h for n, h in manifest['files'].items())
    print('Versão anterior restaurada e conferida byte a byte. Banco, .env e arquivos ignorados preservados.')


if __name__ == '__main__':
    main()
