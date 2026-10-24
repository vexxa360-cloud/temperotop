import { defineConfig } from 'astro/config';

// Domínio oficial (canonical/OG). Pode ser sobrescrito pela variável SITE_URL no build.
export default defineConfig({
  site: process.env.SITE_URL || 'https://nkglobal.com.br',
  trailingSlash: 'never',
  build: { format: 'file' },
});
