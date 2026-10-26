# MesaFácil: como entrar e testar no seu computador

## 1. Ligue o sistema

Abra o PowerShell e execute:

```powershell
cd "C:\Users\luand\OneDrive\Desktop\MesaFacil"
.\.venv\Scripts\python.exe scripts/dev_postgres.py start
.\.venv\Scripts\python.exe manage.py runserver
```

Deixe o terminal aberto enquanto usa o sistema. O pgAdmin não precisa ficar aberto.

## 2. Entre como administrador

Abra **http://localhost:8000/admin/** e preencha:

**Usuário:** `admin`

**Senha:** `admin123`

Esses acessos demonstrativos foram cadastrados no banco local:

| Quem | Usuário | Senha | Onde entrar |
| --- | --- | --- | --- |
| Administrador | `admin` | `admin123` | http://localhost:8000/admin/ |
| Cozinha | `cozinha` | `cozinha123` | http://localhost:8000/cozinha/ |
| Garçom | `garcom` | `garcom123` | http://localhost:8000/garcom/ |
| Cliente | Não precisa | Não precisa | Cardápio da mesa |

O login do pgAdmin é separado: ele conecta ao banco, não ao painel do restaurante.
A relação completa desta máquina, **incluindo a senha do PostgreSQL e o link da
Mesa 1**, está em `.local/ACESSOS_LOCAIS.md`, na pasta do projeto.

## 3. Faça seu primeiro pedido

Para começar de forma simples, **continue logado como admin**. Esse usuário pode
abrir também as telas do garçom e da cozinha, usando abas do mesmo navegador.

| Passo | Abra | Faça isso | Resultado esperado |
| --- | --- | --- | --- |
| 1 | http://localhost:8000/garcom/ | Na Mesa 1, clique **Abrir sessão** | Mesa fica ocupada |
| 2 | http://localhost:8000/admin/restaurante/mesa/ | Na linha da Mesa 1, clique **Abrir cardápio** | Abre o cardápio dessa mesa em outra aba |
| 3 | Aba do cardápio | Clique no **+** de um produto, escolha adicionais e adicione ao carrinho | Item aparece no carrinho |
| 4 | Aba do cardápio | Clique **Revisar pedido** e depois confirme o envio | Pedido aparece como recebido |
| 5 | http://localhost:8000/cozinha/ | Clique **Aceitar e iniciar preparo**, depois **Marcar como pronto** | Pedido fica pronto |
| 6 | http://localhost:8000/garcom/ | Clique **Levar à mesa**, depois **Confirmar entrega** | Pedido fica entregue |

As telas se atualizam a cada quatro segundos. Se um pedido ainda não apareceu,
aguarde alguns segundos. Você pode voltar à aba do cliente para ver cada mudança.

Para conferir o cálculo, use Hambúrguer Clássico com Bacon e Queijo Cheddar:
**R$ 32,90 + R$ 5,00 + R$ 4,00 = R$ 41,90**, com os preços originais do exemplo.

## 4. Feche a conta

1. Na aba do **cliente**, clique **Pedir a conta**.
2. Na aba do **garçom**, encontre a solicitação e clique **Conferir e finalizar**.
3. Escolha **Pix**, **Cartão** ou **Dinheiro no caixa**.
4. Clique **Confirmar pagamento simulado**.
5. Confira: a mesa deve ficar **livre** e o cliente deve ver a sessão encerrada.

Se houver outro pedido ainda em preparo ou entrega, finalize esse pedido antes de
pagar a conta. Para testar conta acumulada, envie dois pedidos antes do fechamento.

## 5. Teste cada funcionário separadamente, quando quiser

Depois do primeiro teste, use os logins `cozinha` e `garcom` da tabela para conferir
os acessos específicos. Use navegadores ou perfis diferentes: trocar o login em
uma aba troca também o usuário das outras abas do mesmo perfil.

O cliente pode abrir o link da mesa numa janela anônima, sem nenhum login.

## Para encerrar

No terminal do Django, pressione **Ctrl+C**. Se também quiser desligar o banco:

```powershell
.\.venv\Scripts\python.exe scripts/dev_postgres.py stop
```

O roteiro detalhado para apresentação está em [ENSAIO_COMPLETO.md](ENSAIO_COMPLETO.md).
