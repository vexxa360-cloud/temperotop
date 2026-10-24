# NK Global Services — site institucional

Astro (estático) · 4 páginas: `/`, `/quem-somos`, `/servicos`, `/diferenciais`.

- **WhatsApp oficial:** `src/config/site.ts` (`WHATSAPP_NUMBER`) — único lugar com o número.
- **Textos:** `src/content/*.ts`.
- **Redes sociais / Privacidade / Termos:** URLs não foram fornecidas; preencha `SOCIAL` e `LEGAL` em `src/config/site.ts` (sem URL, não são exibidas como link).
- **Hospedagem (Cloudflare Pages):** Root directory `nkglobal`, build `npm run build`, output `dist`, variável `NODE_VERSION=22`. Domínio oficial: `https://nkglobal.com.br` (configurado em `astro.config.mjs`).
- Também funciona na Vercel (`vercel.json`), mas o plano gratuito não permite uso comercial.

```bash
cd nkglobal && npm install && npm run dev   # desenvolvimento
npm run build                                # gera dist/
```
