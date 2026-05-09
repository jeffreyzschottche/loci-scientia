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
      viewport: 'width=device-width, initial-scale=1, viewport-fit=cover',
    },
  },
  vite: {
    clearScreen: false,
    server: { strictPort: true },
  },
  devtools: { enabled: true }
})
