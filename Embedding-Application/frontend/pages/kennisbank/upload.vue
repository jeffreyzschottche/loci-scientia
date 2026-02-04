<template>
  <KennisbankTabLayout>
    <div class="max-w-3xl w-full mx-auto">
      <h1 class="text-2xl font-bold mb-6 text-loci-black">
        {{ translate('Document Uploaden', 'Upload Document') }}
      </h1>

      <!-- Upload Form -->
      <div class="bg-loci-white rounded-loci-lg border border-loci-gray-100 p-6 space-y-6">
        <!-- File Input -->
        <div>
          <label class="block text-sm font-medium text-loci-black mb-2">
            {{ translate('Bestand', 'File') }}
          </label>
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
              <p class="text-loci-gray-500 mb-2">
                {{ translate('Sleep een bestand hierheen of', 'Drag a file here or') }}
              </p>
              <button
                type="button"
                class="text-loci-black font-semibold hover:text-loci-yellow-hover"
                @click="($refs.fileInput as HTMLInputElement).click()"
              >
                {{ translate('kies een bestand', 'choose a file') }}
              </button>
              <p class="text-sm text-loci-gray-400 mt-2">
                {{ translate('PDF, DOCX, CSV, XML, TXT (max 50MB)', 'PDF, DOCX, CSV, XML, TXT (max 50MB)') }}
              </p>
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
                {{ translate('Verwijderen', 'Remove') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Metadata -->
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-loci-black">
              {{ translate('Titel', 'Title') }}
            </label>
            <input
              v-model="metadata.title"
              type="text"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              :placeholder="selectedFile?.name.replace(/\.[^/.]+$/, '') || translate('Document titel', 'Document title')"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-loci-black">
              {{ translate('Categorie', 'Category') }}
            </label>

            <div class="mt-1">
              <!-- Existing category dropdown with search -->
              <div v-if="categoryMode === 'existing'" class="relative" data-category-dropdown>
                <input
                  v-model="categorySearch"
                  type="text"
                  class="block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
                  :placeholder="translate('Zoek of selecteer categorie...', 'Search or select category...')"
                  @focus="showCategoryDropdown = true"
                  @input="showCategoryDropdown = true"
                >

                <!-- Dropdown -->
                <div
                  v-if="showCategoryDropdown && filteredCategories.length > 0"
                  class="absolute z-10 mt-1 w-full bg-loci-white border border-loci-gray-200 rounded-loci shadow-lg max-h-48 overflow-auto"
                >
                  <button
                    v-for="cat in filteredCategories"
                    :key="cat"
                    type="button"
                    class="w-full text-left px-4 py-2 hover:bg-loci-yellow/20 text-loci-black transition-colors"
                    :class="{ 'bg-loci-yellow/10': metadata.category === cat }"
                    @click="selectCategory(cat)"
                  >
                    {{ cat }}
                  </button>
                </div>

                <!-- Selected category badge -->
                <div v-if="metadata.category && categoryMode === 'existing'" class="mt-2">
                  <span class="inline-flex items-center gap-2 px-3 py-1 bg-loci-yellow/20 rounded-full text-sm text-loci-black">
                    {{ metadata.category }}
                    <button type="button" class="hover:text-red-500" @click="clearCategory">×</button>
                  </span>
                </div>
              </div>

              <!-- New category input -->
              <input
                v-else
                v-model="metadata.category"
                type="text"
                class="block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
                :placeholder="translate('Nieuwe categorie naam...', 'New category name...')"
              >
            </div>

            <!-- Toggle between existing and new (below input) -->
            <div class="flex gap-4 mt-3">
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="categoryMode"
                  type="radio"
                  value="existing"
                  class="text-loci-yellow focus:ring-loci-yellow"
                >
                <span class="text-sm text-loci-black">{{ translate('Bestaande categorie', 'Existing category') }}</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer">
                <input
                  v-model="categoryMode"
                  type="radio"
                  value="new"
                  class="text-loci-yellow focus:ring-loci-yellow"
                >
                <span class="text-sm text-loci-black">{{ translate('Nieuwe categorie', 'New category') }}</span>
              </label>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-loci-black">
              {{ translate('Versie', 'Version') }}
            </label>
            <input
              v-model="metadata.version_tag"
              type="text"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              :placeholder="translate('bijv. v1.0', 'e.g. v1.0')"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-loci-black">
              {{ translate('Publicatiedatum', 'Publication date') }}
            </label>
            <input
              v-model="metadata.content_date"
              type="date"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            >
            <p class="text-xs text-loci-gray-500 mt-1">
              {{ translate('Gebruik deze datum in de JSON-LD export (default: vandaag).', 'Use this date in the JSON-LD export (default: today).') }}
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-loci-black">
              {{ translate('Taal', 'Language') }}
            </label>
            <select
              v-model="metadata.language"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            >
              <option v-for="lang in languageOptions" :key="lang.code" :value="lang.code">
                {{ lang.flag }} {{ lang.label }}
              </option>
            </select>
          </div>

          <div class="col-span-2">
            <label class="block text-sm font-medium text-loci-black">
              {{ translate('Beschrijving', 'Description') }}
            </label>
            <textarea
              v-model="metadata.description"
              rows="2"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              :placeholder="translate('Korte beschrijving...', 'Short description...')"
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
            {{ isUploading ? translate('Bezig...', 'Processing...') : translate('Uploaden en verwerken', 'Upload and process') }}
          </button>
        </div>
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
const api = useApi();
const { translate } = useTranslations();

// Category selection
const categoryMode = ref<'existing' | 'new'>('existing');
const categorySearch = ref('');
const showCategoryDropdown = ref(false);
const existingCategories = ref<string[]>([]);

const filteredCategories = computed(() => {
  if (!categorySearch.value.trim()) {
    return existingCategories.value;
  }
  const query = categorySearch.value.toLowerCase();
  return existingCategories.value.filter(cat => cat.toLowerCase().includes(query));
});

function selectCategory(cat: string) {
  metadata.value.category = cat;
  categorySearch.value = cat;
  showCategoryDropdown.value = false;
}

function clearCategory() {
  metadata.value.category = '';
  categorySearch.value = '';
}

// Close dropdown when clicking outside
onMounted(async () => {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    if (!target.closest('[data-category-dropdown]')) {
      showCategoryDropdown.value = false;
    }
  });

  // Load existing categories
  try {
    const response = await api.get<{ tree: any[] }>('/library/tree');
    const categories = new Set<string>();
    for (const doc of response.tree) {
      if (doc.category) {
        categories.add(doc.category);
      }
    }
    existingCategories.value = Array.from(categories).sort();
  } catch (e) {
    console.error('Failed to load categories:', e);
  }
});

type UploadMetadata = {
  title: string;
  category: string;
  version_tag: string;
  description: string;
  content_date: string;
  language: string;
};

const languageOptions = [
  { code: 'nl', label: 'Nederlands', flag: '\u{1F1F3}\u{1F1F1}' },
  { code: 'en', label: 'English', flag: '\u{1F1EC}\u{1F1E7}' },
  { code: 'de', label: 'Deutsch', flag: '\u{1F1E9}\u{1F1EA}' },
  { code: 'es', label: 'Espanol', flag: '\u{1F1EA}\u{1F1F8}' },
  { code: 'it', label: 'Italiano', flag: '\u{1F1EE}\u{1F1F9}' },
  { code: 'pl', label: 'Polski', flag: '\u{1F1F5}\u{1F1F1}' },
  { code: 'sv', label: 'Svenska', flag: '\u{1F1F8}\u{1F1EA}' },
  { code: 'da', label: 'Dansk', flag: '\u{1F1E9}\u{1F1F0}' },
  { code: 'fi', label: 'Suomi', flag: '\u{1F1EB}\u{1F1EE}' },
];

function defaultMetadata(): UploadMetadata {
  return {
    title: '',
    category: '',
    version_tag: '',
    description: '',
    content_date: new Date().toISOString().slice(0, 10),
    language: 'nl',
  };
}

const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const isDragging = ref(false);
const isUploading = ref(false);
const status = ref<{ type: 'info' | 'error' | 'success'; message: string } | null>(null);

const metadata = ref<UploadMetadata>(defaultMetadata());

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
  status.value = { type: 'info', message: translate('Uploaden...', 'Uploading...') };

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
    if (metadata.value.language) formData.append('language', metadata.value.language);

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
      throw new Error(error.message || translate('Upload mislukt', 'Upload failed'));
    }

    const uploadData = await uploadResponse.json();
    const document = uploadData.document;

    status.value = { type: 'info', message: translate('Verwerken...', 'Processing...') };

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
      throw new Error(error.message || translate('Verwerking mislukt', 'Processing failed'));
    }

    status.value = { type: 'success', message: translate('Document succesvol geüpload en verwerkt!', 'Document uploaded and processed successfully!') };

    // Reset form
    selectedFile.value = null;
    metadata.value = defaultMetadata();
    categorySearch.value = '';
    categoryMode.value = 'existing';

  } catch (e: any) {
    status.value = { type: 'error', message: e.message || translate('Er is een fout opgetreden', 'Something went wrong') };
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
</script>
