// https://nuxt.com/docs/api/configuration/nuxt-config
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
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
        { rel: 'apple-touch-icon', href: '/appicon.png' },
      ],
    },
  },
  vite: {
    clearScreen: false,
    server: { strictPort: true },
  },
  devtools: { enabled: true }
})
