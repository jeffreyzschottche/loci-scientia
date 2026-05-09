import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18nStore, type Locale, type TranslationKey } from '~/stores/i18n'

export const useI18n = () => {
  const store = useI18nStore()
  const { locale } = storeToRefs(store)

  const t = (key: TranslationKey, vars?: Record<string, string | number>) => {
    return store.translate(key, vars)
  }

  const availableLocales = computed(() => store.availableLocales)

  const setLocale = (nextLocale: Locale) => {
    store.setLocale(nextLocale)
  }

  return {
    t,
    locale,
    setLocale,
    availableLocales,
  }
}

export type { Locale }
