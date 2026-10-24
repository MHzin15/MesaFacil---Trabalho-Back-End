from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
from rest_framework.exceptions import APIException
from . import services
from django.contrib import admin
from .models import (
    Perfil, Mesa, SessaoMesa, Categoria, Produto, Adicional,
    Pedido, ItemPedido, ItemPedidoAdicional, HistoricoStatusPedido, Conta,
)


# ============================================================
# Perfil
# ============================================================
@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================
# Mesa
# ============================================================
@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'token_uuid', 'ativa', 'status_display')
    list_filter = ('ativa',)
    readonly_fields = ('token_uuid', 'baixar_qr')
    exclude = ('qr_code',)
    actions = ['abrir_mesas']

    @admin.display(description='QR Code')
    def baixar_qr(self, obj):
        if obj.pk:
            return format_html('<a href="{}">Baixar QR Code</a>', reverse('qr-download', args=[obj.pk]))
        return 'Salve a mesa primeiro.'

    @admin.action(description='Abrir sessão das mesas selecionadas')
    def abrir_mesas(self, request, queryset):
        for mesa in queryset:
            try:
                services.abrir(mesa.pk, request.user)
                self.message_user(request, f'Sessão aberta: {mesa}.')
            except APIException as exc:
                self.message_user(request, str(exc.detail), level='ERROR')


# ============================================================
# Sessão da Mesa
# ============================================================
@admin.register(SessaoMesa)
class SessaoMesaAdmin(admin.ModelAdmin):
    list_display = ('mesa', 'ativa', 'conta_solicitada', 'aberta_em', 'fechada_em', 'aberta_por')
    list_filter = ('ativa', 'conta_solicitada')
    search_fields = ('mesa__numero',)
    readonly_fields = ('mesa', 'ativa', 'conta_solicitada', 'aberta_em', 'fechada_em', 'aberta_por')
    actions = ['fechar_sessoes']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description='Encerrar sessões sem cobrança e sem pendências')
    def fechar_sessoes(self, request, queryset):
        for sessao in queryset:
            try:
                services.fechar(sessao.pk, request.user)
                self.message_user(request, f'Sessão {sessao.pk} encerrada.')
            except APIException as exc:
                self.message_user(request, str(exc.detail), level='ERROR')


# ============================================================
# Cardápio
# ============================================================
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ordem')
    ordering = ('ordem', 'nome')


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'preco', 'disponivel')
    list_filter = ('categoria', 'disponivel')
    search_fields = ('nome', 'descricao')


@admin.register(Adicional)
class AdicionalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'produto', 'preco')
    list_filter = ('produto__categoria',)
    search_fields = ('nome',)


# ============================================================
# Pedido
# ============================================================
class ItemPedidoAdicionalInline(admin.TabularInline):
    model = ItemPedidoAdicional
    extra = 0
    readonly_fields = ('adicional', 'preco')


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ('produto', 'quantidade', 'preco_unitario', 'observacao')
    can_delete = False
    show_change_link = True


class HistoricoStatusInline(admin.TabularInline):
    model = HistoricoStatusPedido
    extra = 0
    readonly_fields = ('status_anterior', 'status_novo', 'alterado_em', 'alterado_por')
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'mesa_numero', 'status', 'created_at', 'valor_total')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'sessao__mesa__numero', 'observacao')
    inlines = [ItemPedidoInline, HistoricoStatusInline]
    readonly_fields = ('sessao', 'status', 'observacao', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Mesa')
    def mesa_numero(self, obj):
        return f"Mesa {obj.sessao.mesa.numero}"


# ============================================================
# Conta
# ============================================================
@admin.register(Conta)
class ContaAdmin(admin.ModelAdmin):
    list_display = ('sessao', 'valor_total', 'meio_pagamento', 'pago', 'pago_em')
    list_filter = ('pago', 'meio_pagamento')
    readonly_fields = ('sessao', 'valor_total', 'meio_pagamento', 'pago', 'pago_em', 'criado_em')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PerfilInline(admin.StackedInline):
    model = Perfil
    extra = 1
    max_num = 1
    can_delete = False


admin.site.unregister(get_user_model())


@admin.register(get_user_model())
class EquipeUserAdmin(UserAdmin):
    inlines = [PerfilInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(is_superuser=False)

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_fieldsets(request, obj)
        if obj is None:
            return self.add_fieldsets
        return ((None, {'fields': ('username', 'password', 'first_name', 'last_name', 'email', 'is_active')}),)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)
