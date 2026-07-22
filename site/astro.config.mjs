import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://acolhimento.org',
  integrations: [vue(), sitemap()],
  build: { format: 'directory' },
});
