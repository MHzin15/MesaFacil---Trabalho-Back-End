"""Escolhas de produto sem acréscimo de preço, com identidade estável e histórico."""
from uuid import UUID, uuid4
import hashlib
import json

from django.core.exceptions import ValidationError


def validar_grupos_opcoes(value):
    if not isinstance(value, list) or len(value) > 6:
        raise ValidationError('Use até 6 grupos de escolhas por produto.')
    ids = set()
    for group in value:
        if not isinstance(group, dict) or set(group) != {'id', 'nome', 'obrigatorio', 'opcoes'}:
            raise ValidationError('Confira os grupos de escolhas do produto.')
        _identidade(group['id'], ids)
        _nome(group['nome'])
        if not isinstance(group['obrigatorio'], bool):
            raise ValidationError('Informe se a escolha é obrigatória.')
        options = group['opcoes']
        if not isinstance(options, list) or not 1 <= len(options) <= 12:
            raise ValidationError('Cada grupo precisa ter entre 1 e 12 opções.')
        names = set()
        for option in options:
            if not isinstance(option, dict) or set(option) != {'id', 'nome'}:
                raise ValidationError('Confira as opções de cada grupo.')
            _identidade(option['id'], ids)
            _nome(option['nome'])
            name = option['nome'].strip().casefold()
            if name in names:
                raise ValidationError('Não repita uma opção no mesmo grupo.')
            names.add(name)


def _nome(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 80:
        raise ValidationError('Os nomes das escolhas devem ter entre 1 e 80 caracteres.')


def _identidade(value, ids):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value or value in ids:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ValidationError('Uma escolha tem identificação inválida ou repetida.') from None
    ids.add(value)


def escolhas_exemplo(nome):
    defaults = {
        'Refrigerante Lata': ('Sabor', ['Coca-Cola', 'Guaraná', 'Sprite']),
        'Água Mineral': ('Tipo de água', ['Sem gás', 'Com gás']),
        'Suco Natural': ('Sabor', ['Laranja', 'Abacaxi', 'Maracujá']),
        'Chopp Artesanal': ('Estilo', ['Pilsen', 'IPA']),
    }
    if nome not in defaults:
        return []
    title, options = defaults[nome]
    return [{'id': str(uuid4()), 'nome': title, 'obrigatorio': True,
             'opcoes': [{'id': str(uuid4()), 'nome': name} for name in options]}]


def versao_opcoes(grupos):
    return hashlib.sha256(json.dumps(grupos, sort_keys=True).encode()).hexdigest()


def selecionar_opcoes(produto, escolhas, versao=None):
    """Nunca aceite nomes do cliente: grave uma cópia dos nomes do catálogo bloqueado."""
    from rest_framework.exceptions import ValidationError as APIValidationError
    if (produto.grupos_opcoes or escolhas or versao) and versao != versao_opcoes(produto.grupos_opcoes):
        raise APIValidationError({'erro': 'As escolhas deste produto mudaram. Edite o item e confira as opções atuais.'})
    selected = {}
    for choice in escolhas:
        gid, oid = str(choice['grupo_id']), str(choice['opcao_id'])
        if gid in selected:
            raise APIValidationError({'erro': 'Escolha somente uma opção de cada grupo.'})
        selected[gid] = oid
    snapshot = []
    for group in produto.grupos_opcoes:
        oid = selected.pop(group['id'], None)
        option = next((o for o in group['opcoes'] if o['id'] == oid), None)
        if oid and not option:
            raise APIValidationError({'erro': 'As opções deste produto mudaram. Edite o item e escolha novamente.'})
        if group['obrigatorio'] and not option:
            raise APIValidationError({'erro': f'{produto.nome}: escolha uma opção de {group["nome"]}.'})
        if option:
            snapshot.append({'grupo_id': group['id'], 'grupo': group['nome'],
                             'opcao_id': option['id'], 'opcao': option['nome']})
    if selected:
        raise APIValidationError({'erro': 'Uma escolha não pertence a este produto. Edite o item.'})
    return snapshot
