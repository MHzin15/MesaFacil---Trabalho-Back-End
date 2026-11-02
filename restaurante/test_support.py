"""Preparação explícita dos novos contratos nos testes de integração."""
def entrar_cliente(client, mesa):
    # Testes de regras preparam uma comanda existente; a suíte de privacidade
    # testa o ingresso real por convite, sem esta preparação de autorização.
    sessao = mesa.sessao_ativa
    if sessao:
        session = client.session
        session['comandas_privadas'] = {str(mesa.token_uuid): str(sessao.acesso_uuid)}
        session['acessos_comandas'] = {str(mesa.token_uuid): [str(sessao.acesso_uuid)]}
        session.save()
    client.get(f'/mesa/{mesa.token_uuid}/')
    return client.get(f'/api/mesa/{mesa.token_uuid}/')


def conferencia(sessao):
    sessao.refresh_from_db()
    return {'total_esperado': sessao.total_consumo(), 'versao_conta': sessao.versao_conta}
