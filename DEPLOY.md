# Publicar o TemperoTop online (produção)

O site (landing page) é servido pelo próprio backend Node/Express, que também
processa o pagamento (Mercado Pago) e o painel de pedidos. Publicando o backend,
tudo vai junto, com **HTTPS** e **URL pública** (necessária para o webhook do Pix).

Guia usando a **Render** (grátis para começar). Alternativas: Railway, Fly.io, VPS.

---

## 1) Subir o código para o GitHub

1. Crie um repositório no GitHub (privado de preferência).
2. Na pasta do projeto:
   ```bash
   git init
   git add .
   git commit -m "TemperoTop"
   git branch -M main
   git remote add origin https://github.com/SEU-USUARIO/temperotop.git
   git push -u origin main
   ```
   > O `.gitignore` já protege `.env`, `node_modules` e `data/` (não vão para o Git).

## 2) Criar o serviço na Render

1. Acesse https://render.com e crie uma conta (pode logar com o GitHub).
2. **New +** → **Blueprint** → conecte o repositório. A Render lê o `render.yaml`
   automaticamente e cria o serviço `temperotop`.
   - (Ou **New + → Web Service**, apontando a pasta `backend`, build `npm install`,
     start `npm start`.)

## 3) Definir as variáveis de ambiente (na Render)

No painel do serviço → **Environment** → adicione:

| Variável | Valor |
|----------|-------|
| `MP_PUBLIC_KEY` | sua Public Key do Mercado Pago |
| `MP_ACCESS_TOKEN` | seu Access Token (secreto) |
| `ADMIN_TOKEN` | um token forte para o painel `/admin` |
| `BASE_URL` | a URL pública (ex.: `https://temperotop.onrender.com`) |

Salve e aguarde o deploy terminar.

## 4) Configurar o Webhook no Mercado Pago

Para o pagamento (principalmente **Pix**) ser confirmado automaticamente:

1. Painel do Mercado Pago → sua aplicação → **Webhooks / Notificações**.
2. URL de produção:
   ```
   https://SEU-DOMINIO/api/webhook/mercadopago
   ```
3. Evento: **Pagamentos (payment)**.

## 5) Testar em produção

- Abra `https://SEU-DOMINIO` e faça um pedido.
- Painel de pedidos: `https://SEU-DOMINIO/admin?token=SEU_ADMIN_TOKEN`

---

## Recomendações de segurança

- **Rotacione** o Access Token que já foi usado em conversa/testes.
- Nunca comite o `.env` (o `.gitignore` já cobre).
- Comece com **credenciais de TESTE** para validar sem cobrar; depois troque para
  produção.

## Persistência dos pedidos

Os pedidos ficam em `backend/data/orders.json`. Na Render, o `render.yaml` já cria
um **disco persistente** para essa pasta. Para grande volume, migre para um banco
(Postgres/Mongo) mantendo as funções de `backend/store.js`.
