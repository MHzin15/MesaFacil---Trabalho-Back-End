# Etapa 6 — Conferência do plano e do requisito pai

Contexto: usuário pediu retomar após a etapa 4 e conferir tudo contra a avaliação
e o enunciado original. A etapa 5 foi implementada e enviada em b3b92e7.
Concluir validação técnica, regressões e documentação; manter requisitos físicos
ou infraestrutura indisponível claramente pendentes, sem inventar evidências.

Escopo: RF01–RF25, RNF01–RNF13, RN01–RN10, stack obrigatória, marcos e histórico
dos prompts. Restaurante único, sem opcionais nem gateway real. Executar PostgreSQL
real e Chrome isolado com cliente móvel, cozinha, garçom e admin em contextos distintos.

## Erros encontrados e correções do direcionamento

- A largura intrínseca do grid excedia o viewport móvel. O prompt de aceitação
  passou a exigir medida real do viewport/scrollWidth e cliques, não só render HTML.
  Corrigidos mínimos do grid; polling não reconstrói cardápio sem alteração.
- Preço podia mudar após revisão. Exigir nova confirmação visual e comparar
  `total_esperado` com cálculo canônico no servidor; diferenças revertem o pedido,
  sem usar o valor do cliente como preço de venda.
- Fotos eram servidas somente com DEBUG. Permitir apenas `/media/produtos/` também
  em configuração de entrega; manter diretório legado de QR sem rota pública.
- Desativar mesa ocupada interrompia seu atendimento. Bloquear no admin/API com
  validação e lock consistente com abertura de sessão.
- Mover o titular de Perfil deixaria permissões derivadas no usuário antigo.
  Tornar titular imutável no admin e proteger perfis de superusuários de gestores comuns.
- Horários explícitos de São Paulo e cancelamento pela cozinha antes do preparo.

Aceite: validação técnica no PostgreSQL, schema estrito, regressões de concorrência,
fluxo visual completo e testes offline. Demonstrar que perda de resposta não duplica
pedidos. Evidências locais em `.tmp/`; relatório versionado em `ACEITE_FINAL.md`.
Não afirmar teste físico de celular, execução Docker ou Gunicorn Linux não realizados.
