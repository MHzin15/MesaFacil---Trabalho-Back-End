from django.contrib import admin
import qrcode
from io import BytesIO
from django.core.files import File
from django.contrib import admin
from .models import Mesa, Categoria, Produto, Adicional, ItemPedido, Pedido

admin.site.register(Mesa)
admin.site.register(Categoria)
admin.site.register(Produto)
admin.site.register(Adicional)

# No admin ou save da Mesa, podes gerar o QR Code apontando para o URL do frontend/backend:
# url = f"https://seusite.com/mesa/{self.token_uuid}/"

class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 1  # Linhas em branco extra para adicionar itens rapidamente
    filter_horizontal = ('adicionais',) # Facilita a seleção de adicionais


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'mesa', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'mesa')
    search_fields = ('id', 'mesa__numero', 'observacao')
    inlines = [ItemPedidoInline]