<template>
  <div
    ref="scrollContainer"
    class="flex-1 overflow-y-auto px-6 py-6 bg-gray-50"
  >
    <div class="max-w-4xl mx-auto">
      <div v-if="messages.length === 0" class="text-center text-gray-500 mt-12">
        <p class="text-lg">{{ t('chat.emptyState') }}</p>
      </div>

      <ChatMessage
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />

      <div v-if="isLoading" class="mb-4">
        <div class="flex items-start gap-3">
          <div class="flex-shrink-0">
            <div
              class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xl"
            >
              🥚
            </div>
          </div>
          <div class="flex-1">
            <div
              class="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
            >
              <div class="flex gap-1">
                <div
                  class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style="animation-delay: 0ms"
                ></div>
                <div
                  class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style="animation-delay: 150ms"
                ></div>
                <div
                  class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style="animation-delay: 300ms"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { ChatMessage as ChatMessageType } from '~/stores/chat'
import ChatMessage from './ChatMessage.vue'
import { useI18n } from '~/composables/useI18n'

interface Props {
  messages: ChatMessageType[]
  isLoading?: boolean
}

const props = defineProps<Props>()
const { t } = useI18n()

const scrollContainer = ref<HTMLElement | null>(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollContainer.value) {
      scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
    }
  })
}

watch(
  () => props.messages.length,
  () => {
    scrollToBottom()
  },
)

watch(
  () => props.isLoading,
  () => {
    scrollToBottom()
  },
)
</script>
