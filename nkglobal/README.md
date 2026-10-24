# NK Global Services — site institucional

Astro (estático) · 4 páginas: `/`, `/quem-somos`, `/servicos`, `/diferenciais`.

- **WhatsApp oficial:** `src/config/site.ts` (`WHATSAPP_NUMBER`) — único lugar com o número.
- **Textos:** `src/content/*.ts`.
- **Redes sociais / Privacidade / Termos:** URLs não foram fornecidas; preencha `SOCIAL` e `LEGAL` em `src/config/site.ts` (sem URL, não são exibidas como link).
- **Vercel:** importe o repositório e defina **Root Directory = `nkglobal`** (framework Astro é detectado). Opcional: variável `SITE_URL` com o domínio final.

```bash
cd nkglobal && npm install && npm run dev   # desenvolvimento
npm run build                                # gera dist/
```
