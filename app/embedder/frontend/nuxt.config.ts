const eggFavicon =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ctext x='32' y='48' text-anchor='middle' font-size='48'%3E%F0%9F%A5%9A%3C/text%3E%3C/svg%3E"

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
        { rel: 'icon', href: eggFavicon },
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
