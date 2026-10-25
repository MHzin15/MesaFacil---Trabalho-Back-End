"""Pré-checagem somente de leitura; não substitui o ensaio em dois aparelhos."""
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor
from django.http.request import validate_host

from restaurante.models import Adicional, Mesa, Perfil, Produto


class Command(BaseCommand):
    help = 'Confere banco, dados e acesso para o ensaio, sem alterar arquivos ou cadastros.'

    def add_arguments(self, parser):
        parser.add_argument('--celular', action='store_true', help='Exige endereço HTTPS alcançável e configuração de origem correspondente.')

    def handle(self, *args, **options):
        problemas = []

        def conferir(condicao, descricao):
            if condicao:
                self.stdout.write(self.style.SUCCESS(f'OK: {descricao}'))
            else:
                problemas.append(descricao)
                self.stdout.write(self.style.ERROR(f'PENDENTE: {descricao}'))

        conferir(connection.vendor == 'postgresql', 'Usar PostgreSQL real na aplicação e no ensaio.')
        if problemas:
            raise CommandError('Selecione core.settings com DATABASE_URL de PostgreSQL.')

        try:
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS('OK: Conexão com o banco configurado.'))
            executor = MigrationExecutor(connection)
            pendentes = executor.migration_plan(executor.loader.graph.leaf_nodes())
            conferir(not pendentes, 'Aplicar todas as migrations com python manage.py migrate.')
            if not pendentes:
                conferir(Mesa.objects.filter(ativa=True).exists(), 'Cadastrar ao menos uma mesa ativa.')
                produtos = list(Produto.objects.filter(disponivel=True))
                conferir(bool(produtos), 'Disponibilizar ao menos um produto no cardápio.')
                conferir(Adicional.objects.filter(produto__disponivel=True).exists(), 'Cadastrar adicionais para um produto disponível.')
                conferir(bool(produtos) and all(p.descricao.strip() for p in produtos), 'Preencher a descrição dos produtos disponíveis.')
                conferir(bool(produtos) and all(p.foto and p.foto.storage.exists(p.foto.name) for p in produtos), 'Manter as fotos dos produtos disponíveis acessíveis no armazenamento.')
                perfis = list(Perfil.objects.select_related('user').filter(user__is_active=True))
                for role, nome in Perfil.ROLE_CHOICES:
                    usuarios = [p.user for p in perfis if p.role == role and p.user.has_usable_password()]
                    if role == 'ADMIN':
                        usuarios = [u for u in usuarios if u.is_staff and u.has_perm('restaurante.change_mesa') and u.has_perm('auth.add_user')]
                    conferir(bool(usuarios), f'Ter usuário ativo com senha e acesso de {nome}.')
                if options['celular']:
                    padroes = {'admin': 'admin123', 'cozinha': 'cozinha123', 'garcom': 'garcom123'}
                    inseguro = any(
                        u.check_password(padroes[u.username])
                        for u in get_user_model().objects.filter(is_active=True, username__in=padroes)
                    )
                    conferir(not inseguro, 'Trocar as senhas conhecidas dos usuários de exemplo antes de expor o acesso.')
        except DatabaseError:
            # Não propagar mensagens do driver que possam incluir dados da conexão.
            raise CommandError('Não foi possível consultar o PostgreSQL. Inicie o banco e confira o .env.') from None

        try:
            url = urlsplit(settings.PUBLIC_BASE_URL)
            _ = url.port  # Também valida portas fora do intervalo e valores não numéricos.
            url_valida = bool(url.hostname and url.scheme in ('http', 'https') and not url.username
                              and not url.password and url.path in ('', '/') and not url.query and not url.fragment)
        except ValueError:
            url_valida = False
        conferir(url_valida, 'Configurar PUBLIC_BASE_URL como origem HTTP(S), sem caminho nem credenciais.')
        if url_valida:
            conferir(validate_host(url.hostname, settings.ALLOWED_HOSTS), 'Incluir o host de PUBLIC_BASE_URL em ALLOWED_HOSTS.')
            origem = f'{url.scheme}://{url.netloc}'
            conferir(origem in settings.CSRF_TRUSTED_ORIGINS, 'Incluir a origem de PUBLIC_BASE_URL em CSRF_TRUSTED_ORIGINS.')
            if options['celular']:
                local = url.hostname in ('localhost', '0.0.0.0', '::1') or url.hostname.startswith('127.') or url.hostname.endswith('.localhost')
                conferir(url.scheme == 'https' and not local, 'Usar HTTPS com endereço acessível pelo celular; localhost aponta para o próprio aparelho.')
        if options['celular']:
            conferir(not settings.DEBUG, 'Desativar DEBUG no ambiente exposto para a demonstração.')
            conferir(settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE, 'Manter cookies de sessão e CSRF seguros no acesso HTTPS.')
        else:
            self.stdout.write('AVISO: Esta checagem local não valida acesso ou instalação pelo celular. Use --celular no ambiente HTTPS.')

        if problemas:
            raise CommandError(f'Pré-checagem encontrou {len(problemas)} pendência(s). Corrija os itens acima e repita.')
        self.stdout.write(self.style.SUCCESS('Pré-checagem aprovada. Faça o fluxo pelas telas conforme docs/DEMONSTRACAO.md; o ensaio físico continua necessário.'))
