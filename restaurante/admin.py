from django.contrib import admin
import qrcode
from io import BytesIO
from django.core.files import File
from django.contrib import admin
from .models import Mesa, Categoria, Produto, Adicional

admin.site.register(Mesa)
admin.site.register(Categoria)
admin.site.register(Produto)
admin.site.register(Adicional)

# No admin ou save da Mesa, podes gerar o QR Code apontando para o URL do frontend/backend:
# url = f"https://seusite.com/mesa/{self.token_uuid}/"
