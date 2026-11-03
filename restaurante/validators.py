from django.core.exceptions import ValidationError


MAX_FOTO_BYTES = 5 * 1024 * 1024


def validar_tamanho_foto(value):
    # Uma edição sem nova foto não deve rejeitar arquivos legados já gravados.
    if value and not getattr(value, '_committed', False) and value.size > MAX_FOTO_BYTES:
        raise ValidationError('Escolha uma imagem de até 5 MB.', code='foto_muito_grande')
