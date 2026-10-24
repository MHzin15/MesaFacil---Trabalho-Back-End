class PrivateResponses:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(('/api/', '/mesa/', '/cozinha/', '/garcom/', '/admin/', '/entrar/', '/painel/')) and request.path != '/api/cardapio/':
            response['Cache-Control'] = 'no-store'
            response['Referrer-Policy'] = 'same-origin'
        return response
