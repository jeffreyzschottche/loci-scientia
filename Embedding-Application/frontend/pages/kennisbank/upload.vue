<template>
  <KennisbankTabLayout>
    <div class="max-w-3xl w-full mx-auto">
      <h1 class="text-2xl font-bold mb-6 text-loci-black">Document Uploaden</h1>

      <!-- Upload Form -->
      <div class="bg-loci-white rounded-loci-lg border border-loci-gray-100 p-6 space-y-6">
        <!-- File Input -->
        <div>
          <label class="block text-sm font-medium text-loci-black mb-2">Bestand</label>
          <div
            class="border-2 border-dashed rounded-loci-lg p-8 text-center transition-all"
            :class="isDragging ? 'border-loci-yellow bg-loci-yellow/10' : 'border-loci-gray-300'"
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
              <p class="text-loci-gray-500 mb-2">Sleep een bestand hierheen of</p>
              <button
                type="button"
                class="text-loci-black font-semibold hover:text-loci-yellow-hover"
                @click="($refs.fileInput as HTMLInputElement).click()"
              >
                kies een bestand
              </button>
              <p class="text-sm text-loci-gray-400 mt-2">PDF, DOCX, CSV, XML, TXT (max 50MB)</p>
            </div>

            <div v-else class="flex items-center justify-center space-x-4">
              <span class="text-2xl">{{ getFileIcon(selectedFile.type) }}</span>
              <div class="text-left">
                <p class="font-medium text-loci-black">{{ selectedFile.name }}</p>
                <p class="text-sm text-loci-gray-500">{{ formatFileSize(selectedFile.size) }}</p>
              </div>
              <button
                type="button"
                class="text-red-500 hover:text-red-700"
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
            <label class="block text-sm font-medium text-loci-black">Titel</label>
            <input
              v-model="metadata.title"
              type="text"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              :placeholder="selectedFile?.name.replace(/\.[^/.]+$/, '') || 'Document titel'"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-loci-black">Categorie</label>
            <input
              v-model="metadata.category"
              type="text"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              placeholder="bijv. Handleidingen"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-loci-black">Versie</label>
            <input
              v-model="metadata.version_tag"
              type="text"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              placeholder="bijv. v1.0"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-loci-black">Publicatiedatum</label>
            <input
              v-model="metadata.content_date"
              type="date"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            >
            <p class="text-xs text-loci-gray-500 mt-1">Gebruik deze datum in de JSON-LD export (default: vandaag).</p>
          </div>

          <div class="col-span-2">
            <label class="block text-sm font-medium text-loci-black">Beschrijving</label>
            <textarea
              v-model="metadata.description"
              rows="2"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              placeholder="Korte beschrijving..."
            />
          </div>
        </div>

        <!-- Status -->
        <div v-if="status" class="p-4 rounded-loci border" :class="status.type === 'error' ? 'bg-red-50 border-red-200 text-red-700' : status.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-loci-yellow/10 border-loci-yellow text-loci-black'">
          {{ status.message }}
        </div>

        <!-- Submit -->
        <div class="flex justify-end">
          <button
            type="button"
            class="px-6 py-3 bg-loci-yellow text-loci-black-deep rounded-loci-full font-semibold hover:bg-loci-yellow-hover transition-all disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
            :disabled="!selectedFile || isUploading"
            @click="uploadAndProcess"
          >
            {{ isUploading ? 'Bezig...' : 'Uploaden en verwerken' }}
          </button>
        </div>
      </div>

      <!-- Recent uploads -->
      <div v-if="recentUploads.length > 0" class="mt-8 bg-loci-white rounded-loci-lg border border-loci-gray-100">
        <div class="px-6 py-4 border-b border-loci-gray-100">
          <h2 class="text-lg font-medium text-loci-black">Recente uploads</h2>
        </div>
        <ul class="divide-y divide-loci-gray-100">
          <li v-for="doc in recentUploads" :key="doc.id" class="px-6 py-4 flex items-center justify-between">
            <div>
              <p class="font-medium text-loci-black">{{ doc.title || doc.original_filename }}</p>
              <p class="text-sm text-loci-gray-500">{{ doc.category || 'Geen categorie' }}</p>
            </div>
            <div class="flex items-center space-x-3">
              <span
                class="px-2 py-1 text-xs rounded-full font-semibold"
                :class="getStatusClass(doc.status)"
              >
                {{ doc.status }}
              </span>
              <button
                class="text-red-500 hover:text-red-700"
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
  </KennisbankTabLayout>
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
