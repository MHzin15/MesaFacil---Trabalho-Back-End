# Registro de Prompt — Marco 2: Base e Cardápio

## Contexto do Projeto
Desenvolvimento do **MesaFácil**, PWA em Django + PostgreSQL para pedidos por QR Code.

## Objetivo deste Prompt
Implementar a base completa do projeto: modelos de dados, configuração, API do cardápio, mesas com QR Code e dados de exemplo.

## Prompt Utilizado
> "Preciso implementar o Marco 2 do MesaFácil. Clone o repositório existente que já possui uma estrutura básica Django e refatore completamente seguindo as regras do projeto. O foco é:
> 1. Modelos completos: Mesa (com UUID para QR Code), SessaoMesa, Categoria, Produto, Adicional, Pedido (com fluxo RECEBIDO→EM_PREPARACAO→PRONTO→A_CAMINHO→ENTREGUE), ItemPedido (com preço gravado), ItemPedidoAdicional (preço gravado), HistoricoStatusPedido (auditoria RN03), Conta (pagamento simulado), Perfil (roles: ADMIN/COZINHA/GARCOM).
> 2. requirements.txt correto com: Django, DRF, psycopg[binary], django-environ, Pillow, qrcode, drf-spectacular, django-filter, django-cors-headers, whitenoise, gunicorn, pytest-django.
> 3. settings.py configurado com drf-spectacular, django-filter, whitenoise.
> 4. Admin customizado para gerenciamento.
> 5. API REST do cardápio e mesas (RF01-RF07, RF23).
> 6. Geração de QR Code por mesa.
> 7. Management command seed_data para dados de exemplo.
> 8. Documentação Swagger no /api/docs/.
> Stack: Python 3, Django 5.2, PostgreSQL, psycopg v3. Interface em pt-BR, valores em R$."

## Ajustes e Observações
- O repositório original tinha models incompletos (faltavam SessaoMesa, HistoricoStatusPedido, Conta, Perfil, ItemPedidoAdicional, e o status A_CAMINHO).
- Os serializers estavam duplicados (CategoriaSerializer e outros definidos duas vezes).
- O requirements.txt estava em UTF-16 (encoding incorreto) com nome errado (`requeriments.txt`).
- Adicionamos drf-spectacular para documentação automática da API.
- Adicionamos whitenoise para servir estáticos.
- Criamos tabela intermediária ItemPedidoAdicional para gravar preço do adicional no pedido (RNF08).
