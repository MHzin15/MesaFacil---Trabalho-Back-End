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


# ============================================================
# Mesa
# ============================================================
@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'token_uuid', 'ativa', 'status_display')
    list_filter = ('ativa',)
    readonly_fields = ('token_uuid', 'qr_code')


# ============================================================
# Sessão da Mesa
# ============================================================
@admin.register(SessaoMesa)
class SessaoMesaAdmin(admin.ModelAdmin):
    list_display = ('mesa', 'ativa', 'conta_solicitada', 'aberta_em', 'fechada_em', 'aberta_por')
    list_filter = ('ativa', 'conta_solicitada')
    search_fields = ('mesa__numero',)
    readonly_fields = ('aberta_em',)


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
