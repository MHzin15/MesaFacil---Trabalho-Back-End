"""Área de gestão do restaurante, com permissões e regras do domínio existentes."""
import csv
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.http import QueryDict
from urllib.parse import urlsplit
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework.exceptions import APIException

from restaurante import services
from restaurante.models import Adicional, Categoria, Conta, Mesa, Pedido, Perfil, SessaoMesa
from restaurante.pages import equipe
from restaurante.serializers import ProdutoSerializer
from restaurante.models import Produto
from .forms import (AdicionalForm, CategoriaForm, FuncionarioForm, MesaForm, PedidoFiltroForm,
                    PeriodoForm, PrecoForm, ProdutoForm, RedefinirSenhaForm, CancelamentoExcepcionalForm)


def page(request, template, section, title, description='', **context):
    return render(request, f'gestao/{template}.html', dict(section=section, titulo=title,
                  descricao=description, **context))


def paginate(request, queryset):
    query = request.GET.copy()
    query.pop('page', None)
    return {'pagina': Paginator(queryset, 20).get_page(request.GET.get('page')), 'filtros_url': query.urlencode()}


def busca(request):
    return request.GET.get('q', '').strip()[:120]


def retorno(request, destino, anchor=''):
    """Somente a listagem esperada e filtros conhecidos; nunca aceite URL externa."""
    fallback = reverse(f'gestao:{destino}')
    raw = request.POST.get('retorno') if request.method == 'POST' else request.GET.get('retorno')
    if not raw or len(raw) > 2000:
        return fallback
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return fallback
    if parsed.scheme or parsed.netloc or parsed.path != fallback or raw.startswith('//'):
        return fallback
    allowed = QueryDict(mutable=True)
    original = QueryDict(parsed.query)
    for key in ('q', 'categoria', 'status', 'page', 'vista'):
        if key in original:
            allowed[key] = original[key][:120]
    query = allowed.urlencode()
    return fallback + (f'?{query}' if query else '') + (f'#{anchor}' if anchor else '')


def registrar(actor, obj, message, created=False):
    LogEntry.objects.create(user=actor, content_type=ContentType.objects.get_for_model(obj),
                            object_id=str(obj.pk), object_repr=str(obj)[:200],
                            action_flag=ADDITION if created else CHANGE, change_message=message)


def usuarios_visiveis(actor):
    qs = get_user_model().objects.select_related('perfil').order_by('first_name', 'username')
    return qs if actor.is_superuser else qs.filter(is_superuser=False)


def limites(data):
    tz = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(data['inicio'], time.min), tz),
            timezone.make_aware(datetime.combine(data['fim'], time.max), tz))


def periodo(request, form_class=PeriodoForm):
    today = timezone.localdate()
    data = {'inicio': (today - timedelta(days=6)).isoformat(), 'fim': today.isoformat(), **request.GET.dict()}
    return form_class(data)


@equipe('ADMIN')
def inicio(request):
    today = timezone.localdate()
    start, end = limites({'inicio': today, 'fim': today})
    recebidos = Conta.objects.filter(pago=True, pago_em__range=(start, end)).aggregate(
        total=Sum('valor_total', default=Decimal('0.00')), quantidade=Count('id'))
    pedidos = Pedido.objects.filter(created_at__range=(start, end))
    counts = dict(pedidos.values('status').annotate(n=Count('id')).values_list('status', 'n'))
    return page(request, 'inicio', 'inicio', 'Seu restaurante, em dia.',
                'Acompanhe o atendimento e resolva o que precisa da sua atenção.',
                hoje=today, recebidos=recebidos, pedidos_hoje=pedidos.count(),
                em_preparo=counts.get('RECEBIDO', 0) + counts.get('EM_PREPARACAO', 0),
                cancelados=counts.get('CANCELADO', 0),
                ocupadas=Mesa.objects.filter(sessoes__ativa=True).distinct().count(),
                contas_pendentes=SessaoMesa.objects.filter(ativa=True, conta_solicitada=True).select_related('mesa'),
                indisponiveis=Produto.objects.filter(disponivel=False).count(),
                recentes=Pedido.objects.para_exibicao()[:5],
                atividades=LogEntry.objects.select_related('user').order_by('-action_time')[:5])


@equipe('ADMIN')
def funcionarios(request):
    qs = usuarios_visiveis(request.user)
    q = busca(request)
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q))
    status = request.GET.get('status', '')
    if status in ('ativo', 'suspenso'):
        qs = qs.filter(is_active=status == 'ativo')
    return page(request, 'equipe', 'equipe', 'Equipe e acessos',
                'Cadastre pessoas, defina a função de cada uma e recupere o acesso quando necessário.',
                q=q, status=status, **paginate(request, qs))


@equipe('ADMIN')
def funcionario_editar(request, pk=None):
    obj = get_object_or_404(usuarios_visiveis(request.user), pk=pk) if pk else get_user_model()()
    form = FuncionarioForm(request.POST or None, instance=obj, actor=request.user)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                if pk:
                    obj = get_object_or_404(usuarios_visiveis(request.user).select_for_update(of=('self',)), pk=pk)
                    form = FuncionarioForm(request.POST, instance=obj, actor=request.user)
                if form.is_valid():
                    user = form.save()
                    registrar(request.user, user, 'Dados e função de acesso atualizados.' if pk else 'Funcionário cadastrado.', not pk)
                    messages.success(request, 'Funcionário atualizado.' if pk else 'Funcionário cadastrado. Informe o usuário e a senha inicial à pessoa.')
                    return redirect(retorno(request, 'equipe', f'pessoa-{user.pk}'))
        except IntegrityError:
            form.add_error(None, 'Este usuário já está cadastrado. Escolha outro nome para entrar.')
    return page(request, 'formulario', 'equipe', 'Editar funcionário' if pk else 'Cadastrar funcionário',
                'O acesso é definido pela função no restaurante.', form=form, voltar=retorno(request, 'equipe'),
                dica='Para trocar uma senha esquecida, use “Redefinir senha” na lista da equipe.')


@equipe('ADMIN')
def senha(request, pk):
    user = get_object_or_404(usuarios_visiveis(request.user), pk=pk)
    form = RedefinirSenhaForm(user, request.POST or None, actor=request.user)
    if request.method == 'POST':
        with transaction.atomic():
            user = get_object_or_404(usuarios_visiveis(request.user).select_for_update(of=('self',)), pk=pk)
            form = RedefinirSenhaForm(user, request.POST, actor=request.user)
            if form.is_valid():
                form.save()
                registrar(request.user, user, 'Senha de acesso redefinida pelo gestor.')
                if user.pk == request.user.pk:
                    update_session_auth_hash(request, user)
                messages.success(request, f'Senha de {user.get_full_name() or user.username} redefinida. As sessões anteriores dessa pessoa serão encerradas.')
                return redirect(retorno(request, 'equipe', f'pessoa-{user.pk}'))
    return page(request, 'formulario', 'equipe', f'Redefinir senha de {user.get_full_name() or user.username}',
                f'Usuário: {user.username}. A nova senha substitui a anterior.', form=form,
                voltar=retorno(request, 'equipe'), botao='Redefinir senha',
                dica='Informe a nova senha diretamente à pessoa. O sistema não envia senhas por e-mail nem as registra no histórico.')


@equipe('ADMIN')
def mesas(request):
    qs = Mesa.objects.com_sessao_ativa()
    q = busca(request)
    if q:
        qs = qs.filter(numero=int(q)) if q.isdecimal() and len(q) < 10 else qs.none()
    return page(request, 'mesas', 'mesas', 'Mesas e atendimento',
                'Cadastre mesas, acompanhe a ocupação e baixe os QR Codes para o salão.', q=q, **paginate(request, qs))


CADASTROS = {
    'mesas': (Mesa, MesaForm, 'mesas', 'mesa', 'O QR Code da mesa é mantido ao editar o cadastro.'),
    'produtos': (Produto, ProdutoForm, 'cardapio', 'produto', 'Preços de pedidos já enviados não são alterados.'),
    'categorias': (Categoria, CategoriaForm, 'categorias', 'categoria', 'As categorias organizam a navegação do cliente.'),
    'adicionais': (Adicional, AdicionalForm, 'adicionais', 'adicional', 'Cada adicional pertence a um produto e tem seu próprio preço.'),
}


@equipe('ADMIN')
def cadastro(request, tipo, pk=None):
    if tipo not in CADASTROS:
        from django.http import Http404
        raise Http404
    model, form_class, destino, nome, dica = CADASTROS[tipo]
    obj = get_object_or_404(model, pk=pk) if pk else model()
    form = form_class(request.POST or None, request.FILES or None, instance=obj)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                if pk:
                    obj = get_object_or_404(model.objects.select_for_update(of=('self',)), pk=pk)
                    form = form_class(request.POST, request.FILES, instance=obj)
                old_price = getattr(obj, 'preco', None)
                if form.is_valid():
                    changed = ', '.join(str(form.fields[field].label or field) for field in form.changed_data)
                    saved = form.save()
                    detalhe = f'Cadastro atualizado: {changed}.' if pk else f'{nome.capitalize()} cadastrado.'
                    if pk and old_price is not None and old_price != saved.preco:
                        detalhe += f' Preço: R$ {old_price:.2f} → R$ {saved.preco:.2f}.'
                    registrar(request.user, saved, detalhe, not pk)
                    messages.success(request, f'{nome.capitalize()} salvo com sucesso.')
                    return redirect(retorno(request, destino, f'produto-{saved.pk}' if tipo == 'produtos' else ''))
        except IntegrityError:
            form.add_error(None, 'Já existe um cadastro com esses dados. Confira e tente novamente.')
    return page(request, 'formulario', 'mesas' if tipo == 'mesas' else 'cardapio',
                f'Editar {nome}' if pk else f'Cadastrar {nome}', dica, form=form,
                voltar=retorno(request, destino), dica=dica)


@equipe('ADMIN')
def cardapio(request):
    qs = Produto.objects.select_related('categoria').prefetch_related('adicionais')
    q = busca(request)
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))
    category = request.GET.get('categoria', '')
    if category.isdecimal() and len(category) < 10:
        qs = qs.filter(categoria_id=int(category))
    status = request.GET.get('status', '')
    if status in ('disponivel', 'pausado'):
        qs = qs.filter(disponivel=status == 'disponivel')
    pagination = paginate(request, qs)
    for product in pagination['pagina']:
        product.foto_gestao = ProdutoSerializer(product).data['foto']
    return page(request, 'cardapio', 'cardapio', 'Cardápio e preços',
                'Mantenha os produtos organizados, ajuste os preços e pause o que acabou.',
                q=q, categoria=category, status=status, categorias=Categoria.objects.all(), **pagination)


@equipe('ADMIN')
def preco(request, pk):
    obj = get_object_or_404(Produto, pk=pk)
    form = PrecoForm(request.POST or None, initial={'preco': obj.preco, 'anterior': obj.preco})
    if request.method == 'POST':
        with transaction.atomic():
            obj = get_object_or_404(Produto.objects.select_for_update(), pk=pk)
            if form.is_valid():
                if form.cleaned_data['anterior'] != obj.preco:
                    form.add_error(None, 'Outra pessoa alterou este preço. Volte ao cardápio e confira o valor atual antes de salvar.')
                else:
                    anterior = obj.preco
                    obj.preco = form.cleaned_data['preco']
                    obj.save(update_fields=['preco'])
                    registrar(request.user, obj, f'Preço alterado de R$ {anterior:.2f} para R$ {obj.preco:.2f}.')
                    messages.success(request, f'Preço de {obj.nome} atualizado.')
                    return redirect(retorno(request, 'cardapio', f'produto-{obj.pk}'))
    return page(request, 'formulario', 'cardapio', f'Alterar preço: {obj.nome}',
                f'Preço atual: R$ {obj.preco:.2f}. O novo valor vale para os próximos pedidos.',
                form=form, voltar=retorno(request, 'cardapio'), botao='Confirmar novo preço')


@equipe('ADMIN')
@require_POST
def disponibilidade(request, pk):
    with transaction.atomic():
        obj = get_object_or_404(Produto.objects.select_for_update(), pk=pk)
        value = request.POST.get('disponivel')
        if value not in ('0', '1'):
            messages.error(request, 'Escolha uma situação válida para o produto.')
        else:
            obj.disponivel = value == '1'
            obj.save(update_fields=['disponivel'])
            registrar(request.user, obj, 'Produto liberado para venda.' if obj.disponivel else 'Produto pausado no cardápio.')
            messages.success(request, f'{obj.nome}: {"disponível" if obj.disponivel else "pausado"}.')
    return redirect(retorno(request, 'cardapio', f'produto-{obj.pk}'))


@equipe('ADMIN')
def categorias(request):
    return page(request, 'categorias', 'cardapio', 'Categorias do cardápio',
                'Organize os produtos na ordem em que devem aparecer para o cliente.',
                **paginate(request, Categoria.objects.annotate(n_produtos=Count('produtos')).order_by('ordem', 'nome', 'pk')))


@equipe('ADMIN')
def adicionais(request):
    qs = Adicional.objects.select_related('produto').order_by('produto__nome', 'nome')
    q = busca(request)
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(produto__nome__icontains=q))
    return page(request, 'adicionais', 'cardapio', 'Adicionais dos produtos',
                'Personalizações que o cliente pode acrescentar ao pedido.', q=q, **paginate(request, qs))


@equipe('ADMIN')
@require_POST
def abrir_mesa(request, pk):
    try:
        services.abrir(pk, request.user)
        messages.success(request, 'Atendimento aberto. O cliente já pode fazer pedidos pelo QR Code.')
    except APIException as exc:
        messages.error(request, str(exc.detail))
    return redirect('gestao:mesas')


@equipe('ADMIN')
def pedidos(request):
    form = periodo(request, PedidoFiltroForm)
    qs = Pedido.objects.para_exibicao()
    if form.is_valid():
        qs = qs.filter(created_at__range=limites(form.cleaned_data))
        if form.cleaned_data['status']:
            qs = qs.filter(status=form.cleaned_data['status'])
    else:
        qs = qs.none()
    return page(request, 'pedidos', 'pedidos', 'Pedidos do restaurante',
                'Consulte o andamento e o histórico de cada pedido.', form=form, **paginate(request, qs))


@equipe('ADMIN')
def pedido(request, pk):
    obj = get_object_or_404(Pedido.objects.para_exibicao(), pk=pk)
    historico = list(obj.historico_status.select_related('alterado_por'))
    for evento in historico:
        evento.rotulo = dict(Pedido.STATUS_CHOICES).get(evento.status_novo, evento.status_novo)
        if evento.alterado_por:
            evento.autor_nome = evento.alterado_por.get_full_name() or evento.alterado_por.username
        else:
            evento.autor_nome = 'Cliente'
    return page(request, 'pedido', 'pedidos', f'Pedido #{obj.pk}',
                f'Mesa {obj.sessao.mesa.numero} · {obj.get_status_display()}', pedido=obj,
                historico=historico)


@equipe('ADMIN')
def cancelar(request, pk):
    obj = get_object_or_404(Pedido.objects.select_related('sessao__mesa'), pk=pk)
    if request.method == 'POST':
        try:
            services.transitar(pk, 'CANCELADO', request.user)
            messages.success(request, 'Pedido cancelado e retirado da cobrança.')
        except APIException as exc:
            messages.error(request, str(exc.detail))
        return redirect('gestao:pedido', pk=pk)
    return page(request, 'confirmar', 'pedidos', f'Cancelar pedido #{pk}?',
                'O cancelamento só é permitido antes de iniciar o preparo e fica registrado no histórico.',
                voltar=reverse('gestao:pedido', args=[pk]), botao='Confirmar cancelamento')


@equipe('ADMIN')
def cancelar_excepcional(request, pk):
    obj = get_object_or_404(Pedido.objects.select_related('sessao__mesa'), pk=pk)
    form = CancelamentoExcepcionalForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            services.cancelar_excepcional(pk, form.cleaned_data['motivo'], request.user)
            messages.success(request, 'Pedido cancelado com justificativa e retirado da cobrança.')
            return redirect('gestao:pedido', pk=pk)
        except APIException as exc:
            form.add_error(None, str(exc.detail))
    return page(request, 'cancelar_excepcional', 'pedidos', f'Resolver exceção · Pedido #{pk}',
                'Cancelamento do pedido inteiro. Conta paga exige um fluxo próprio de devolução.',
                form=form, pedido=obj)


@equipe('ADMIN')
def relatorios(request):
    form = periodo(request)
    qs = Conta.objects.filter(pago=True).select_related('sessao__mesa')
    if form.is_valid():
        qs = qs.filter(pago_em__range=limites(form.cleaned_data))
    else:
        qs = qs.none()
    resumo = qs.aggregate(total=Sum('valor_total', default=Decimal('0.00')), quantidade=Count('id'))
    resumo['ticket'] = resumo['total'] / resumo['quantidade'] if resumo['quantidade'] else Decimal('0.00')
    if request.GET.get('exportar') == 'csv' and form.is_valid():
        if qs.count() > 10000:
            messages.error(request, 'Reduza o período para exportar até 10 mil contas por arquivo.')
        else:
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="recebimentos-mesafacil.csv"'
            response.write('\ufeff')
            writer = csv.writer(response, delimiter=';')
            writer.writerow(['Conta', 'Mesa', 'Data', 'Forma de pagamento', 'Valor (R$)'])
            for conta in qs.order_by('-pago_em', '-id').iterator(chunk_size=500):
                writer.writerow([conta.pk, conta.sessao.mesa.numero, timezone.localtime(conta.pago_em).strftime('%d/%m/%Y %H:%M'),
                                 conta.get_meio_pagamento_display(), f'{conta.valor_total:.2f}'.replace('.', ',')])
            return response
    meios = list(qs.order_by().values('meio_pagamento').annotate(total=Sum('valor_total'), quantidade=Count('id')))
    for meio in meios:
        meio['nome'] = dict(Conta.MEIO_PAGAMENTO_CHOICES).get(meio['meio_pagamento'], 'Não informado')
    return page(request, 'relatorios', 'relatorios', 'Recebimentos e relatórios',
                'Confira as contas fechadas e os valores registrados por período.',
                form=form, resumo=resumo, meios=meios, **paginate(request, qs.order_by('-pago_em', '-id')))


@equipe('ADMIN')
def atividades(request):
    return page(request, 'atividades', 'atividades', 'Histórico de alterações',
                'Veja quem alterou cadastros e acessos, e quando a mudança aconteceu.',
                **paginate(request, LogEntry.objects.select_related('user').order_by('-action_time', '-id')))
