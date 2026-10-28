"""Ilustrações locais para a demonstração; substitua por fotos no admin."""
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw
from .models import Produto


def criar_imagens():
    for produto in Produto.objects.all():
        # No Render Free, arquivos locais somem após reiniciar. Recrie apenas as
        # ilustrações geradas aqui; nunca substitua uma foto enviada pelo usuário.
        if produto.foto:
            if not produto.foto.name.startswith('produtos/demo-') or produto.foto.storage.exists(produto.foto.name):
                continue
        image = Image.new('RGB', (640, 360), '#f4eadb')
        draw = ImageDraw.Draw(image)
        draw.ellipse((185, 45, 455, 315), fill='#fffaf2', outline='#ae452c', width=8)
        draw.ellipse((250, 110, 390, 250), fill='#ae452c')
        draw.text((22, 325), 'MesaFacil - ilustracao demonstrativa', fill='#492d23')
        output = BytesIO()
        image.save(output, format='PNG')
        produto.foto.save(f'demo-{produto.pk}.png', ContentFile(output.getvalue()), save=True)
