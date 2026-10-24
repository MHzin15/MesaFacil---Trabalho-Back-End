from io import BytesIO
import qrcode
from drf_spectacular.utils import extend_schema, OpenApiTypes
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from .models import Mesa
from .permissions import IsAdmin


@extend_schema(responses={(200, 'image/png'): OpenApiTypes.BINARY, 403: OpenApiTypes.OBJECT})
@api_view(['GET'])
@permission_classes([IsAdmin])
def download(request, mesa_id):
    mesa = get_object_or_404(Mesa, pk=mesa_id)
    url = settings.PUBLIC_BASE_URL + reverse('cliente', args=[mesa.token_uuid])
    output = BytesIO()
    qrcode.make(url).save(output, format='PNG')
    response = HttpResponse(output.getvalue(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="mesa-{mesa.numero}.png"'
    response['Cache-Control'] = 'no-store'
    return response
