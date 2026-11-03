# Voltar ao estado anterior à UI/UX

O estado local que existia antes desta implementação foi salvo no commit **873e9f8**, na branch **codex/checkpoint-uiux-20261102**. Inclui as alterações que ainda não estavam commitadas, a auditoria, o protótipo e o arquivo de demonstração que já estava modificado.

Além do Git, há uma cópia de **229 arquivos com os bytes originais**, conferida por SHA-256:

`.local/uiux-checkpoint-20261102-213732/source.zip`

O manifesto, os diffs originais e a cópia do índice Git estão no mesmo diretório. Ele é ignorado pelo Git: mantenha essa pasta para conservar a restauração byte a byte. Arquivos ignorados como `.env`, mídia e banco não foram incluídos no commit nem são removidos pelo retorno.

## Conferir a cópia sem mudar nada

Na raiz do projeto, em PowerShell:

```powershell
.venv/Scripts/python.exe scripts/restore_uiux_checkpoint.py
```

## Retornar

Com a árvore limpa, executar:

```powershell
.venv/Scripts/python.exe scripts/restore_uiux_checkpoint.py --restore
```

O script verifica o arquivo inteiro, confere o commit de segurança, troca para a branch anterior e restaura os bytes. **Recusa alterações não salvas**, em vez de descartá-las. Não executa reset destrutivo, limpeza de diretórios ou downgrade do banco. A implementação permanece guardada em sua branch.

O retorno completo foi exercitado nesta entrega, incluindo conferência dos 229 hashes e troca de volta à implementação. No Windows, o script também atualiza marcações do índice somente quando os bytes já são idênticos ao commit, mantendo o Git limpo sem alterar conteúdo.

Para voltar às melhorias:

```powershell
git switch codex/ui-ux-20261102
```

Uma cópia do script também fica na pasta local do checkpoint, para continuar disponível após trocar de branch. A simples troca para a branch de segurança já recupera o conteúdo versionado; a cópia ZIP também preserva as diferenças originais de finais de linha.

## Banco e publicação

Nesta entrega, a migração 0010 foi aplicada apenas em bancos exclusivos de teste e navegador. O banco real e o Render foram preservados, portanto o retorno atual não precisa desfazer dados de operação.

**Atualização durante a inicialização local solicitada em 02/11:** o PostgreSQL de desenvolvimento estava desligado e o banco local ainda estava na migração 0006. O serviço foi religado e as migrações 0007–0010 foram aplicadas para permitir o teste da branch. Antes disso foi criado e validado um backup em `.local/antes-iniciar-uiux-20261102-224336/`, contendo `database.dump`, mídia e manifesto com hashes/contagens. As contagens das tabelas anteriores foram conferidas após a atualização e permaneceram iguais. O Render não foi acessado nem atualizado. O script de retorno continua restaurando somente arquivos; para voltar também os dados locais, preserve esse backup e restaure o dump em outro banco vazio, sem apagar o atual.

Se esta versão for publicada e receber pedidos novos, a volta dos arquivos não significa voltar os dados no tempo. As escolhas estruturadas precisam ser preservadas. Não remova a migração/colunas para tentar retornar e não ultrapasse a barreira de proteção da migração 0009. Antes de uma publicação futura, siga o procedimento de backup e recuperação em [RECUPERACAO.md](RECUPERACAO.md).
