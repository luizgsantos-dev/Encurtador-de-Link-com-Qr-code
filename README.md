# Encurtador de Links com QR Code

Solução self-hosted para encurtar links, com destino editável a qualquer momento, geração de QR
code, UTM builder e estatísticas de cliques (total, por dia, por dispositivo e por referrer).

## Como rodar

1. Copie o arquivo de variáveis de ambiente e ajuste os valores (usuário/senha do admin inicial,
   senha do banco, `JWT_SECRET`):

   ```
   cp .env.example .env
   ```

2. Suba os containers:

   ```
   docker compose up --build -d
   ```

3. Acesse `http://localhost:8080/login.html` (ou a porta definida em `WEB_PORT`) e entre com
   `ADMIN_USERNAME` / `ADMIN_PASSWORD`. Esse usuário admin só é criado automaticamente na primeira
   inicialização (banco sem nenhum usuário).
4. Como admin, crie grupos em **Grupos** (ex: Marketing, Relacionamento) e usuários em
   **Usuários**, associando cada um aos grupos que deve enxergar. Um usuário comum só vê e gerencia
   links dos grupos aos quais pertence; o admin enxerga todos os grupos e links.

Se a solução for exposta publicamente atrás de HTTPS, ajuste `BASE_URL` para o domínio real e
`COOKIE_SECURE=true` no `.env`.

## Arquitetura

- **db**: PostgreSQL, guarda usuários, grupos, links e cliques.
- **api**: FastAPI — CRUD de links/usuários/grupos, autenticação (JWT em cookie httponly, senha com
  hash bcrypt), geração de QR code, estatísticas e o próprio redirecionamento (`GET /{codigo}`).
- **web**: Nginx, serve o painel estático e atua como proxy reverso único na porta 8080:
  - `/api/*` → backend
  - `/login.html`, `/dashboard.html`, `/link-detail.html`, `/users.html`, `/groups.html`,
    `/assets/*` → painel
  - qualquer outro caminho (`/{codigo}`) → backend, que faz o redirect e registra o clique

## Funcionalidades

- Login multiusuário: cada conta tem usuário/senha próprios; apenas administradores criam e
  gerenciam contas (não há autocadastro).
- Grupos configuráveis pelo admin (ex: Marketing, Relacionamento): cada usuário pode pertencer a
  vários grupos e só enxerga os links dos grupos aos quais pertence. Administradores enxergam todos
  os grupos e links.
- Ao criar ou editar um link, o usuário escolhe manualmente a qual grupo ele pertence (entre os
  grupos aos quais tem acesso).
- Link curto estático: o código nunca muda, mas o destino pode ser editado quando quiser.
- Geração de QR code (PNG ou SVG) apontando para o link curto.
- UTM Builder no formulário de criação/edição: monta a URL de destino com `utm_source`,
  `utm_medium`, `utm_campaign`, `utm_term` e `utm_content`, com prévia em tempo real.
- Estatísticas por link: total de cliques, gráfico dos últimos 30 dias, dispositivo
  (mobile/desktop/tablet/bot) e principais referrers.
- Ativar/desativar um link sem excluí-lo (desativado retorna 404 no redirect).

## Desenvolvimento local sem Docker (opcional)

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Nesse modo, sirva os arquivos de `frontend/` com qualquer servidor estático e ajuste `API_BASE` em
`frontend/assets/js/api.js` se a API não estiver no mesmo host/porta.
