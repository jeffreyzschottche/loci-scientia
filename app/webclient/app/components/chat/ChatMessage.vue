<template>
  <div :class="messageClasses">
    <div v-if="message.role === 'assistant'">
      <div v-if="hasVisibleAssistantContent" class="flex min-w-0 items-start gap-3">
        <div class="flex-shrink-0">
          <div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xl">
            🥚
          </div>
        </div>
        <div class="min-w-0 flex-1">
          <div class="min-w-0 overflow-hidden bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div class="flex min-w-0 items-center justify-between gap-2 mb-2">
              <span class="text-sm font-medium text-gray-900">AITJE</span>
              <div class="flex flex-shrink-0 gap-2">
                <button
                  @click="copyMessage"
                  class="text-xs px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  {{ copyLabel }}
                </button>
                <button
                  @click="printMessage"
                  class="text-xs px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  {{ t('message.print') }}
                </button>
              </div>
            </div>
            <div
              v-if="hasThinking"
              class="mb-3 overflow-hidden rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2 text-sm text-gray-700 whitespace-pre-wrap break-words"
            >
              <div class="mb-1 text-[11px] font-semibold uppercase tracking-wide text-yellow-800">
                {{ t('chat.reasoning') }}
              </div>
              <div>{{ message.thinking }}</div>
            </div>
            <div v-if="hasAnswer" class="chat-content prose prose-sm max-w-none text-gray-800" v-html="renderedContent"></div>
            <div v-if="hasWebSources" class="mt-3 border-t border-gray-100 pt-2">
              <div class="text-[11px] font-semibold uppercase tracking-wide text-gray-500 mb-1">
                {{ t('chat.webSearch.sourcesHeading') }}
              </div>
              <ul class="space-y-1">
                <li
                  v-for="(source, index) in message.webSources"
                  :key="`${message.id}-source-${index}`"
                  class="text-xs"
                >
                  <a
                    :href="source.url"
                    :title="source.title"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-yellow-700 hover:underline"
                  >
                    {{ sourceHostname(source.url) }}
                  </a>
                </li>
              </ul>
            </div>
            <div class="text-xs text-gray-500 mt-2">{{ formattedTime }}</div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex min-w-0 items-start justify-end gap-3">
      <div class="min-w-0 flex-1 flex flex-col items-end">
        <div class="max-w-full overflow-hidden bg-black text-white rounded-lg shadow-sm px-4 py-2 sm:max-w-md">
          <div v-if="message.images?.length" class="mb-2 space-y-2">
            <img
              v-for="(image, index) in message.images"
              :key="`${message.id}-image-${index}`"
              :src="image"
              alt="Attached image"
              class="w-full max-h-56 object-contain rounded border border-gray-700 bg-gray-900"
            />
          </div>
          <div v-if="message.documents?.length" class="mb-2 space-y-1">
            <div
              v-for="(document, index) in message.documents"
              :key="`${message.id}-document-${index}`"
              class="min-w-0 px-2 py-1 rounded bg-gray-900 border border-gray-700 text-xs text-gray-100 break-words"
            >
              {{ document.filename }}
            </div>
          </div>
          <div v-if="message.content.trim()" class="whitespace-pre-wrap break-words">{{ message.content }}</div>
        </div>
        <div class="text-xs text-gray-500 mt-1">{{ formattedTime }}</div>
      </div>
      <div class="flex-shrink-0">
        <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-xl">
          👤
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import type { ChatMessage } from '~/stores/chat'
import { useI18n } from '~/composables/useI18n'

interface Props {
  message: ChatMessage
}

const props = defineProps<Props>()

const { t, locale } = useI18n()
const copied = ref(false)

const messageClasses = computed(() => {
  return 'mb-4'
})

const hasAnswer = computed(() => props.message.content.trim().length > 0)
const hasThinking = computed(() => props.message.thinking?.trim().length ? true : false)
const hasWebSources = computed(() => (props.message.webSources?.length ?? 0) > 0)
const hasVisibleAssistantContent = computed(() => hasAnswer.value || hasThinking.value || hasWebSources.value)

const sourceHostname = (url: string) => {
  try {
    return new URL(url).hostname
  } catch (_e) {
    return url
  }
}

const renderedContent = computed(() => {
  if (props.message.role === 'assistant') {
    return marked.parse(props.message.content, { breaks: true })
  }
  return props.message.content
})

const formattedTime = computed(() => {
  const date = new Date(props.message.timestamp)
  const localeTag = locale.value === 'en' ? 'en-US' : 'nl-NL'
  return date.toLocaleTimeString(localeTag, { hour: '2-digit', minute: '2-digit' })
})

const copyLabel = computed(() => (copied.value ? t('message.copied') : t('message.copy')))

const copyMessage = async () => {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

const printMessage = () => {
  const printWindow = window.open('', '', 'width=600,height=400')
  if (printWindow) {
    printWindow.document.write(`
      <html>
        <head>
          <title>${t('message.printTitle')}</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .header { margin-bottom: 20px; }
            .reasoning { margin-bottom: 16px; padding: 12px; background: #fef3c7; border: 1px solid #fde68a; border-radius: 8px; white-space: pre-wrap; }
            .content { white-space: pre-wrap; }
          </style>
        </head>
        <body>
          <div class="header">
            <h2>AITJE</h2>
            <p>${formattedTime.value}</p>
          </div>
          ${hasThinking.value ? `<div class="reasoning"><strong>${t('chat.reasoning')}</strong><br>${props.message.thinking}</div>` : ''}
          <div class="content">${props.message.content}</div>
        </body>
      </html>
    `)
    printWindow.document.close()
    printWindow.print()
  }
}
</script>

<style scoped>
.chat-content {
  overflow-wrap: anywhere;
  word-break: break-word;
}

.chat-content :deep(*) {
  max-width: 100%;
}

.chat-content :deep(pre) {
  overflow-x: auto;
  white-space: pre-wrap;
}

.chat-content :deep(code) {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.chat-content :deep(table) {
  display: block;
  overflow-x: auto;
}
</style>
