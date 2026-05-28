// https://nuxt.com/docs/api/configuration/nuxt-config
const eggFavicon =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ctext x='32' y='48' text-anchor='middle' font-size='48'%3E%F0%9F%A5%9A%3C/text%3E%3C/svg%3E"

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt'],
  ssr: false,
  devServer: {
    port: 3000,
  },
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      title: 'AITJE',
      viewport: 'width=device-width, initial-scale=1, viewport-fit=cover',
      link: [
        { rel: 'icon', href: eggFavicon },
      ],
    },
  },
  vite: {
    clearScreen: false,
    server: { strictPort: true },
  },
  devtools: { enabled: true }
})
