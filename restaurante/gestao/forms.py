"""Formulários da gestão: nomes e instruções voltados à equipe do restaurante."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from restaurante.models import Adicional, Categoria, Mesa, Perfil, Produto, Pedido

PAPEIS = [('GARCOM', 'Garçom — mesas, entregas e contas'),
          ('COZINHA', 'Cozinha — preparo e disponibilidade'),
          ('ADMIN', 'Gestor — equipe, cardápio e administração')]


class EstiloForm:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'
            if field.help_text:
                field.widget.attrs['aria-describedby'] = f'{self[name].id_for_label}_help'


class FuncionarioForm(EstiloForm, forms.ModelForm):
    role = forms.ChoiceField(label='Função no restaurante', choices=PAPEIS,
                             help_text='A função define quais telas essa pessoa pode acessar.')
    senha = forms.CharField(label='Senha inicial', required=False, strip=False,
                            widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    confirmar_senha = forms.CharField(label='Repita a senha inicial', required=False, strip=False,
                                      widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'username', 'email', 'role', 'is_active']
        labels = {'first_name': 'Nome', 'last_name': 'Sobrenome', 'username': 'Usuário para entrar',
                  'email': 'E-mail', 'is_active': 'Acesso liberado'}
        help_texts = {'username': 'Use um nome simples, sem espaços. Exemplo: ana.salao.',
                      'is_active': 'Desmarque para suspender o acesso sem apagar o histórico.'}

    def __init__(self, *args, actor, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        if self.instance.pk:
            self.fields.pop('senha')
            self.fields.pop('confirmar_senha')
            self.initial['role'] = getattr(getattr(self.instance, 'perfil', None), 'role', 'GARCOM')
        else:
            self.fields['senha'].required = self.fields['confirmar_senha'].required = True
            self.fields['senha'].help_text = 'Use pelo menos 8 caracteres e evite nomes, sequências e senhas comuns.'

    def clean(self):
        data = super().clean()
        if not self.instance.pk and data.get('senha'):
            if data.get('senha') != data.get('confirmar_senha'):
                self.add_error('confirmar_senha', 'As senhas precisam ser iguais.')
            candidate = get_user_model()(username=data.get('username', ''), first_name=data.get('first_name', ''),
                                          last_name=data.get('last_name', ''), email=data.get('email', ''))
            try:
                validate_password(data['senha'], candidate)
            except forms.ValidationError as exc:
                self.add_error('senha', exc)
        if self.instance.pk == self.actor.pk and (not data.get('is_active') or data.get('role') != 'ADMIN'):
            raise forms.ValidationError('Você não pode suspender ou retirar seu próprio acesso de gestor.')
        if self.instance.is_superuser and (not data.get('is_active') or data.get('role') != 'ADMIN'):
            raise forms.ValidationError('A conta responsável pelo sistema precisa manter o acesso de gestor.')
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.pk:
            user.set_password(self.cleaned_data['senha'])
        if commit:
            user.save()
            Perfil.objects.update_or_create(user=user, defaults={'role': self.cleaned_data['role']})
        return user


class RedefinirSenhaForm(EstiloForm, SetPasswordForm):
    senha_gestor = forms.CharField(label='Sua senha de gestor', strip=False,
                                  widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
                                  help_text='Confirme sua identidade para redefinir o acesso desta pessoa.')

    def __init__(self, *args, actor, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'Nova senha do funcionário'
        self.fields['new_password2'].label = 'Repita a nova senha'

    def clean_senha_gestor(self):
        password = self.cleaned_data['senha_gestor']
        if not self.actor.check_password(password):
            raise forms.ValidationError('Sua senha de gestor não confere.')
        return password


class MesaForm(EstiloForm, forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'ativa']
        labels = {'numero': 'Número da mesa', 'ativa': 'Mesa disponível para atendimento'}
        help_texts = {'ativa': 'Uma mesa em atendimento só pode ser desativada depois de encerrar a conta.'}


class ProdutoForm(EstiloForm, forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'categoria', 'descricao', 'preco', 'foto', 'disponivel']
        localized_fields = ['preco']
        labels = {'nome': 'Nome no cardápio', 'descricao': 'Descrição para o cliente', 'preco': 'Preço de venda (R$)',
                  'foto': 'Foto do produto', 'disponivel': 'Disponível para novos pedidos'}
        help_texts = {'preco': 'O novo preço vale para os próximos pedidos. Pedidos anteriores mantêm o valor original.',
                      'foto': 'Envie uma imagem de até 5 MB. Fotos horizontais ficam melhores no cardápio.',
                      'disponivel': 'Desmarque quando o produto acabar. Ele continua no histórico.'}
        widgets = {'descricao': forms.Textarea(attrs={'rows': 3}), 'preco': forms.TextInput(attrs={'inputmode': 'decimal'})}

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and getattr(foto, 'size', 0) > 5 * 1024 * 1024:
            raise forms.ValidationError('Escolha uma imagem de até 5 MB.')
        return foto


class PrecoForm(EstiloForm, forms.Form):
    preco = forms.DecimalField(label='Novo preço (R$)', max_digits=10, decimal_places=2, min_value=0,
                              localize=True, widget=forms.TextInput(attrs={'inputmode': 'decimal'}))
    anterior = forms.DecimalField(max_digits=10, decimal_places=2, widget=forms.HiddenInput)


class CategoriaForm(EstiloForm, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'ordem']
        labels = {'nome': 'Nome da categoria', 'ordem': 'Ordem no cardápio'}
        help_texts = {'ordem': 'Números menores aparecem primeiro.'}


class AdicionalForm(EstiloForm, forms.ModelForm):
    class Meta:
        model = Adicional
        fields = ['produto', 'nome', 'preco']
        localized_fields = ['preco']
        widgets = {'preco': forms.TextInput(attrs={'inputmode': 'decimal'})}
        labels = {'produto': 'Produto que recebe este adicional', 'nome': 'Nome do adicional', 'preco': 'Preço adicional (R$)'}


class PeriodoForm(EstiloForm, forms.Form):
    inicio = forms.DateField(label='De', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    fim = forms.DateField(label='Até', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    def clean(self):
        data = super().clean()
        if data.get('inicio') and data.get('fim'):
            if data['inicio'] > data['fim']:
                raise forms.ValidationError('A data inicial precisa ser anterior ou igual à final.')
            if (data['fim'] - data['inicio']).days > 366:
                raise forms.ValidationError('Consulte um período de até um ano por vez.')
        return data


class CancelamentoExcepcionalForm(forms.Form):
    motivo = forms.CharField(label='Justificativa do cancelamento', min_length=10, max_length=500,
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        help_text='Explique o ocorrido. O pedido inteiro sairá da cobrança e a operação ficará no histórico.')


class PedidoFiltroForm(PeriodoForm):
    status = forms.ChoiceField(label='Etapa do pedido', required=False, choices=[('', 'Todas as etapas'), *Pedido.STATUS_CHOICES])
