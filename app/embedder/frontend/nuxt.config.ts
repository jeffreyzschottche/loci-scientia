export default defineNuxtConfig({
  srcDir: '.',
  compatibilityDate: '2024-01-09',

  // SPA-only: deze app wordt statisch gegenereerd (npm run generate) en door
  // FastAPI op http://aitje-<n>.local:8000/embedder/ gehost — zie
  // app/backend/main.py voor de mount + reverse-proxy naar Laravel.
  ssr: false,

  app: {
    baseURL: '/embedder/',
    buildAssetsDir: '_nuxt/',
    head: {
      title: 'AITJE',
      meta: [
        { name: 'robots', content: 'noindex, nofollow' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/embedder/favicon.ico' },
        { rel: 'apple-touch-icon', href: '/embedder/aitje.png' },
      ],
    },
  },

  css: ['~/assets/css/tailwind.css'],

  modules: ['@pinia/nuxt'],

  postcss: {
    plugins: {
      tailwindcss: {},
      autoprefixer: {},
    },
  },

  runtimeConfig: {
    public: {
      // Same-origin: FastAPI proxiet /embedder/api/* naar Laravel op de loopback.
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || '/embedder/api/v1',
    },
  },

  devtools: { enabled: true },
});
