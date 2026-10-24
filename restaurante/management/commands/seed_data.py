"""
Management command para popular o banco com dados de exemplo.
Cria mesas, categorias, produtos, adicionais e usuários de teste.

Uso: python manage.py seed_data
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from restaurante.models import Mesa, Categoria, Produto, Adicional, Perfil


class Command(BaseCommand):
    help = 'Popula o banco com dados de exemplo do restaurante MesaFácil'

    def add_arguments(self, parser):
        parser.add_argument('--demo-users', action='store_true', help='Cria usuários locais de demonstração; nunca usar em produção.')
        parser.add_argument('--demo-images', action='store_true', help='Cria ilustrações de exemplo para produtos sem foto.')

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('  Populando dados do MesaFácil...'))

        if options['demo_users']:
            self._criar_usuarios()
        self._criar_mesas()
        self._criar_cardapio()

        self.stdout.write(self.style.SUCCESS(' Dados de exemplo criados com sucesso!'))
        self.stdout.write('')
        if options['demo_images']:
            from restaurante.demo_images import criar_imagens
            criar_imagens()
        if options['demo_users']:
            self.stdout.write('Demonstração local: admin/admin123, cozinha/cozinha123, garcom/garcom123')

    def _criar_usuarios(self):
        """Cria usuários de teste com perfis."""
        usuarios = [
            {
                'username': 'admin',
                'password': 'admin123',
                'first_name': 'Administrador',
                'last_name': 'MesaFácil',
                'is_staff': True,
                'is_superuser': True,
                'role': 'ADMIN',
            },
            {
                'username': 'cozinha',
                'password': 'cozinha123',
                'first_name': 'Equipe',
                'last_name': 'Cozinha',
                'is_staff': False,
                'is_superuser': False,
                'role': 'COZINHA',
            },
            {
                'username': 'garcom',
                'password': 'garcom123',
                'first_name': 'João',
                'last_name': 'Garçom',
                'is_staff': False,
                'is_superuser': False,
                'role': 'GARCOM',
            },
        ]

        for u in usuarios:
            role = u.pop('role')
            password = u.pop('password')

            user, created = User.objects.get_or_create(
                username=u['username'],
                defaults=u,
            )

            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'    Usuário "{user.username}" criado')
            else:
                self.stdout.write(f'     Usuário "{user.username}" já existe')

            Perfil.objects.get_or_create(
                user=user,
                defaults={'role': role},
            )

    def _criar_mesas(self):
        """Cria 10 mesas de exemplo."""
        for i in range(1, 11):
            mesa, created = Mesa.objects.get_or_create(
                numero=i,
                defaults={'ativa': True},
            )
            if created:
                self.stdout.write(f'    Mesa {i} criada (UUID: {mesa.token_uuid})')

    def _criar_cardapio(self):
        """Cria categorias, produtos e adicionais de exemplo."""

        # --- Categorias ---
        categorias_data = [
            {'nome': 'Entradas', 'ordem': 1},
            {'nome': 'Hambúrgueres', 'ordem': 2},
            {'nome': 'Pratos Principais', 'ordem': 3},
            {'nome': 'Acompanhamentos', 'ordem': 4},
            {'nome': 'Bebidas', 'ordem': 5},
            {'nome': 'Sobremesas', 'ordem': 6},
        ]

        categorias = {}
        for cat_data in categorias_data:
            cat, _ = Categoria.objects.get_or_create(
                nome=cat_data['nome'],
                defaults={'ordem': cat_data['ordem']},
            )
            categorias[cat.nome] = cat

        # --- Produtos e Adicionais ---
        produtos_data = [
            # Entradas
            {
                'categoria': 'Entradas',
                'nome': 'Bruschetta de Tomate',
                'descricao': 'Fatias de pão italiano com tomate fresco, manjericão e azeite.',
                'preco': Decimal('18.90'),
                'adicionais': [],
            },
            {
                'categoria': 'Entradas',
                'nome': 'Bolinho de Bacalhau (6 un.)',
                'descricao': 'Bolinhos crocantes de bacalhau com azeitonas.',
                'preco': Decimal('24.90'),
                'adicionais': [],
            },
            # Hambúrgueres (referência RN07)
            {
                'categoria': 'Hambúrgueres',
                'nome': 'Hambúrguer Clássico',
                'descricao': 'Pão brioche, blend de 180g, alface, tomate e maionese da casa.',
                'preco': Decimal('32.90'),
                'adicionais': [
                    {'nome': 'Bacon', 'preco': Decimal('5.00')},
                    {'nome': 'Queijo Cheddar', 'preco': Decimal('4.00')},
                    {'nome': 'Ovo', 'preco': Decimal('3.00')},
                    {'nome': 'Cebola Caramelizada', 'preco': Decimal('3.50')},
                ],
            },
            {
                'categoria': 'Hambúrgueres',
                'nome': 'Hambúrguer Duplo',
                'descricao': 'Dois blends de 180g, queijo, alface, tomate e molho especial.',
                'preco': Decimal('42.90'),
                'adicionais': [
                    {'nome': 'Bacon', 'preco': Decimal('5.00')},
                    {'nome': 'Queijo Cheddar', 'preco': Decimal('4.00')},
                    {'nome': 'Jalapeño', 'preco': Decimal('3.00')},
                ],
            },
            {
                'categoria': 'Hambúrgueres',
                'nome': 'Hambúrguer Vegano',
                'descricao': 'Blend de grão de bico, alface, tomate, cebola roxa e maionese vegana.',
                'preco': Decimal('34.90'),
                'adicionais': [
                    {'nome': 'Cogumelos', 'preco': Decimal('4.50')},
                    {'nome': 'Guacamole', 'preco': Decimal('5.00')},
                ],
            },
            # Pratos Principais
            {
                'categoria': 'Pratos Principais',
                'nome': 'Filé à Parmegiana',
                'descricao': 'Filé empanado com molho de tomate e queijo gratinado. Acompanha arroz e fritas.',
                'preco': Decimal('49.90'),
                'adicionais': [
                    {'nome': 'Porção Extra de Fritas', 'preco': Decimal('8.00')},
                ],
            },
            {
                'categoria': 'Pratos Principais',
                'nome': 'Salmão Grelhado',
                'descricao': 'Salmão grelhado com legumes salteados e purê de batata.',
                'preco': Decimal('62.90'),
                'adicionais': [],
            },
            # Acompanhamentos
            {
                'categoria': 'Acompanhamentos',
                'nome': 'Batata Frita',
                'descricao': 'Porção generosa de batatas fritas crocantes.',
                'preco': Decimal('16.90'),
                'adicionais': [
                    {'nome': 'Cheddar e Bacon', 'preco': Decimal('6.00')},
                ],
            },
            {
                'categoria': 'Acompanhamentos',
                'nome': 'Onion Rings (8 un.)',
                'descricao': 'Anéis de cebola empanados e crocantes.',
                'preco': Decimal('14.90'),
                'adicionais': [],
            },
            # Bebidas
            {
                'categoria': 'Bebidas',
                'nome': 'Refrigerante Lata',
                'descricao': 'Coca-Cola, Guaraná ou Sprite.',
                'preco': Decimal('7.90'),
                'adicionais': [],
            },
            {
                'categoria': 'Bebidas',
                'nome': 'Suco Natural',
                'descricao': 'Laranja, abacaxi ou maracujá (400ml).',
                'preco': Decimal('12.90'),
                'adicionais': [],
            },
            {
                'categoria': 'Bebidas',
                'nome': 'Água Mineral',
                'descricao': 'Garrafa 500ml — com ou sem gás.',
                'preco': Decimal('5.90'),
                'adicionais': [],
            },
            {
                'categoria': 'Bebidas',
                'nome': 'Chopp Artesanal',
                'descricao': 'Chopp artesanal 300ml — Pilsen ou IPA.',
                'preco': Decimal('16.90'),
                'adicionais': [],
            },
            # Sobremesas
            {
                'categoria': 'Sobremesas',
                'nome': 'Petit Gâteau',
                'descricao': 'Bolo de chocolate com centro cremoso, acompanhado de sorvete de baunilha.',
                'preco': Decimal('26.90'),
                'adicionais': [
                    {'nome': 'Calda de Caramelo', 'preco': Decimal('3.00')},
                ],
            },
            {
                'categoria': 'Sobremesas',
                'nome': 'Pudim de Leite',
                'descricao': 'Pudim de leite condensado tradicional.',
                'preco': Decimal('14.90'),
                'adicionais': [],
            },
        ]

        for prod_data in produtos_data:
            categoria = categorias[prod_data['categoria']]
            adicionais = prod_data.pop('adicionais')
            prod_data.pop('categoria')

            produto, created = Produto.objects.get_or_create(
                nome=prod_data['nome'],
                defaults={
                    'categoria': categoria,
                    'descricao': prod_data['descricao'],
                    'preco': prod_data['preco'],
                },
            )

            if created:
                self.stdout.write(f'    Produto: {produto.nome}')

                for add_data in adicionais:
                    Adicional.objects.get_or_create(
                        produto=produto,
                        nome=add_data['nome'],
                        defaults={'preco': add_data['preco']},
                    )
