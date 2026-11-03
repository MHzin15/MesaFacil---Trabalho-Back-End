from django import forms


class EscolhasWidget(forms.HiddenInput):
    template_name = 'gestao/widgets/escolhas.html'

    class Media:
        js = ('js/opcoes-editor.js',)


class FotoProdutoWidget(forms.ClearableFileInput):
    template_name = 'gestao/widgets/foto.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['preview_url'] = getattr(self, 'preview_url', '')
        return context
