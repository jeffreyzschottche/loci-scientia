import { defineNuxtPlugin } from '#app'
import { useI18nStore } from '~/stores/i18n'

export default defineNuxtPlugin(() => {
  const store = useI18nStore()
  store.initLocale()
})
