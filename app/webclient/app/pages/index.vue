<template>
  <NuxtLayout name="default">
    <div class="relative h-full w-full overflow-hidden flex flex-col">
      <!-- Header -->
      <header class="bg-white border-b border-gray-200 py-1 pt-safe">
        <div
          class="mx-auto flex items-center justify-between gap-2"
          :class="isNativeMobileApp ? 'w-[94%]' : ''"
          :style="isNativeMobileApp ? undefined : 'width: 80%; max-width: 1200px;'"
        >
          <div class="flex items-center">
            <img
              src="/aitje-logox.png"
              alt="AITJE"
              :class="isNativeMobileApp ? 'h-[40px] w-auto' : 'h-[54px] w-auto'"
            />
          </div>
          <div class="flex items-center gap-1.5 sm:gap-2">
            <LanguageSwitcher :size="isNativeMobileApp ? 'xs' : 'sm'" />
            <button
              @click="handleLogout"
              class="bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-medium rounded-full transition-colors whitespace-nowrap"
              :class="isNativeMobileApp ? 'px-2 py-1 text-[10px]' : 'px-2 py-1 text-[10px]'"
            >
              {{ t('header.logout') }}
            </button>
            <button
              @click="handleChangeDevice"
              class="bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-medium rounded-full transition-colors whitespace-nowrap"
              :class="isNativeMobileApp ? 'px-2 py-1 text-[10px]' : 'px-2 py-1 text-[10px]'"
            >
              {{ t('header.switchDevice') }}
            </button>
          </div>
        </div>
      </header>

      <!-- Gele status balk -->
      <div class="bg-yellow-400 border-b border-yellow-500 py-2">
        <div
          class="mx-auto"
          :class="isNativeMobileApp ? 'w-[94%]' : ''"
          :style="isNativeMobileApp ? undefined : 'width: 80%; max-width: 1200px;'"
        >
          <div
            class="flex items-center justify-between gap-3"
            :class="isNativeMobileApp ? 'min-w-0' : ''"
          >
            <div class="flex min-w-0 items-center gap-2 text-gray-900 font-medium" :class="isNativeMobileApp ? 'text-[12px]' : 'text-xs'">
              <div class="h-2 w-2 flex-shrink-0 rounded-full bg-green-500"></div>
              <span class="truncate whitespace-nowrap">{{ t('status.connectedLabel') }} <span class="font-semibold">{{ connectedDeviceLabel }}</span></span>
            </div>

            <div v-if="isNativeMobileApp" class="relative flex flex-shrink-0 items-center gap-2" ref="settingsMenuRef">
              <button
                type="button"
                :disabled="chatStore.isLoading"
                class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-black/10 bg-white/85 text-gray-900 shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Instellingen"
                @click="toggleSettingsMenu"
              >
                <span class="text-base leading-none">⚙️</span>
              </button>

              <button
                @click="openNewChatModal"
                :disabled="chatStore.messages.length === 0"
                class="rounded-full bg-black px-3 py-2 text-[12px] font-medium text-white transition-colors whitespace-nowrap hover:text-yellow-400 disabled:cursor-not-allowed disabled:bg-black disabled:text-white disabled:hover:text-white"
              >
                {{ t('header.newChat') }}
              </button>

              <div
                v-if="showSettingsMenu"
                class="absolute right-0 top-full z-30 mt-2 w-52 rounded-2xl border border-yellow-200 bg-white p-3 shadow-lg"
              >
                <p class="text-sm font-semibold text-gray-900">Instellingen</p>
                <div class="mt-3 flex items-center justify-between gap-3 rounded-xl bg-gray-50 px-3 py-2">
                  <span class="text-sm font-medium text-gray-700">{{ t('chat.reasoning') }}</span>
                  <button
                    type="button"
                    role="switch"
                    :aria-checked="thinkingEnabled"
                    :disabled="chatStore.isLoading"
                    class="relative inline-flex h-6 w-11 items-center rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-60"
                    :class="thinkingEnabled ? 'border-yellow-500 bg-yellow-400' : 'border-gray-300 bg-gray-200'"
                    @click="thinkingEnabled = !thinkingEnabled"
                  >
                    <span
                      class="absolute left-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-all"
                      :class="thinkingEnabled ? 'translate-x-5' : 'translate-x-0'"
                    />
                  </button>
                </div>
                <div class="mt-2 flex items-center justify-between gap-3 rounded-xl bg-gray-50 px-3 py-2">
                  <span class="text-sm font-medium text-gray-700">{{ t('chat.webSearch.toggleLabel') }}</span>
                  <button
                    type="button"
                    role="switch"
                    :aria-checked="webSearchEnabled"
                    :disabled="chatStore.isLoading"
                    class="relative inline-flex h-6 w-11 items-center rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-60"
                    :class="webSearchEnabled ? 'border-yellow-500 bg-yellow-400' : 'border-gray-300 bg-gray-200'"
                    @click="webSearchEnabled = !webSearchEnabled"
                  >
                    <span
                      class="absolute left-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-all"
                      :class="webSearchEnabled ? 'translate-x-5' : 'translate-x-0'"
                    />
                  </button>
                </div>
              </div>
            </div>

            <div v-else class="flex items-center gap-3">
              <button
                type="button"
                role="switch"
                :aria-checked="thinkingEnabled"
                :disabled="chatStore.isLoading"
                class="group inline-flex items-center gap-3 rounded-full border border-black/10 bg-white/75 px-2 py-1 text-xs font-semibold text-gray-900 shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-60"
                @click="thinkingEnabled = !thinkingEnabled"
              >
                <span class="pl-1">{{ t('chat.reasoning') }}</span>
                <span
                  :class="[
                    'relative inline-flex h-6 w-11 items-center rounded-full border transition-colors',
                    thinkingEnabled
                      ? 'border-yellow-500 bg-yellow-400'
                      : 'border-gray-300 bg-gray-200',
                  ]"
                >
                  <span
                    :class="[
                      'absolute left-0.5 h-5 w-5 rounded-full shadow-sm transition-all',
                      thinkingEnabled
                        ? 'translate-x-5 bg-white'
                        : 'translate-x-0 bg-white',
                    ]"
                  />
                </span>
              </button>

              <button
                type="button"
                role="switch"
                :aria-checked="webSearchEnabled"
                :disabled="chatStore.isLoading"
                class="group inline-flex items-center gap-3 rounded-full border border-black/10 bg-white/75 px-2 py-1 text-xs font-semibold text-gray-900 shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-60"
                @click="webSearchEnabled = !webSearchEnabled"
              >
                <span class="pl-1">{{ t('chat.webSearch.toggleLabel') }}</span>
                <span
                  :class="[
                    'relative inline-flex h-6 w-11 items-center rounded-full border transition-colors',
                    webSearchEnabled
                      ? 'border-yellow-500 bg-yellow-400'
                      : 'border-gray-300 bg-gray-200',
                  ]"
                >
                  <span
                    :class="[
                      'absolute left-0.5 h-5 w-5 rounded-full shadow-sm transition-all',
                      webSearchEnabled
                        ? 'translate-x-5 bg-white'
                        : 'translate-x-0 bg-white',
                    ]"
                  />
                </span>
              </button>

              <button
                @click="openNewChatModal"
                :disabled="chatStore.messages.length === 0"
                class="px-3 py-1 text-xs bg-black hover:text-yellow-400 disabled:bg-black disabled:text-white disabled:hover:text-white disabled:cursor-not-allowed text-white font-medium rounded-full transition-colors whitespace-nowrap"
              >
                {{ t('header.newChat') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Chat area - neemt alle resterende ruimte -->
      <div class="flex-1 overflow-hidden bg-gray-100" :class="isNativeMobileApp ? 'px-3 py-4' : 'p-6'">
        <div
          class="mx-auto relative h-full overflow-x-hidden overflow-y-auto rounded-2xl border border-gray-200 bg-white shadow-sm"
          :class="isNativeMobileApp ? 'w-full p-4' : 'p-6'"
          :style="isNativeMobileApp ? undefined : 'width: 80%; max-width: 1200px;'"
        >
          <div
            v-if="chatStore.messages.length === 0"
            class="pointer-events-none absolute inset-0 z-0 flex flex-col items-center justify-center px-6"
          >
            <p
              class="absolute left-1/2 -translate-x-1/2 text-gray-500 whitespace-nowrap"
              :class="isNativeMobileApp ? 'top-14 text-base' : 'top-24 text-lg'"
            >
              {{ t('chat.emptyState') }}
            </p>
            <div class="flex h-full w-full items-center justify-center">
              <img
                src="/aitje-chat-bg.png"
                alt=""
                aria-hidden="true"
                class="w-full object-contain opacity-[0.12]"
                :class="isNativeMobileApp ? 'max-w-[220px]' : 'max-w-[560px]'"
              />
            </div>
          </div>

          <div class="relative z-10 min-h-full flex min-w-0 flex-col justify-end">

            <ChatMessage
              v-for="message in chatStore.messages"
              :key="message.id"
              :message="message"
            />

            <div v-if="showLoadingIndicator" class="mb-4">
              <div class="flex items-start gap-3">
                <div class="flex-shrink-0">
                  <div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xl">
                    🥚
                  </div>
                </div>
                <div class="flex-1">
                  <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <div v-if="webSearchStatusLabel" class="flex items-center gap-2 text-xs text-gray-500">
                      <span class="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse"></span>
                      <span class="italic">{{ webSearchStatusLabel }}</span>
                    </div>
                    <div v-else class="flex gap-1">
                      <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                      <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                      <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="error" class="px-4 py-2 bg-red-50 border border-red-200 rounded-lg mb-4">
              <p class="text-sm text-red-600 text-center">{{ error }}</p>
            </div>

            <div
              v-else-if="stoppedGeneration"
              class="mb-4 rounded-xl border border-yellow-200 bg-yellow-50 px-4 py-3 text-center"
            >
              <p class="text-sm font-semibold text-gray-900">{{ t('chat.stoppedTitle') }}</p>
              <p class="mt-1 text-sm text-gray-700">{{ t('chat.stoppedMessage') }}</p>
            </div>
          </div>
        </div>

      </div>

        <div class="bg-gray-100" :class="isNativeMobileApp ? '-mt-4' : ''">
          <div
            class="mx-auto flex h-14 items-center justify-center"
            :class="isNativeMobileApp ? 'w-[94%]' : ''"
            :style="isNativeMobileApp ? undefined : 'width: 80%; max-width: 1200px;'"
          >
            <p
              class="inline-flex items-center rounded-full border border-gray-200 bg-white/95 shadow-sm backdrop-blur whitespace-nowrap"
              :class="isNativeMobileApp ? 'px-2.5 py-1 text-[10px] tracking-tight text-gray-500' : 'px-5 py-1.5 text-xs text-gray-500'"
            >
              {{ t('chat.disclaimer') }}
            </p>
          </div>
        </div>

      <div class="bg-white py-3" style="padding-bottom: calc(env(safe-area-inset-bottom) + 1em);">
        <div
          class="mx-auto space-y-2"
          :class="isNativeMobileApp ? 'w-[94%]' : ''"
          :style="isNativeMobileApp ? undefined : 'width: 80%; max-width: 1200px;'"
        >
            <div v-if="selectedImages.length > 0" class="flex gap-2 overflow-x-auto pb-1">
              <div
                v-for="image in selectedImages"
                :key="image.id"
                class="relative w-16 h-16 flex-shrink-0"
              >
                <img
                  :src="image.dataUrl"
                  :alt="image.name"
                  class="w-full h-full object-cover rounded-lg border border-gray-300"
                />
                <button
                  type="button"
                  @click="removeSelectedImage(image.id)"
                  :aria-label="t('chat.removeImage')"
                  class="absolute top-1 right-1 w-5 h-5 bg-black text-white text-xs rounded-full flex items-center justify-center shadow-sm"
                >
                  x
                </button>
              </div>
            </div>

            <div v-if="selectedDocuments.length > 0" class="flex gap-2 overflow-x-auto pb-1">
              <div
                v-for="document in selectedDocuments"
                :key="document.id"
                class="relative min-w-[180px] max-w-[260px] px-3 py-2 rounded-lg border border-gray-300 bg-gray-50"
              >
                <div class="text-xs text-gray-900 truncate">{{ document.name }}</div>
                <div class="text-[10px] text-gray-500">{{ formatFileSize(document.size) }}</div>
                <button
                  type="button"
                  @click="removeSelectedDocument(document.id)"
                  :aria-label="t('chat.removeDocument')"
                  class="absolute top-1 right-1 w-5 h-5 bg-black text-white text-xs rounded-full flex items-center justify-center shadow-sm"
                >
                  x
                </button>
              </div>
            </div>

            <form @submit.prevent="handleSendMessage(inputText)" class="flex items-center" :class="isNativeMobileApp ? 'gap-1.5' : 'gap-2'">
              <input
                ref="fileInputRef"
                type="file"
                accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                multiple
                class="hidden"
                @change="handleImageSelection"
              />
              <input
                ref="cameraInputRef"
                type="file"
                accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                capture="environment"
                class="hidden"
                @change="handleImageSelection"
              />
              <input
                ref="documentInputRef"
                type="file"
                accept=".png,.jpg,.jpeg,.pdf,.doc,.docx,.xls,.xlsx,.txt,image/png,image/jpeg,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain"
                multiple
                class="hidden"
                @change="handleDocumentSelection"
              />

              <div ref="attachmentMenuRef" class="relative flex items-center">
                <button
                  type="button"
                  :disabled="chatStore.isLoading"
                  :aria-label="t('chat.attach')"
                class="flex items-center justify-center rounded-full border border-gray-300 bg-gray-100 leading-none text-gray-900 hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                :class="isNativeMobileApp ? 'h-10 w-10 flex-shrink-0 text-[1.45rem]' : 'h-10 w-10 text-[1.5rem]'"
                  @click="toggleAttachmentMenu"
                >
                  <span :class="isNativeMobileApp ? '-translate-y-[1px]' : '-translate-y-0.5'">+</span>
                </button>
                <div
                  v-if="showAttachmentMenu"
                  class="absolute bottom-12 left-0 min-w-[170px] bg-white border border-gray-200 rounded-xl shadow-lg p-2 z-20"
                >
                  <button
                    type="button"
                    :disabled="chatStore.isLoading"
                    class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    @click="openImagePicker"
                  >
                    {{ t('chat.attachImage') }}
                  </button>
                  <button
                    v-if="isMobilePlatform"
                    type="button"
                    :disabled="chatStore.isLoading"
                    class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    @click="openCamera"
                  >
                    {{ t('chat.openCamera') }}
                  </button>
                  <button
                    type="button"
                    :disabled="chatStore.isLoading"
                    class="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    @click="openDocumentPicker"
                  >
                    {{ t('chat.attachDocument') }}
                  </button>
                </div>
              </div>

              <input
                ref="chatInputRef"
                v-model="inputText"
                type="text"
                :placeholder="chatInputPlaceholder"
                class="min-w-0 flex-1 border-2 border-gray-300 rounded-full focus:border-yellow-400 focus:outline-none disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
                :class="isNativeMobileApp ? 'px-4 py-2.5 text-sm' : 'px-3 py-2 text-sm'"
              />
              <button
                :type="chatStore.isLoading ? 'button' : 'submit'"
                :disabled="!chatStore.isLoading && !canSendMessage"
                class="flex-shrink-0 rounded-full font-medium transition-colors disabled:cursor-not-allowed disabled:bg-gray-300"
                :class="isNativeMobileApp ? 'mr-0.5 bg-black px-3 py-2.5 text-sm text-white hover:bg-gray-800' : 'bg-black px-4 py-2 text-sm text-white hover:bg-gray-800'"
                @click="chatStore.isLoading ? handleStopMessage() : undefined"
              >
                {{ chatStore.isLoading ? t('chat.stop') : t('chat.send') }}
              </button>
            </form>
        </div>
      </div>
    </div>

    <ConfirmModal
      :is-open="showNewChatModal"
      :title="t('chat.newChatTitle')"
      :message="t('chat.newChatMessage')"
      @confirm="confirmNewChat"
      @cancel="showNewChatModal = false"
    />
  </NuxtLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'
import { useAuthStore } from '~/stores/auth'
import { useChatStore } from '~/stores/chat'
import { useAitjeApi, type WebSearchStatus } from '~/composables/useAitjeApi'
import { useChatLogger } from '~/composables/useChatLogger'
import { useRouter } from 'vue-router'
import ChatMessage from '~/components/chat/ChatMessage.vue'
import ConfirmModal from '~/components/modals/ConfirmModal.vue'
import { useI18n } from '~/composables/useI18n'
import LanguageSwitcher from '~/components/common/LanguageSwitcher.vue'

interface PendingImage {
  id: string
  name: string
  dataUrl: string
  base64: string
}

interface PendingDocument {
  id: string
  name: string
  base64: string
  size: number
  contentType?: string | null
}

const allowedDocumentExtensions = new Set(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'])
const allowedDocumentMimeTypes = new Set([
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/plain',
])
const allowedImageExtensions = new Set(['png', 'jpg', 'jpeg'])
const allowedImageMimeTypes = new Set(['image/png', 'image/jpeg'])

const authStore = useAuthStore()
const chatStore = useChatStore()
const { ask } = useAitjeApi()
const { clearLogs } = useChatLogger()
const router = useRouter()
const { t } = useI18n()

const error = ref('')
const showNewChatModal = ref(false)
const inputText = ref('')
const thinkingEnabled = ref(false)
const webSearchEnabled = ref(false)
const webSearchStatus = ref<WebSearchStatus | null>(null)
const shouldResetServerChat = ref(false)
const isMobilePlatform = ref(false)
const isNativeMobileApp = ref(false)
const selectedImages = ref<PendingImage[]>([])
const selectedDocuments = ref<PendingDocument[]>([])
const showAttachmentMenu = ref(false)
const showSettingsMenu = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const cameraInputRef = ref<HTMLInputElement | null>(null)
const documentInputRef = ref<HTMLInputElement | null>(null)
const attachmentMenuRef = ref<HTMLElement | null>(null)
const settingsMenuRef = ref<HTMLElement | null>(null)
const activeAskController = ref<AbortController | null>(null)
const chatInputRef = ref<HTMLInputElement | null>(null)
const stoppedGeneration = ref(false)

const connectedDeviceLabel = computed(() => {
  if (authStore.deviceNumber) {
    return t('status.connectedValue', { device: authStore.deviceNumber })
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname
    const aitjeMatch = hostname.match(/^aitje-(.+?)(?:\.local)?$/i)
    if (aitjeMatch?.[1]) {
      return t('status.connectedValue', { device: aitjeMatch[1] })
    }
    if (hostname) {
      return hostname
    }
  }

  return t('status.connectedUnknown')
})

const canSendMessage = computed(() => {
  return Boolean(inputText.value.trim() || selectedImages.value.length > 0 || selectedDocuments.value.length > 0)
})

const chatInputPlaceholder = computed(() => {
  return stoppedGeneration.value ? t('chat.stopFeedbackPlaceholder') : t('chat.placeholder')
})

const showLoadingIndicator = computed(() => {
  if (!chatStore.isLoading) return false

  const lastMessage = chatStore.messages[chatStore.messages.length - 1]
  if (!lastMessage || lastMessage.role !== 'assistant') return true

  return !lastMessage.content.trim() && !lastMessage.thinking?.trim()
})

const webSearchStatusLabel = computed(() => {
  const status = webSearchStatus.value
  if (!status) return ''

  if (status.type === 'searching') {
    return t('chat.webSearch.searching', { query: status.query })
  }

  if (status.type === 'fetching') {
    let host = status.url
    try {
      host = new URL(status.url).hostname
    } catch (_e) {
      // keep raw url if parse fails
    }
    return `${t('chat.webSearch.fetching', { index: status.index, total: status.total })} ${host}`
  }

  return t('chat.webSearch.summarizing')
})

const readFileAsDataUrl = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('Image read failed'))
    reader.readAsDataURL(file)
  })
}

const readFileAsArrayBuffer = (file: File): Promise<ArrayBuffer> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as ArrayBuffer)
    reader.onerror = () => reject(new Error('Document read failed'))
    reader.readAsArrayBuffer(file)
  })
}

const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
  const bytes = new Uint8Array(buffer)
  const chunkSize = 0x8000
  let binary = ''

  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize)
    binary += String.fromCharCode(...chunk)
  }

  return btoa(binary)
}

const getExtension = (filename: string) => {
  const parts = filename.toLowerCase().split('.')
  return parts.length > 1 ? parts.pop() || '' : ''
}

const isAllowedDocumentFile = (file: File) => {
  const extension = getExtension(file.name)
  return allowedDocumentExtensions.has(extension) || allowedDocumentMimeTypes.has(file.type.toLowerCase())
}

const isAllowedImageFile = (file: File) => {
  const extension = getExtension(file.name)
  const mimeType = file.type.toLowerCase()
  return allowedImageExtensions.has(extension) || allowedImageMimeTypes.has(mimeType)
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

const handleImageSelection = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files

  if (!files || files.length === 0) return

  await addSelectedImages(Array.from(files))
  target.value = ''
}

const addSelectedImages = async (files: File[]) => {
  let foundUnsupportedFile = false

  try {
    for (const file of files) {
      if (!isAllowedImageFile(file)) {
        foundUnsupportedFile = true
        continue
      }

      const dataUrl = await readFileAsDataUrl(file)
      const base64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl

      selectedImages.value.push({
        id: `${Date.now()}-${Math.random()}`,
        name: file.name || 'image',
        dataUrl,
        base64,
      })
    }

    if (foundUnsupportedFile) {
      error.value = t('chat.error.unsupportedImageType')
    }
  } catch (_error) {
    error.value = t('chat.error.imageReadFailed')
  }
}

const handleDocumentSelection = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files

  if (!files || files.length === 0) return

  let foundUnsupportedFile = false

  try {
    for (const file of Array.from(files)) {
      if (isAllowedImageFile(file)) {
        await addSelectedImages([file])
        continue
      }

      if (!isAllowedDocumentFile(file)) {
        foundUnsupportedFile = true
        continue
      }

      const buffer = await readFileAsArrayBuffer(file)
      const base64 = arrayBufferToBase64(buffer)

      selectedDocuments.value.push({
        id: `${Date.now()}-${Math.random()}`,
        name: file.name || 'document',
        base64,
        size: file.size,
        contentType: file.type || null,
      })
    }

    if (foundUnsupportedFile) {
      error.value = t('chat.error.unsupportedDocumentType')
    }
  } catch (_error) {
    error.value = t('chat.error.documentReadFailed')
  } finally {
    target.value = ''
  }
}

const removeSelectedImage = (imageId: string) => {
  selectedImages.value = selectedImages.value.filter(image => image.id !== imageId)
}

const removeSelectedDocument = (documentId: string) => {
  selectedDocuments.value = selectedDocuments.value.filter(document => document.id !== documentId)
}

const clearSelectedImages = () => {
  selectedImages.value = []
}

const clearSelectedDocuments = () => {
  selectedDocuments.value = []
}

const clearSelectedAttachments = () => {
  clearSelectedImages()
  clearSelectedDocuments()
}

const toggleAttachmentMenu = () => {
  showSettingsMenu.value = false
  showAttachmentMenu.value = !showAttachmentMenu.value
}

const toggleSettingsMenu = () => {
  showAttachmentMenu.value = false
  showSettingsMenu.value = !showSettingsMenu.value
}

const openImagePicker = () => {
  showAttachmentMenu.value = false
  fileInputRef.value?.click()
}

const openCamera = () => {
  showAttachmentMenu.value = false
  cameraInputRef.value?.click()
}

const openDocumentPicker = () => {
  showAttachmentMenu.value = false
  documentInputRef.value?.click()
}

const handleDocumentClick = (event: MouseEvent) => {
  const target = event.target as Node | null
  if (!target) return

  if (showAttachmentMenu.value && attachmentMenuRef.value && !attachmentMenuRef.value.contains(target)) {
    showAttachmentMenu.value = false
  }

  if (showSettingsMenu.value && settingsMenuRef.value && !settingsMenuRef.value.contains(target)) {
    showSettingsMenu.value = false
  }
}

const abortActiveRequest = () => {
  activeAskController.value?.abort()
  activeAskController.value = null
}

const handleStopMessage = async () => {
  if (!chatStore.isLoading) return

  stoppedGeneration.value = true
  error.value = ''
  abortActiveRequest()

  await nextTick()
  chatInputRef.value?.focus()
}

const handleSendMessage = async (message: string) => {
  const trimmedMessage = message.trim()
  const messageImages = [...selectedImages.value]
  const messageDocuments = [...selectedDocuments.value]

  if (!trimmedMessage && messageImages.length === 0 && messageDocuments.length === 0) return

  error.value = ''
  stoppedGeneration.value = false
  inputText.value = ''
  webSearchStatus.value = null
  clearSelectedAttachments()

  chatStore.addUserMessage(
    trimmedMessage,
    messageImages.map(image => image.dataUrl),
    messageDocuments.map(document => ({
      filename: document.name,
      contentType: document.contentType,
    })),
  )
  chatStore.setLoading(true)

  const assistantMessageId = chatStore.addAssistantMessage('')
  const askController = new AbortController()
  activeAskController.value = askController
  let latestAssistantMessage = ''
  let latestThinking = ''

  try {
    const response = await ask({
      prompt: trimmedMessage,
      thinking: thinkingEnabled.value,
      webSearch: webSearchEnabled.value,
      maxNewTokens: 128,
      history: chatStore.getRequestHistory,
      images: messageImages.map(image => image.base64),
      documents: messageDocuments.map(document => ({
        filename: document.name,
        data: document.base64,
        content_type: document.contentType,
      })),
      newChat: shouldResetServerChat.value,
      signal: askController.signal,
      onToken: (content) => {
        latestAssistantMessage = content
        if (content) {
          webSearchStatus.value = null
        }
        chatStore.updateMessage(assistantMessageId, { content })
      },
      onThinking: (thinking) => {
        latestThinking = thinking
        chatStore.updateMessage(assistantMessageId, { thinking })
      },
      onSearchStatus: (status) => {
        webSearchStatus.value = status
      },
      onWebSources: (sources) => {
        chatStore.updateMessage(assistantMessageId, { webSources: sources })
      },
    })

    latestAssistantMessage = response.message
    latestThinking = response.thinking
    chatStore.updateMessage(assistantMessageId, {
      content: latestAssistantMessage,
      thinking: latestThinking,
      ...(response.webSources ? { webSources: response.webSources } : {}),
    })
    webSearchStatus.value = null

    const historyQuestion = trimmedMessage || t('chat.attachmentsOnly')
    chatStore.addToPromptHistory(historyQuestion, latestAssistantMessage)
    shouldResetServerChat.value = false
  } catch (e: any) {
    const aitjeError = e as Error & { code?: string }
    const hasStreamedContent = Boolean(latestAssistantMessage.trim() || latestThinking.trim())

    if (!hasStreamedContent) {
      chatStore.removeMessage(assistantMessageId)
    }

    if (aitjeError.code !== 'REQUEST_ABORTED') {
      error.value = aitjeError.message || t('chat.error.general')
    }

    if (aitjeError.code === 'SESSION_EXPIRED') {
      setTimeout(() => {
        router.push('/login')
      }, 2000)
    }
  } finally {
    activeAskController.value = null
    webSearchStatus.value = null
    chatStore.setLoading(false)
  }
}

const openNewChatModal = () => {
  if (chatStore.messages.length > 0) {
    showNewChatModal.value = true
  }
}

const confirmNewChat = () => {
  abortActiveRequest()
  chatStore.clearMessages()
  clearLogs()
  clearSelectedAttachments()
  showAttachmentMenu.value = false
  showSettingsMenu.value = false
  error.value = ''
  stoppedGeneration.value = false
  shouldResetServerChat.value = true
  showNewChatModal.value = false
}

const handleLogout = () => {
  abortActiveRequest()
  authStore.clearAuth()
  chatStore.clearMessages()
  clearLogs()
  clearSelectedAttachments()
  showAttachmentMenu.value = false
  showSettingsMenu.value = false
  stoppedGeneration.value = false
  shouldResetServerChat.value = false
  router.push('/login')
}

const handleChangeDevice = () => {
  abortActiveRequest()
  authStore.clearAll()
  chatStore.clearMessages()
  clearLogs()
  clearSelectedAttachments()
  showAttachmentMenu.value = false
  showSettingsMenu.value = false
  stoppedGeneration.value = false
  shouldResetServerChat.value = false
  router.push({ path: '/setup', query: { changeDevice: '1' } })
}

onMounted(() => {
  const isMobileBrowser = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)
  isNativeMobileApp.value = isMobileBrowser
  isMobilePlatform.value = isMobileBrowser

  authStore.loadFromLocalStorage()

  if (!authStore.isDeviceConfigured) {
    router.push('/setup')
  } else if (!authStore.isAuthenticated) {
    router.push('/login')
  }

  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  abortActiveRequest()
  if (typeof document !== 'undefined') {
    document.removeEventListener('click', handleDocumentClick)
  }
})
</script>
