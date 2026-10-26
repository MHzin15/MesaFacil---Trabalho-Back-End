# Ensaio completo e critérios de apresentação

Para começar no computador, use primeiro o [guia local simplificado](DEMONSTRACAO.md).
Este documento guarda a conferência mais detalhada para a apresentação do semestre.

Continuação da etapa 6 do [plano](AVALIACAO_E_PLANO_2026-10-23.md).
O pgAdmin consulta o banco. O navegador abre o sistema. O terminal inicia os dois.

## 1. Ligar o projeto no Windows

Abra o PowerShell na pasta em que clonou o repositório. Nesta máquina:

```powershell
cd "C:\Users\luand\OneDrive\Desktop\MesaFacil"
.\.venv\Scripts\python.exe scripts/dev_postgres.py start
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py verificar_demonstracao
```

A checagem só lê dados. Ela informa se faltam mesas, cardápio, fotos, equipe,
migrations ou configurações. Não cria usuários nem redefine senhas. Em instalação
nova, siga os comandos de seed e criação de usuário do README; se faltar um perfil
existente, confira o cadastro e execute `manage.py sync_roles`.

Depois, mantenha este comando rodando no terminal:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Abra http://localhost:8000 no navegador. Para parar o Django, pressione Ctrl+C.
O banco pode continuar ligado; para desligá-lo quando terminar o trabalho:

```powershell
.\.venv\Scripts\python.exe scripts/dev_postgres.py stop
```

## 2. Conferir o banco pelo pgAdmin

Nesta máquina, o cluster exclusivo já existe em `.local/postgres` e o `.env`
aponta para `127.0.0.1:55432`, usuário e banco `mesafacil`. A senha é somente local.
Em outra instalação, use os valores do seu próprio `.env`.

No formulário de conexão, limpe **Existing Server** se estiver selecionado outro
servidor. Preencha:

| Campo | Valor nesta máquina |
| --- | --- |
| Server Name | MesaFacil |
| Host name/address | 127.0.0.1 |
| Port | 55432 |
| Database / Maintenance database | mesafacil |
| User / Username | mesafacil |
| Password | Senha da DATABASE_URL no .env, entre `mesafacil:` e `@` |

Deixe Role e Service vazios. Conecte e procure **Schemas → public → Tables** no
Object Explorer, quando usar a conexão registrada. O Django cria as tabelas pelo
`migrate`; não é necessário criar cada tabela à mão. No Query Tool, pode conferir:

```sql
SELECT current_database(), current_user;
SELECT numero, ativa FROM restaurante_mesa ORDER BY numero;
SELECT id, status, sessao_id FROM restaurante_pedido ORDER BY id DESC LIMIT 10;
```

Use o sistema para abrir sessões, mudar pedidos e pagar. Essas operações passam
pelas regras e pelo histórico; editar diretamente as linhas pelo pgAdmin contorna
essas proteções. A conexão do pgAdmin será encerrada quando você desligar o banco.

## 3. Ensaiar pelas telas no computador

Use navegadores ou perfis separados para cozinha, garçom e administração. Abas do
mesmo perfil compartilham login; entrar como garçom numa aba também altera a sessão
das outras. O cliente pode usar uma janela anônima para o fluxo de pedidos, mas
use um perfil normal separado para verificar a instalação do PWA.

| Papel | Endereço | Ação inicial |
| --- | --- | --- |
| Administrador | /admin/ | Conferir mesas, cardápio, preços, fotos e equipe |
| Garçom | /garcom/ | Abrir sessão de uma mesa livre |
| Cozinha | /cozinha/ | Deixar painel aberto para receber pedidos |
| Cliente | Link do QR da mesa | Entrar sem criar conta |

Entre com as credenciais que cadastrou. Se usou explicitamente `seed_data
--demo-users`, os usuários locais iniciais estão no README. Antes de expor a
aplicação por um endereço público, troque as senhas com `manage.py changepassword
NOME_DO_USUARIO`. O seed não restaura senhas alteradas.

1. No admin, abra uma mesa e clique **Baixar QR Code**. O PNG identifica aquela
   mesa pelo UUID. No ensaio local, o endereço é o PUBLIC_BASE_URL do `.env`.
2. No garçom, clique **Abrir sessão** nessa mesa. No cliente, abra o link do QR.
3. Escolha Hambúrguer Clássico com Bacon e Queijo Cheddar, quantidade 2, e uma
   observação. Com os preços originais do seed, a revisão deve mostrar R$ 83,80.
   Se você alterou o cardápio, confira o total com os preços atuais.
4. Confirme o envio. Deixe a cozinha receber por polling, sem recarregar a página.
   Inicie o preparo e depois marque pronto. No cliente, acompanhe as mudanças.
5. No garçom, clique **Levar à mesa** e **Confirmar entrega**. Confira a sequência
   recebido → em preparação → pronto → a caminho → entregue.
6. Envie um segundo pedido na mesma mesa. Mostre que a conta acumula os dois.
   Solicite a conta antes da entrega deste segundo pedido: o fechamento deve
   permanecer bloqueado por pendências. Termine preparo e entrega normalmente.
7. No cliente, clique **Pedir a conta**. No garçom, confira pedidos e total,
   escolha Pix, cartão ou dinheiro e clique **Confirmar pagamento simulado**.
   A mesa deve ficar livre e o cliente deve ver o encerramento.
8. No admin, consulte o pedido e seu histórico de status com horários e autores.
   Consulte também a conta paga e use os filtros por data.

Para demonstrar cancelamento, use outro pedido ainda recebido e cancele na
cozinha. Após iniciar preparo essa ação não deve estar disponível. A prova de
saltos/regressões proibidos e isolamento entre mesas está nos testes automatizados.

## 4. Fazer a demonstração em dois aparelhos

O computador e o celular precisam alcançar a mesma aplicação. `localhost` no
celular aponta para o próprio celular. Um IP local em HTTP serve para testar
conectividade, mas não comprova instalação/offline do PWA. Para o aceite completo,
prepare uma hospedagem ou túnel com HTTPS; a publicação não foi feita nesta etapa.

No ambiente HTTPS, configure o `.env` com o endereço real, por exemplo:

```dotenv
DEBUG=False
PUBLIC_BASE_URL=https://SEU-ENDERECO-HTTPS
ALLOWED_HOSTS=SEU-ENDERECO-HTTPS
CSRF_TRUSTED_ORIGINS=https://SEU-ENDERECO-HTTPS
```

Substitua o exemplo pelo domínio, sem `https://` em ALLOWED_HOSTS. Preserve
SECRET_KEY e DATABASE_URL. Use o servidor apropriado à hospedagem; o Compose
do repositório executa Gunicorn em Linux, mas o HTTPS precisa ser configurado
na hospedagem/proxy. Não exponha `runserver` como servidor de produção.

Depois da configuração, execute `collectstatic --noinput` e:

```powershell
.\.venv\Scripts\python.exe manage.py verificar_demonstracao --celular
```

O comando confere a configuração, sem tentar acessar o domínio nem comprovar
que o certificado, o proxy ou a rede funcionam. Repita o download do QR para ele
usar o endereço novo. No celular, confirme que o QR abre a mesa; na segunda tela,
execute cozinha/garçom. Repita o ciclo da seção anterior, com os dois aparelhos.

Instale o app em um navegador compatível usando o botão ou menu do navegador.
Com o cardápio já carregado, desligue a conexão e tente navegar: deve aparecer a
página offline e o cardápio salvo. Nenhum pedido ou pagamento pode ser enviado.
Reconecte e confira que os dados atuais voltam a aparecer.

## 5. Registrar o que foi demonstrado

Preencha após o ensaio real. Campos em branco não são evidência de aprovação.

| Evidência | Resultado a preencher pela dupla |
| --- | --- |
| Data, integrantes e commit apresentado | |
| Celular/navegador e segunda tela | |
| QR abriu a mesa correta | |
| Dois pedidos e acompanhamento sem recarga | |
| Fluxo completo, conta acumulada e pagamento | |
| Histórico de status e filtros no admin | |
| Instalação, offline e reconexão no celular | |
| Infraestrutura Docker/Gunicorn, se utilizada | |

Não registre senhas, cookies ou QR privados no histórico público. Os testes
técnicos e seus limites continuam em [ACEITE_FINAL.md](ACEITE_FINAL.md).
