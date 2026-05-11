# BookTime — Automação de Posts no Instagram

Automação que publica posts (foto única no feed) no Instagram da BookTime via GitHub Actions, usando a Instagram Graph API da Meta.

**Como funciona em uma frase:** você joga uma imagem + caption.txt numa pasta do repositório, clica em "Run workflow" no GitHub, e o post sai no Instagram automaticamente.

---

## Índice

1. [Visão geral](#visão-geral)
2. [O que você precisa antes de começar](#o-que-você-precisa-antes-de-começar)
3. [Passo 1 — Criar o app no Meta for Developers](#passo-1--criar-o-app-no-meta-for-developers)
4. [Passo 2 — Pegar o User Access Token](#passo-2--pegar-o-user-access-token)
5. [Passo 3 — Trocar pelo Long-Lived Token (60 dias)](#passo-3--trocar-pelo-long-lived-token-60-dias)
6. [Passo 4 — Descobrir o Instagram Business Account ID](#passo-4--descobrir-o-instagram-business-account-id)
7. [Passo 5 — Subir o código para um novo repositório no GitHub](#passo-5--subir-o-código-para-um-novo-repositório-no-github)
8. [Passo 6 — Configurar os secrets no GitHub](#passo-6--configurar-os-secrets-no-github)
9. [Passo 7 — Publicar o primeiro post](#passo-7--publicar-o-primeiro-post)
10. [Renovação automática do token (opcional mas recomendado)](#renovação-automática-do-token-opcional-mas-recomendado)
11. [Solução de problemas](#solução-de-problemas)

---

## Visão geral

```
┌─────────────────────────────────────────────────────────────┐
│  Você commita uma pasta em posts/ com imagem + caption.txt  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
       ┌──────────────────────────────────────┐
       │  Você clica "Run workflow" no GitHub │
       └──────────────────┬───────────────────┘
                          │
                          ▼
       ┌─────────────────────────────────────────────────┐
       │  GitHub Actions roda post_to_instagram.py:       │
       │  1. Pega a pasta mais antiga                     │
       │  2. Monta URL pública da imagem (raw.github)     │
       │  3. Chama POST /media (cria container)           │
       │  4. Aguarda container ficar pronto               │
       │  5. Chama POST /media_publish (publica)          │
       │  6. Move a pasta pra posts/published/            │
       └──────────────────┬──────────────────────────────┘
                          │
                          ▼
                ┌──────────────────┐
                │  Post no Insta!  │
                └──────────────────┘
```

---

## O que você precisa antes de começar

- ✅ Conta do Instagram da BookTime configurada como **Business** ou **Creator**
- ✅ Página do Facebook vinculada à conta Instagram (sem isso, a API não funciona)
- ✅ Acesso de administrador na Página do Facebook
- ✅ Conta no GitHub
- ⏰ Aproximadamente **1 hora** pra fazer todo o setup (uma vez só)

> **Não tem a Página do Facebook vinculada?** No app do Instagram, vai em **Configurações → Conta → Compartilhar com outros apps → Facebook** e conecta uma Página. Sem isso, a Graph API não consegue acessar o Instagram.

---

## Passo 1 — Criar o app no Meta for Developers

1. Acesse [developers.facebook.com](https://developers.facebook.com) e faça login com a conta do Facebook que administra a Página da BookTime.

2. No topo, clique em **Meus Apps → Criar App**.

3. Em "Caso de uso", selecione **"Outro"**.

4. Em "Tipo", selecione **"Empresa"**.

5. Preencha:
   - **Nome do app**: `BookTime Instagram Auto` (qualquer nome, é interno)
   - **E-mail de contato**: seu e-mail
   - **Conta da Empresa**: pode deixar "Não estou vinculando..." se não tiver Business Manager

6. Clique em **Criar app** e confirme com sua senha do Facebook.

7. Na página do app, vá em **Adicionar produto** no menu lateral.

8. Encontre **Instagram → Graph API** e clique em **Configurar**.

9. Anote duas coisas que vamos usar depois:
   - **App ID**: aparece no topo da página
   - **App Secret**: vá em **Configurações → Básico → App Secret → Mostrar** (vai pedir senha)

> 📝 Guarde o **App ID** e o **App Secret** num lugar seguro. Vamos colocar nos secrets do GitHub.

---

## Passo 2 — Pegar o User Access Token

1. Ainda no painel do app, vá em **Ferramentas → Graph API Explorer** (ou acesse direto: [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer)).

2. No topo direito, selecione seu app no dropdown "Meta App".

3. Em "User or Page", deixe **"User Access Token"**.

4. Em "Permissions", clique em **Add a Permission** e adicione todas estas:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
   - `business_management`

5. Clique no botão **Generate Access Token** (azul, no canto superior direito).

6. Vai abrir um pop-up do Facebook. Autorize o acesso à Página da BookTime quando pedir.

7. Copie o token gerado (string longa que aparece no campo "Access Token").

> ⚠️ **Esse token dura apenas 1 hora.** No próximo passo vamos trocar por um de 60 dias.

---

## Passo 3 — Trocar pelo Long-Lived Token (60 dias)

Cole essa URL no navegador, **substituindo** os três campos entre `{}`:

```
https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id={APP_ID}&client_secret={APP_SECRET}&fb_exchange_token={TOKEN_DE_1H}
```

- `{APP_ID}` → o App ID do Passo 1
- `{APP_SECRET}` → o App Secret do Passo 1
- `{TOKEN_DE_1H}` → o token do Passo 2

Você vai receber uma resposta JSON parecida com:

```json
{
  "access_token": "EAABxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "token_type": "bearer",
  "expires_in": 5183944
}
```

> 📝 Guarde esse `access_token`. **Esse é o token de 60 dias** que vamos usar.
> `expires_in` em segundos ≈ 60 dias.

---

## Passo 4 — Descobrir o Instagram Business Account ID

Cole essa URL no navegador, substituindo `{TOKEN_60D}` pelo token do passo anterior:

```
https://graph.facebook.com/v21.0/me/accounts?access_token={TOKEN_60D}
```

Vai listar as Páginas do Facebook que você administra. Anote o `id` da Página da BookTime.

Agora cole essa, substituindo `{PAGE_ID}` e `{TOKEN_60D}`:

```
https://graph.facebook.com/v21.0/{PAGE_ID}?fields=instagram_business_account&access_token={TOKEN_60D}
```

Resposta esperada:

```json
{
  "instagram_business_account": {
    "id": "17841400000000000"
  },
  "id": "PAGE_ID"
}
```

> 📝 Guarde o `id` que aparece dentro de `instagram_business_account`. **Esse é o IG Business Account ID.**

Resumo do que você tem até aqui:
- ✅ APP_ID
- ✅ APP_SECRET
- ✅ Long-Lived Token (60 dias)
- ✅ IG Business Account ID

---

## Passo 5 — Subir o código para um novo repositório no GitHub

1. No GitHub, clique em **+ → New repository** (canto superior direito).

2. Configurações:
   - **Repository name**: `booktime-instagram-auto`
   - **Visibility**: **Private** (recomendado — não tem motivo pra deixar público)
   - **Initialize this repository with**: deixe **todas as opções desmarcadas** (sem README, sem .gitignore, sem licença)

3. Clique em **Create repository**.

4. Agora você precisa subir todos os arquivos. A forma mais fácil sem usar terminal:

   a. Na página vazia do repo, clique em **uploading an existing file** (link que aparece na frase "you can also import code from another repository").

   b. Arraste **todos os arquivos e pastas** que recebeu (mantendo a estrutura):
   ```
   .github/workflows/publish.yml
   .github/workflows/refresh-token.yml
   scripts/post_to_instagram.py
   scripts/refresh_token.py
   posts/README.md
   .gitignore
   README.md
   requirements.txt
   ```

   > ⚠️ O GitHub web preserva a estrutura de pastas quando você arrasta a pasta inteira do seu computador. Se ele não preservar, você pode criar as pastas manualmente usando a opção **Add file → Create new file** e digitando o caminho completo no nome (ex: `.github/workflows/publish.yml`).

   c. Escreva uma mensagem de commit (ex: "Setup inicial") e clique em **Commit changes**.

---

## Passo 6 — Configurar os secrets no GitHub

No repositório recém-criado:

1. Vá em **Settings** (aba do topo do repo) **→ Secrets and variables → Actions**.

2. Clique em **New repository secret** e adicione um por vez:

   | Nome do secret | Valor |
   |---|---|
   | `IG_ACCESS_TOKEN` | O Long-Lived Token (60 dias) do Passo 3 |
   | `IG_BUSINESS_ACCOUNT_ID` | O ID descoberto no Passo 4 |
   | `APP_ID` | O App ID do Passo 1 |
   | `APP_SECRET` | O App Secret do Passo 1 |

3. O quinto secret (`GH_PAT_FOR_SECRETS`) só é necessário pra renovação automática do token, e está explicado [na seção de renovação](#renovação-automática-do-token-opcional-mas-recomendado).

> ⚠️ **Nunca cole esses valores em arquivos do repositório**, comentários, ou em qualquer lugar fora dos Secrets. Se vazar, qualquer pessoa pode postar no Instagram da BookTime.

---

## Passo 7 — Publicar o primeiro post

### Criar a pasta do post

1. No GitHub, vá na pasta `posts/`.

2. Clique em **Add file → Create new file**.

3. No campo de nome do arquivo, digite (exemplo):
   ```
   2026-05-15-teste/.gitkeep
   ```
   Isso cria uma pasta nova chamada `2026-05-15-teste`. O arquivo `.gitkeep` é só pra forçar a criação da pasta (você pode apagar depois).

4. Clique em **Commit changes**.

### Subir a imagem

1. Entre na pasta `posts/2026-05-15-teste/` que você acabou de criar.

2. Clique em **Add file → Upload files**.

3. Arraste a imagem (JPG ou PNG, idealmente quadrada — 1080x1080).

   > 📏 **Requisitos da imagem**:
   > - Formato: JPG ou PNG
   > - Razão de aspecto: entre 4:5 (vertical) e 1.91:1 (paisagem)
   > - Tamanho máximo: 8 MB
   > - Recomendado: 1080x1080px (quadrado)

4. Commit.

### Criar o caption.txt

1. Na mesma pasta, clique em **Add file → Create new file**.

2. Nome: `caption.txt`

3. No corpo, escreva a legenda do post. Pode usar quebras de linha, emojis, hashtags. Exemplo:
   ```
   Chegou na BookTime! 📚

   [descrição do livro]

   Garante o seu pelo link da bio.

   #booktime #livros #leitura
   ```

4. Commit.

### Disparar a publicação

1. Vá na aba **Actions** do repositório.

2. No menu lateral esquerdo, clique em **Publicar no Instagram**.

3. Clique no botão **Run workflow** (canto direito) e confirme.

4. Aguarde uns 30-60 segundos. Você vai ver o workflow rodando.

5. Clique no workflow rodando pra ver os logs em tempo real. Você vai ver mensagens como:
   ```
   📂 Próximo post: 2026-05-15-teste
   🖼️  Imagem: imagem.jpg
   📤 Criando container de mídia...
   ⏳ Aguardando processamento do container...
   🚀 Publicando no Instagram...
   ✅ Publicado! Media ID: ...
   ```

6. **Confira no Instagram da BookTime — o post deve estar lá!** 🎉

7. Depois do post, a pasta `2026-05-15-teste/` vai ser movida automaticamente pra `posts/published/`. Isso é commitado pelo próprio bot do Actions.

---

## Renovação automática do token (opcional mas recomendado)

O token de 60 dias **expira**. Se não renovar, a automação para de funcionar.

Você tem duas opções:

### Opção A — Renovar manualmente a cada 50 dias

Refaz os passos 2, 3 e atualiza o secret `IG_ACCESS_TOKEN` no GitHub. Fim.

### Opção B — Renovação automática (recomendado)

Já tem um workflow pronto (`.github/workflows/refresh-token.yml`) que roda todo dia 1º do mês e renova o token. Pra ele funcionar, você precisa criar um **Personal Access Token (PAT)** do GitHub com permissão pra atualizar secrets.

**Como criar o PAT:**

1. Acesse [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta) (Fine-grained tokens).

2. Clique em **Generate new token**.

3. Configure:
   - **Token name**: `BookTime Instagram Auto - Refresh Secrets`
   - **Expiration**: 1 ano (ou o máximo permitido)
   - **Repository access**: **Only select repositories** → escolha `booktime-instagram-auto`
   - **Permissions → Repository permissions**: encontre **Secrets** e mude pra **Read and write**

4. Clique em **Generate token** e **copie o valor** (ele só aparece uma vez).

5. Volte no repositório → **Settings → Secrets and variables → Actions → New repository secret**:
   - Nome: `GH_PAT_FOR_SECRETS`
   - Valor: o PAT que você acabou de copiar

6. Pronto. O workflow vai rodar automaticamente todo dia 1º.

> 💡 **Teste antes**: vá em **Actions → Renovar token do Instagram → Run workflow** pra rodar manualmente uma vez e confirmar que está funcionando. Se der erro, os logs vão te dizer o que está faltando.

---

## Solução de problemas

### "❌ ERRO: variável de ambiente IG_ACCESS_TOKEN não foi definida"
Algum secret está faltando no GitHub. Confira na aba **Settings → Secrets and variables → Actions** se todos os secrets necessários existem com o nome **exato** (maiúsculas e minúsculas importam).

### "❌ ERRO ao criar container: HTTP 400"
Geralmente é uma destas causas:
- **Token expirou**: refaça os passos 2 e 3 e atualize o secret `IG_ACCESS_TOKEN`.
- **Imagem fora do formato aceito**: confira razão de aspecto e tamanho.
- **URL da imagem não está pública**: se o repo é privado, a URL `raw.githubusercontent.com` não funciona sem autenticação. Para repo privado, considere usar Cloudflare R2 (veja seção "expansões futuras").

### "❌ ERRO: container falhou com status ERROR"
A Meta rejeitou a imagem. Causas mais comuns:
- Imagem corrompida
- Formato fora do padrão (use JPG ou PNG, não WebP/HEIC)
- Dimensões ou razão de aspecto fora do permitido

### "Repositório privado — imagem não publica"
Quando o repo é privado, `raw.githubusercontent.com` exige autenticação, e o Instagram não consegue baixar a imagem. Soluções:
- Deixar o repo público (não recomendado se houver conteúdo sensível)
- Mover as imagens pra um bucket externo (Cloudflare R2, AWS S3)

Se for migrar pra bucket externo, me avisa que monto a versão.

### "Não estou achando a aba Actions / botão Run workflow"
Verifique se o GitHub Actions está habilitado para o repositório em **Settings → Actions → General → Allow all actions**.

### "Quero cancelar um post antes de publicar"
Antes de clicar em "Run workflow", apague a pasta do post em `posts/`. Se já clicou e ainda está rodando, pode parar pela própria UI do Actions.

---

## Expansões futuras

Quando precisar evoluir, dá pra adicionar:

- **Carrosséis (múltiplas imagens)** — usar `is_carousel_item=true` e container pai
- **Reels (vídeos)** — `media_type=REELS`, upload de vídeo, mais permissões
- **Agendamento por horário** — adicionar `cron schedule` no `publish.yml`
- **Múltiplas contas** — separar por pasta (`posts/booktime/`, `posts/ecclesiae/`) e ler conta-alvo via metadado
- **Geração de caption por IA** — chamar API da Anthropic dentro do script
- **Repositório privado com bucket externo** — migrar imagens pra Cloudflare R2

---

## Arquivos do projeto

```
booktime-instagram-auto/
├── .github/
│   └── workflows/
│       ├── publish.yml              # Workflow manual de publicação
│       └── refresh-token.yml        # Workflow agendado de renovação
├── scripts/
│   ├── post_to_instagram.py         # Script principal
│   └── refresh_token.py             # Renovação automática do token
├── posts/                           # Pasta de posts pendentes
│   └── README.md                    # Instruções de estrutura
├── .gitignore
├── README.md                        # Este arquivo
└── requirements.txt                 # Dependências Python
```
