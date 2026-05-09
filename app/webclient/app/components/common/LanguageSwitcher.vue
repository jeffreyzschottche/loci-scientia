<template>
  <div class="relative inline-flex" ref="rootEl">
    <button
      type="button"
      class="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white shadow-sm transition-colors"
      :class="buttonClass"
      @click="toggleDropdown"
      :aria-haspopup="'menu'"
      :aria-expanded="isOpen.toString()"
    >
      <span :class="flagClass">{{ currentOption.flag }}</span>
      <span class="uppercase tracking-wide">{{ currentOption.short }}</span>
      <svg
        class="w-3 h-3 text-gray-500"
        viewBox="0 0 12 8"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M1 1.5L6 6.5L11 1.5"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 mt-2 w-32 rounded-lg border border-gray-200 bg-white shadow-lg z-50 py-1"
      role="menu"
    >
      <button
        v-for="option in languageOptions"
        :key="option.locale"
        type="button"
        @click="selectLanguage(option.locale)"
        class="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 transition-colors"
        :class="option.locale === locale ? 'font-semibold text-gray-900' : 'text-gray-600'"
      >
        <span class="text-lg leading-none">{{ option.flag }}</span>
        <span>{{ t(option.labelKey) }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useI18n } from '~/composables/useI18n'
import type { Locale, TranslationKey } from '~/stores/i18n'

interface Props {
  size?: 'sm' | 'xs'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'sm',
})

const { t, locale, setLocale } = useI18n()
const isOpen = ref(false)
const rootEl = ref<HTMLElement | null>(null)

const languageOptions: Array<{
  locale: Locale
  flag: string
  short: string
  labelKey: TranslationKey
}> = [
  { locale: 'nl', flag: '🇳🇱', short: 'NL', labelKey: 'common.language.nl' },
  { locale: 'en', flag: '🇬🇧', short: 'EN', labelKey: 'common.language.en' },
]

const buttonClass = computed(() =>
  props.size === 'xs' ? 'px-2 py-1 text-[10px]' : 'px-3 py-1.5 text-xs',
)
const flagClass = computed(() => (props.size === 'xs' ? 'text-sm leading-none' : 'text-base leading-none'))
const currentOption = computed(() => languageOptions.find((opt) => opt.locale === locale.value) || languageOptions[0])

const selectLanguage = (nextLocale: Locale) => {
  setLocale(nextLocale)
  isOpen.value = false
}

const toggleDropdown = () => {
  isOpen.value = !isOpen.value
}

const handleClickOutside = (event: MouseEvent) => {
  if (!rootEl.value) return
  if (!rootEl.value.contains(event.target as Node)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
