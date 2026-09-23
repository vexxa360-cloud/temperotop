# Integração Mercado Pago — Porta-Temperos 360°

O frontend (`index.html`) chama `POST /api/create-preference`. O backend cria uma
**preferência de pagamento** no Mercado Pago e devolve o `init_point` — o link para
onde o cliente é redirecionado para pagar. **As credenciais ficam só no servidor.**

## Passo a passo

1. Instale o [Node.js](https://nodejs.org) (versão 18+).
2. No terminal, entre na pasta do backend:
   ```bash
   cd backend
   npm install
   ```
3. Crie o arquivo de credenciais a partir do exemplo:
   ```bash
   copy .env.example .env      # Windows
   # ou:  cp .env.example .env  (Mac/Linux)
   ```
4. Abra o `.env` e cole o seu **Access Token** do Mercado Pago:
   - Acesse https://www.mercadopago.com.br/developers
   - **Suas integrações → Credenciais**
   - Use `TEST-...` para testar e `APP_USR-...` em produção.
5. Inicie o servidor:
   ```bash
   npm start
   ```
6. Abra **http://localhost:3000** — o site e o pagamento já funcionam juntos.

## Como funciona o fluxo

1. Cliente preenche o formulário (Nome, CPF, Telefone, E-mail).
2. Ao digitar o **CEP**, o endereço (Rua, Bairro, Cidade, UF) é preenchido
   automaticamente via **ViaCEP**; o cliente só informa **Número** e **Complemento**.
3. O frontend envia os dados para `POST /api/create-preference`.
4. O backend **revalida o CEP na ViaCEP** (não confia só no navegador), valida os
   demais campos, **cria um PEDIDO com ID** (ex.: `PEDIDO #000123`) e salva o
   endereço vinculado a esse pedido em `backend/data/orders.json`.
5. O backend cria a preferência do Mercado Pago com `external_reference = ID do pedido`
   e devolve o `init_point`.
6. O cliente é redirecionado ao checkout do Mercado Pago.
7. Após o pagamento, volta para `/?status=success|failure|pending&pedido=<id>`.

## Busca automática de CEP

- Aceita CEP com ou sem máscara (`08400000` ou `08400-000`) e aplica `00000-000`.
- Consulta automática ao completar 8 dígitos, com aviso “Buscando endereço...”.
- CEP não encontrado → “CEP não encontrado. Verifique o número informado.”
- API indisponível → “Não foi possível consultar o CEP agora. Preencha o endereço
  manualmente.” (os campos são liberados e a compra **não** é bloqueada).
- Após preencher, o cursor vai automaticamente para **Número**.
- Endpoint de validação no servidor: `GET /api/cep/:cep`.

## Painel administrativo (preparar envios)

- **Dashboard** `/admin` — contadores em tempo real por etapa + fila "Próximas ações".
- **Detalhe** `/admin/orders/<id>` — barra de progresso, painel de avanço rápido,
  dados do cliente, endereço completo para etiqueta e histórico de auditoria.
- Proteção: defina `ADMIN_TOKEN` no `.env` e acesse com `?token=SEU_ADMIN_TOKEN`.
  Em localhost, sem token definido, o painel é liberado apenas para `127.0.0.1`.
- Os pedidos ficam em `backend/data/orders.json` (troque por um banco em produção
  mantendo as funções de `store.js`).

## Ciclo de vida do pedido (3 status independentes)

Cada pedido tem **três status separados** e rastreáveis:

| Campo | Valores |
|-------|---------|
| **Pagamento** | pendente → em processamento → aprovado (ou rejeitado/cancelado/reembolsado) |
| **Operação** | aguardando → faturado → separação → pronto para envio |
| **Envio** | aguardando → enviado → acompanhamento → em trânsito → saiu para entrega → entregue |

A **barra de progresso** (13 estágios) é derivada desses três campos.

### Avanço automático do pagamento (webhook)

- Endpoint: `POST /api/webhook/mercadopago` (informado ao MP como `notification_url`).
- Quando o Mercado Pago confirma, o pagamento avança **sozinho** — o admin não marca
  "aprovado" manualmente. Fica registrado: origem, ID da transação, status e data/hora.
- **Modo de teste** (sem credenciais): envie
  `POST /api/webhook/mercadopago` com `{"orderId":"000001","status":"approved"}`.

### Regras de segurança

- Etapas operacionais (faturar/separar/enviar…) só liberam com **pagamento aprovado**;
  antes disso o painel mostra "AGUARDANDO CONFIRMAÇÃO DO PAGAMENTO".
- Não é possível pular etapas (a sequência é validada no servidor).
- Alteração manual de pagamento é **excepcional** e exige **motivo + responsável**,
  ficando tudo no log de auditoria (origem MANUAL).

### Auditoria

Toda mudança grava: pedido, campo, etapa anterior → nova etapa, responsável,
data, hora e origem (AUTOMÁTICA ou MANUAL).

## Observações
- Enquanto o `.env` não estiver configurado, o site valida o formulário e exibe um
  aviso amigável — nada quebra.
- Nunca coloque o Access Token no frontend nem suba o `.env` para repositórios.
- Para hospedar, publique estes arquivos em qualquer serviço Node (Render, Railway,
  Vercel Serverless, VPS etc.) e defina as variáveis de ambiente lá.
