<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Tab Navigation -->
    <div class="bg-white border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav class="flex space-x-8">
          <NuxtLink
            to="/kennisbank/upload"
            class="py-4 px-1 border-b-2 font-medium text-sm border-blue-500 text-blue-600"
          >
            Uploaden
          </NuxtLink>
          <NuxtLink
            to="/kennisbank/library"
            class="py-4 px-1 border-b-2 font-medium text-sm border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          >
            Bibliotheek
          </NuxtLink>
          <NuxtLink
            to="/kennisbank/relations"
            class="py-4 px-1 border-b-2 font-medium text-sm border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          >
            Relaties
          </NuxtLink>
          <NuxtLink
            to="/kennisbank/priorities"
            class="py-4 px-1 border-b-2 font-medium text-sm border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          >
            Prioriteiten
          </NuxtLink>
          <NuxtLink
            to="/kennisbank/insights"
            class="py-4 px-1 border-b-2 font-medium text-sm border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          >
            Inzicht
          </NuxtLink>
        </nav>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 class="text-2xl font-bold mb-6">Document Uploaden</h1>

      <!-- Upload Form -->
      <div class="bg-white rounded-lg shadow p-6 space-y-6">
        <!-- File Input -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Bestand</label>
          <div
            class="border-2 border-dashed rounded-lg p-8 text-center"
            :class="isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInput"
              type="file"
              class="hidden"
              accept=".pdf,.docx,.doc,.csv,.xml,.txt,.md"
              @change="handleFileSelect"
            >

            <div v-if="!selectedFile">
              <p class="text-gray-600 mb-2">Sleep een bestand hierheen of</p>
              <button
                type="button"
                class="text-blue-600 hover:text-blue-500 font-medium"
                @click="($refs.fileInput as HTMLInputElement).click()"
              >
                kies een bestand
              </button>
              <p class="text-sm text-gray-500 mt-2">PDF, DOCX, CSV, XML, TXT (max 50MB)</p>
            </div>

            <div v-else class="flex items-center justify-center space-x-4">
              <span class="text-2xl">{{ getFileIcon(selectedFile.type) }}</span>
              <div class="text-left">
                <p class="font-medium">{{ selectedFile.name }}</p>
                <p class="text-sm text-gray-500">{{ formatFileSize(selectedFile.size) }}</p>
              </div>
              <button
                type="button"
                class="text-red-600 hover:text-red-500"
                @click="selectedFile = null"
              >
                Verwijderen
              </button>
            </div>
          </div>
        </div>

        <!-- Metadata -->
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700">Titel</label>
            <input
              v-model="metadata.title"
              type="text"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              :placeholder="selectedFile?.name.replace(/\.[^/.]+$/, '') || 'Document titel'"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700">Categorie</label>
            <input
              v-model="metadata.category"
              type="text"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="bijv. Handleidingen"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700">Versie</label>
            <input
              v-model="metadata.version_tag"
              type="text"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="bijv. v1.0"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700">Publicatiedatum</label>
            <input
              v-model="metadata.content_date"
              type="date"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
            <p class="text-xs text-gray-500 mt-1">Gebruik deze datum in de JSON-LD export (default: vandaag).</p>
          </div>

          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700">Beschrijving</label>
            <textarea
              v-model="metadata.description"
              rows="2"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="Korte beschrijving..."
            />
          </div>
        </div>

        <!-- Status -->
        <div v-if="status" class="p-4 rounded-lg" :class="status.type === 'error' ? 'bg-red-50 text-red-700' : status.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-blue-50 text-blue-700'">
          {{ status.message }}
        </div>

        <!-- Submit -->
        <div class="flex justify-end">
          <button
            type="button"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            :disabled="!selectedFile || isUploading"
            @click="uploadAndProcess"
          >
            {{ isUploading ? 'Bezig...' : 'Uploaden en verwerken' }}
          </button>
        </div>
      </div>

      <!-- Recent uploads -->
      <div v-if="recentUploads.length > 0" class="mt-8 bg-white rounded-lg shadow">
        <div class="px-6 py-4 border-b">
          <h2 class="text-lg font-medium">Recente uploads</h2>
        </div>
        <ul class="divide-y">
          <li v-for="doc in recentUploads" :key="doc.id" class="px-6 py-4 flex items-center justify-between">
            <div>
              <p class="font-medium">{{ doc.title || doc.original_filename }}</p>
              <p class="text-sm text-gray-500">{{ doc.category || 'Geen categorie' }}</p>
            </div>
            <div class="flex items-center space-x-3">
              <span
                class="px-2 py-1 text-xs rounded-full"
                :class="getStatusClass(doc.status)"
              >
                {{ doc.status }}
              </span>
              <button
                class="text-red-600 hover:text-red-800"
                @click="deleteDocument(doc.id)"
                title="Verwijderen"
              >
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
});

const authStore = useAuthStore();
const config = useRuntimeConfig();

type UploadMetadata = {
  title: string;
  category: string;
  version_tag: string;
  description: string;
  content_date: string;
};

function defaultMetadata(): UploadMetadata {
  return {
    title: '',
    category: '',
    version_tag: '',
    description: '',
    content_date: new Date().toISOString().slice(0, 10),
  };
}

const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const isDragging = ref(false);
const isUploading = ref(false);
const status = ref<{ type: 'info' | 'error' | 'success'; message: string } | null>(null);
const recentUploads = ref<any[]>([]);

const metadata = ref<UploadMetadata>(defaultMetadata());

onMounted(async () => {
  await loadRecentUploads();
});

async function loadRecentUploads() {
  try {
    const baseUrl = config.public.apiBaseUrl as string;
    const response = await fetch(`${baseUrl}/documents`, {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
        Accept: 'application/json',
      },
    });
    const data = await response.json();
    recentUploads.value = data.documents?.slice(0, 5) || [];
  } catch (e) {
    console.error('Failed to load recent uploads:', e);
  }
}

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files?.length) {
    selectedFile.value = input.files[0];
    if (!metadata.value.title) {
      metadata.value.title = selectedFile.value.name.replace(/\.[^/.]+$/, '');
    }
  }
}

function handleDrop(event: DragEvent) {
  isDragging.value = false;
  if (event.dataTransfer?.files.length) {
    selectedFile.value = event.dataTransfer.files[0];
    if (!metadata.value.title) {
      metadata.value.title = selectedFile.value.name.replace(/\.[^/.]+$/, '');
    }
  }
}

async function uploadAndProcess() {
  if (!selectedFile.value) return;

  isUploading.value = true;
  status.value = { type: 'info', message: 'Uploaden...' };

  try {
    const baseUrl = config.public.apiBaseUrl as string;

    // Step 1: Upload
    const formData = new FormData();
    formData.append('file', selectedFile.value);
    if (metadata.value.title) formData.append('title', metadata.value.title);
    if (metadata.value.category) formData.append('category', metadata.value.category);
    if (metadata.value.version_tag) formData.append('version_tag', metadata.value.version_tag);
    if (metadata.value.description) formData.append('description', metadata.value.description);
    if (metadata.value.content_date) formData.append('content_date', metadata.value.content_date);

    const uploadResponse = await fetch(`${baseUrl}/documents`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authStore.token}`,
        Accept: 'application/json',
      },
      body: formData,
    });

    if (!uploadResponse.ok) {
      const error = await uploadResponse.json();
      throw new Error(error.message || 'Upload mislukt');
    }

    const uploadData = await uploadResponse.json();
    const document = uploadData.document;

    status.value = { type: 'info', message: 'Verwerken...' };

    // Step 2: Process
    const processResponse = await fetch(`${baseUrl}/documents/${document.id}/process`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authStore.token}`,
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
    });

    if (!processResponse.ok) {
      const error = await processResponse.json();
      throw new Error(error.message || 'Verwerking mislukt');
    }

    status.value = { type: 'success', message: 'Document succesvol geupload en verwerkt!' };

    // Reset form
    selectedFile.value = null;
    metadata.value = defaultMetadata();

    // Refresh recent uploads
    await loadRecentUploads();

  } catch (e: any) {
    status.value = { type: 'error', message: e.message || 'Er is een fout opgetreden' };
  } finally {
    isUploading.value = false;
  }
}

function getFileIcon(type: string) {
  if (type.includes('pdf')) return '📄';
  if (type.includes('word') || type.includes('document')) return '📝';
  if (type.includes('csv') || type.includes('excel')) return '📊';
  if (type.includes('xml')) return '📋';
  return '📄';
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function getStatusClass(status: string) {
  switch (status) {
    case 'formatted':
      return 'bg-green-100 text-green-800';
    case 'processing':
      return 'bg-blue-100 text-blue-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

async function deleteDocument(id: number) {
  if (!confirm('Weet je zeker dat je dit document wilt verwijderen?')) return;

  try {
    const baseUrl = config.public.apiBaseUrl as string;
    const response = await fetch(`${baseUrl}/documents/${id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${authStore.token}`,
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Verwijderen mislukt');
    }

    await loadRecentUploads();
  } catch (e: any) {
    alert(e.message || 'Er is een fout opgetreden');
  }
}
</script>
