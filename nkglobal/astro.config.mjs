import { defineConfig } from 'astro/config';

// Defina SITE_URL na Vercel (ex.: https://www.seudominio.com.br) para URLs absolutas em OG/canonical.
export default defineConfig({
  site: process.env.SITE_URL || undefined,
  trailingSlash: 'never',
  build: { format: 'file' },
});
