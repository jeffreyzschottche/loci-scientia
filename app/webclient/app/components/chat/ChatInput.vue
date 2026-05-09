<template>
  <div class="bg-white p-3 border-t border-gray-200 pb-safe">
    <form
      @submit.prevent="handleSubmit"
      class="flex gap-2 items-center max-w-4xl mx-auto"
    >
      <input
        v-model="inputText"
        type="text"
        :placeholder="t('chat.placeholder')"
        :disabled="disabled"
        autofocus
        class="flex-1 px-3 py-2 text-sm border-2 border-gray-300 rounded-full focus:border-yellow-400 focus:outline-none disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors min-w-0"
      />
      <button
        type="submit"
        :disabled="disabled || !inputText.trim()"
        class="bg-black hover:bg-gray-800 text-white font-medium px-4 py-2 text-sm rounded-full transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex-shrink-0"
      >
        <span class="text-lg leading-none">➤</span>
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from '~/composables/useI18n'

interface Props {
  disabled?: boolean
}

interface Emits {
  (e: 'send', message: string): void
}

defineProps<Props>()
const emit = defineEmits<Emits>()
const { t } = useI18n()

const inputText = ref('')

const handleSubmit = () => {
  if (inputText.value.trim()) {
    emit('send', inputText.value.trim())
    inputText.value = ''
  }
}
</script>
