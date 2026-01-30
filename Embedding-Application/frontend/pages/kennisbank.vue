<template>
  <div class="mx-auto max-w-7xl px-4 py-12 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold">{{ t('kennisbank') }}</h1>
      <button
        @click="pushToGit"
        :disabled="pushing || !hasEmbeddedDocuments"
        class="rounded-lg bg-green-600 px-4 py-2 text-white font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ pushing ? t('pushing') : t('push_to_git') }}
      </button>
    </div>

    <!-- Upload Section -->
    <div class="rounded-lg bg-white p-6 shadow">
      <h2 class="mb-4 text-xl font-semibold">{{ t('upload_document') }}</h2>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <!-- PDF - Active -->
        <label
          class="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-blue-300 bg-blue-50 p-6 cursor-pointer hover:border-blue-500 hover:bg-blue-100 transition-colors"
        >
          <svg class="h-8 w-8 text-blue-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          <span class="text-sm font-medium text-blue-700">PDF</span>
          <span class="text-xs text-blue-500 mt-1">{{ t('click_to_upload') }}</span>
          <input
            type="file"
            accept=".pdf"
            class="hidden"
            @change="handleFileUpload"
            :disabled="uploading"
          />
        </label>

        <!-- DOCX - Disabled -->
        <div class="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 p-6 opacity-50 cursor-not-allowed">
          <svg class="h-8 w-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span class="text-sm font-medium text-gray-400">DOCX</span>
          <span class="text-xs text-gray-400 mt-1">{{ t('coming_soon') }}</span>
        </div>

        <!-- TXT - Disabled -->
        <div class="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 p-6 opacity-50 cursor-not-allowed">
          <svg class="h-8 w-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
          </svg>
          <span class="text-sm font-medium text-gray-400">TXT</span>
          <span class="text-xs text-gray-400 mt-1">{{ t('coming_soon') }}</span>
        </div>

        <!-- CSV - Disabled -->
        <div class="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 p-6 opacity-50 cursor-not-allowed">
          <svg class="h-8 w-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18M9 4v16M15 4v16" />
          </svg>
          <span class="text-sm font-medium text-gray-400">CSV</span>
          <span class="text-xs text-gray-400 mt-1">{{ t('coming_soon') }}</span>
        </div>
      </div>

      <!-- Upload progress -->
      <div v-if="uploading" class="mt-4 flex items-center text-sm text-blue-600">
        <svg class="animate-spin h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ t('uploading') }}
      </div>
    </div>

    <!-- Documents List -->
    <div class="rounded-lg bg-white p-6 shadow">
      <h2 class="mb-4 text-xl font-semibold">{{ t('documents') }}</h2>

      <div v-if="documents.length === 0" class="text-center py-8 text-gray-500">
        {{ t('no_documents_yet') }}
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="border-b text-gray-500 uppercase text-xs">
            <tr>
              <th class="pb-3 pr-4">{{ t('document') }}</th>
              <th class="pb-3 pr-4">{{ t('size') }}</th>
              <th class="pb-3 pr-4">{{ t('status') }}</th>
              <th class="pb-3 pr-4">{{ t('chunks') }}</th>
              <th class="pb-3 pr-4">{{ t('date') }}</th>
              <th class="pb-3">{{ t('actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="doc in documents" :key="doc.id" class="hover:bg-gray-50">
              <td class="py-3 pr-4 font-medium">{{ doc.original_filename }}</td>
              <td class="py-3 pr-4 text-gray-600">{{ formatSize(doc.file_size) }}</td>
              <td class="py-3 pr-4">
                <span :class="statusClass(doc.status)" class="rounded-full px-2 py-1 text-xs font-medium">
                  {{ statusLabel(doc.status) }}
                </span>
              </td>
              <td class="py-3 pr-4 text-gray-600">{{ doc.chunk_count || '-' }}</td>
              <td class="py-3 pr-4 text-gray-600">{{ formatDate(doc.created_at) }}</td>
              <td class="py-3 space-x-2">
                <button
                  v-if="doc.status === 'uploaded'"
                  @click="processDocument(doc.id)"
                  :disabled="processing === doc.id"
                  class="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {{ processing === doc.id ? t('processing') : t('embed') }}
                </button>
                <button
                  @click="deleteDocument(doc.id)"
                  class="rounded bg-red-100 px-3 py-1 text-xs text-red-700 hover:bg-red-200"
                >
                  {{ t('delete') }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Git Configuration -->
    <div class="rounded-lg bg-white p-6 shadow">
      <h2 class="mb-4 text-xl font-semibold">{{ t('git_configuration') }}</h2>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Repository URL</label>
          <input
            v-model="gitConfig.repo_url"
            type="text"
            placeholder="https://github.com/user/repo.git"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Branch</label>
          <input
            v-model="gitConfig.branch"
            type="text"
            placeholder="main"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Access Token</label>
          <input
            v-model="gitConfig.access_token"
            type="password"
            placeholder="ghp_xxxxxxxxxxxxx"
            class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>

      <div class="mt-4 flex items-center justify-between">
        <button
          @click="saveGitConfig"
          :disabled="savingConfig"
          class="rounded-lg bg-gray-800 px-4 py-2 text-sm text-white hover:bg-gray-900 disabled:opacity-50"
        >
          {{ savingConfig ? t('saving') : t('save_configuration') }}
        </button>
        <span v-if="gitLastPushed" class="text-sm text-gray-500">
          {{ t('last_pushed') }} {{ gitLastPushed }}
        </span>
      </div>
    </div>

    <!-- Status Messages -->
    <div v-if="message" :class="messageIsError ? 'bg-red-50 text-red-700 border-red-200' : 'bg-green-50 text-green-700 border-green-200'" class="rounded-lg border p-4 text-sm">
      {{ message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Document, DocumentsResponse, DocumentResponse, GitConfigResponse } from '~/types/Document'
import type { MessageResponse } from '~/types/ApiResponse'

definePageMeta({
  middleware: 'auth',
})

const authStore = useAuthStore()
const api = useApi()
const { t } = useTranslations()

const documents = ref<Document[]>([])
const uploading = ref(false)
const processing = ref<number | null>(null)
const pushing = ref(false)
const savingConfig = ref(false)
const message = ref('')
const messageIsError = ref(false)
const gitLastPushed = ref<string | null>(null)

const gitConfig = ref({
  repo_url: '',
  branch: 'main',
  access_token: '',
})

const hasEmbeddedDocuments = computed(() =>
  documents.value.some(d => d.status === 'embedded')
)

// Load documents and git config on mount
onMounted(async () => {
  await Promise.all([loadDocuments(), loadGitConfig()])
})

async function loadDocuments() {
  try {
    const res = await api.get<DocumentsResponse>('/documents')
    documents.value = res.documents
  } catch (e: any) {
    showMessage(e.message || t('error_loading_documents'), true)
  }
}

async function loadGitConfig() {
  try {
    const res = await api.get<GitConfigResponse>('/kennisbank/git-config')
    if (res.config) {
      gitConfig.value.repo_url = res.config.repo_url
      gitConfig.value.branch = res.config.branch
      gitLastPushed.value = res.config.last_pushed_at
        ? new Date(res.config.last_pushed_at).toLocaleString('nl-NL')
        : null
    }
  } catch {}
}

async function handleFileUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploading.value = true
  message.value = ''

  try {
    const formData = new FormData()
    formData.append('file', file)

    const config = useRuntimeConfig()
    const baseUrl = config.public.apiBaseUrl as string

    const response = await fetch(`${baseUrl}/documents`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${authStore.token}`,
      },
      body: formData,
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.message || t('upload_failed'))
    }

    documents.value.unshift(data.document)
    showMessage(`"${file.name}" ${t('uploaded')}`)
  } catch (e: any) {
    showMessage(e.message || t('upload_failed'), true)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function processDocument(id: number) {
  processing.value = id
  message.value = ''

  try {
    const res = await api.post<DocumentResponse>(`/documents/${id}/process`)
    const idx = documents.value.findIndex(d => d.id === id)
    if (idx !== -1 && res.document) {
      documents.value[idx] = res.document
    }
    showMessage(res.message || t('document_embedded'))
  } catch (e: any) {
    showMessage(e.message || t('embedding_failed'), true)
    await loadDocuments()
  } finally {
    processing.value = null
  }
}

async function deleteDocument(id: number) {
  if (!confirm(t('confirm_delete'))) return

  try {
    await api.delete<MessageResponse>(`/documents/${id}`)
    documents.value = documents.value.filter(d => d.id !== id)
    showMessage(t('document_deleted'))
  } catch (e: any) {
    showMessage(e.message || t('delete_failed'), true)
  }
}

async function saveGitConfig() {
  savingConfig.value = true
  message.value = ''

  try {
    await api.post<MessageResponse>('/kennisbank/git-config', gitConfig.value)
    showMessage(t('git_config_saved'))
  } catch (e: any) {
    showMessage(e.message || t('save_failed'), true)
  } finally {
    savingConfig.value = false
  }
}

async function pushToGit() {
  pushing.value = true
  message.value = ''

  try {
    const res = await api.post<{ message: string; last_pushed_at: string }>('/kennisbank/push')
    showMessage(res.message)
    if (res.last_pushed_at) {
      gitLastPushed.value = new Date(res.last_pushed_at).toLocaleString('nl-NL')
    }
  } catch (e: any) {
    showMessage(e.message || t('push_failed'), true)
  } finally {
    pushing.value = false
  }
}

function showMessage(msg: string, isError = false) {
  message.value = msg
  messageIsError.value = isError
  setTimeout(() => { message.value = '' }, 5000)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('nl-NL')
}

function statusClass(status: string): string {
  const classes: Record<string, string> = {
    uploaded: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    embedded: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }
  return classes[status] || 'bg-gray-100 text-gray-800'
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    uploaded: t('status_uploaded'),
    processing: t('status_processing'),
    embedded: t('status_embedded'),
    failed: t('status_failed'),
  }
  return labels[status] || status
}
</script>
