<template>
  <KennisbankTabLayout>
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="flex gap-4" style="height: calc(100vh - 200px);">
        <!-- Left Panel: Categories & Documents -->
        <div class="w-80 bg-loci-white rounded-loci-lg border border-loci-gray-100 flex flex-col">
          <div class="p-4 border-b border-loci-gray-100">
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="translate('Zoeken...', 'Search...')"
              class="w-full px-4 py-2 border border-loci-gray-300 rounded-loci bg-loci-cream text-loci-black focus:border-loci-yellow focus:outline-none"
            >
          </div>

          <div class="flex-1 overflow-auto p-2">
            <div v-if="isLoading" class="text-center py-8">
              <p class="text-loci-gray-500">{{ translate('Laden...', 'Loading...') }}</p>
            </div>

            <div v-else-if="error" class="text-center py-8">
              <p class="text-red-500">{{ error }}</p>
            </div>

            <div v-else-if="tree.length === 0" class="text-center py-8 text-loci-gray-500">
              <p>{{ translate('Geen documenten gevonden', 'No documents found') }}</p>
              <NuxtLink to="/kennisbank/upload" class="text-loci-black font-semibold hover:text-loci-yellow-hover mt-2 block">
                {{ translate('Upload je eerste document', 'Upload your first document') }}
              </NuxtLink>
            </div>

            <div v-else class="space-y-1">
              <!-- Categories with documents -->
              <div v-for="category in filteredCategories" :key="category.name">
                <!-- Category header -->
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-loci hover:bg-loci-yellow/10 transition-all text-left"
                  @click="toggleCategory(category.name)"
                >
                  <svg
                    class="h-4 w-4 text-loci-gray-500 transition-transform duration-200"
                    :class="{ 'rotate-90': expandedCategories.has(category.name) }"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                  <span class="font-medium text-loci-black flex-1">{{ category.name }}</span>
                  <span
                    class="text-xs px-2 py-0.5 rounded-full transition-colors"
                    :class="expandedCategories.has(category.name) ? 'bg-loci-yellow text-loci-black-deep' : 'bg-loci-gray-100 text-loci-gray-400'"
                  >
                    {{ category.documents.length }}
                  </span>
                </button>

                <!-- Documents in category -->
                <div
                  v-if="expandedCategories.has(category.name)"
                  class="ml-4 border-l-2 border-loci-gray-100 pl-2 space-y-1 mt-1"
                >
                  <div
                    v-for="doc in category.documents"
                    :key="doc.id"
                    class="flex items-center gap-2 px-3 py-2 rounded-loci cursor-pointer transition-all"
                    :class="selectedId === doc.id ? 'bg-loci-yellow/20' : 'hover:bg-loci-yellow/10'"
                    @click="selectDocument(doc)"
                  >
                    <svg class="h-4 w-4 text-loci-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span class="flex-1 truncate text-sm text-loci-black" :title="doc.title">{{ doc.title }}</span>
                    <button
                      type="button"
                      class="text-red-400 hover:text-red-600 disabled:opacity-50 flex-shrink-0"
                      :title="translate('Verwijderen', 'Delete')"
                      :disabled="deletingId === doc.id"
                      @click.stop="requestDelete(doc)"
                    >
                      <svg
                        v-if="deletingId !== doc.id"
                        class="h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      <svg
                        v-else
                        class="h-4 w-4 animate-spin"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Panel: Preview -->
        <div class="flex-1 bg-loci-white rounded-loci-lg border border-loci-gray-100 flex flex-col">
          <div v-if="!selectedDocument" class="flex-1 flex items-center justify-center text-loci-gray-500">
            <p>{{ translate('Selecteer een document', 'Select a document') }}</p>
          </div>

          <template v-else>
            <div class="p-4 border-b border-loci-gray-100">
              <h2 class="text-lg font-medium text-loci-black">{{ selectedDocument.title }}</h2>
              <p class="text-sm text-loci-gray-500">{{ selectedDocument.category || translate('Geen categorie', 'No category') }}</p>
            </div>

            <div class="flex-1 overflow-auto p-4">
              <!-- Sections -->
              <div v-if="selectedDocument.sections" class="space-y-6">
                <div v-for="section in selectedDocument.sections" :key="section.id">
                  <h3 class="font-semibold border-b border-loci-gray-100 pb-2 text-loci-black">{{ section.title }}</h3>
                  <p class="mt-2 whitespace-pre-wrap text-loci-gray-500">{{ section.text }}</p>
                </div>
              </div>
              <div v-else class="text-loci-gray-500">
                <p>{{ translate('Geen secties gevonden', 'No sections found') }}</p>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </KennisbankTabLayout>
  <teleport to="body">
    <div
      v-if="deleteCandidate"
      class="fixed inset-0 z-50 flex items-center justify-center px-4"
    >
      <div
        class="absolute inset-0 bg-loci-black/60"
        aria-hidden="true"
        @click="cancelDelete"
      />

      <div
        class="relative w-full max-w-md bg-loci-white border border-loci-gray-100 rounded-loci-lg shadow-2xl p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-confirm-title"
        aria-describedby="delete-confirm-message"
        tabindex="-1"
      >
        <div class="flex items-start gap-4">
          <div class="flex h-12 w-12 items-center justify-center rounded-full bg-loci-yellow text-loci-black text-xl font-semibold">
            ?
          </div>
          <div class="flex-1">
            <h3 id="delete-confirm-title" class="text-lg font-semibold text-loci-black">
              {{ translate('Verwijderen bevestigen', 'Confirm deletion') }}
            </h3>
            <p id="delete-confirm-message" class="mt-2 text-sm text-loci-gray-500">
              {{ translate('Weet je zeker dat je dit document wilt verwijderen?', 'Are you sure you want to remove this document?') }}
              <span class="mt-1 block font-medium text-loci-black">"{{ deleteCandidate.title }}"</span>
            </p>
            <p class="mt-4 text-xs text-loci-gray-400">
              {{ translate('Deze actie kan niet ongedaan worden gemaakt.', 'This action cannot be undone.') }}
            </p>
          </div>
          <button
            type="button"
            class="text-loci-gray-400 hover:text-loci-black disabled:opacity-40"
            :aria-label="translate('Sluiten', 'Close')"
            :disabled="isDeleteInProgress"
            @click="cancelDelete"
          >
            <span aria-hidden="true">&times;</span>
          </button>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <button
            type="button"
            class="px-5 py-2 rounded-loci-full border border-loci-gray-200 text-loci-gray-500 hover:text-loci-black hover:border-loci-gray-400 transition disabled:opacity-50"
            :disabled="isDeleteInProgress"
            @click="cancelDelete"
          >
            {{ translate('Annuleren', 'Cancel') }}
          </button>
          <button
            type="button"
            class="px-5 py-2 rounded-loci-full bg-loci-yellow text-loci-black font-semibold hover:bg-loci-yellow-hover transition disabled:opacity-50"
            :disabled="isDeleteInProgress"
            @click="deleteFromLibrary"
          >
            <span v-if="isDeleteInProgress">
              {{ translate('Verwijderen...', 'Deleting...') }}
            </span>
            <span v-else>
              {{ translate('Verwijderen', 'Delete') }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="deleteError"
      class="fixed inset-0 z-50 flex items-center justify-center px-4"
    >
      <div
        class="absolute inset-0 bg-loci-black/60"
        aria-hidden="true"
        @click="closeDeleteError"
      />

      <div
        class="relative w-full max-w-md bg-loci-white border border-loci-gray-100 rounded-loci-lg shadow-2xl p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-error-title"
        aria-describedby="delete-error-message"
        tabindex="-1"
      >
        <div class="flex items-start gap-4">
          <div class="flex h-12 w-12 items-center justify-center rounded-full bg-loci-yellow text-loci-black text-xl font-semibold">
            !
          </div>
          <div class="flex-1">
            <h3 id="delete-error-title" class="text-lg font-semibold text-loci-black">
              {{ deleteError.title }}
            </h3>
            <p id="delete-error-message" class="mt-2 text-sm text-loci-gray-500">
              {{ deleteError.message }}
            </p>
          </div>
          <button
            type="button"
            class="text-loci-gray-400 hover:text-loci-black"
            :aria-label="translate('Sluiten', 'Close')"
            @click="closeDeleteError"
          >
            <span aria-hidden="true">&times;</span>
          </button>
        </div>

        <div class="mt-6 flex justify-end">
          <button
            type="button"
            class="px-5 py-2 rounded-loci-full bg-loci-black text-loci-white hover:bg-loci-black-deep transition"
            @click="closeDeleteError"
          >
            {{ translate('Begrepen', 'Got it') }}
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
});

const api = useApi();
const { translate } = useTranslations();

const searchQuery = ref('');
const isLoading = ref(true);
const error = ref<string | null>(null);
const tree = ref<any[]>([]);
const selectedId = ref<number | null>(null);
const selectedDocument = ref<any | null>(null);
const deletingId = ref<number | null>(null);
const expandedCategories = ref<Set<string>>(new Set());
const deleteError = ref<{ title: string; message: string } | null>(null);
const deleteCandidate = ref<any | null>(null);

type CategoryGroup = {
  name: string;
  documents: any[];
};

const groupedByCategory = computed<CategoryGroup[]>(() => {
  const groups: Record<string, any[]> = {};

  for (const doc of tree.value) {
    const category = doc.category || translate('Geen categorie', 'No category');
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(doc);
  }

  return Object.entries(groups)
    .map(([name, documents]) => ({ name, documents }))
    .sort((a, b) => a.name.localeCompare(b.name));
});

const filteredCategories = computed<CategoryGroup[]>(() => {
  if (!searchQuery.value.trim()) {
    return groupedByCategory.value;
  }

  const query = searchQuery.value.toLowerCase();
  return groupedByCategory.value
    .map((category) => ({
      name: category.name,
      documents: category.documents.filter(
        (doc) =>
          doc.title.toLowerCase().includes(query) ||
          (doc.category && doc.category.toLowerCase().includes(query)),
      ),
    }))
    .filter((category) => category.documents.length > 0);
});

const isDeleteInProgress = computed(() => {
  if (!deleteCandidate.value) return false;
  return deletingId.value === deleteCandidate.value.id;
});

function toggleCategory(categoryName: string) {
  if (expandedCategories.value.has(categoryName)) {
    expandedCategories.value.delete(categoryName);
  } else {
    expandedCategories.value.add(categoryName);
  }
  expandedCategories.value = new Set(expandedCategories.value);
}

onMounted(async () => {
  await loadTree();
});

async function loadTree() {
  isLoading.value = true;
  error.value = null;

  try {
    const response = await api.get<{ tree: any[] }>('/library/tree');
    tree.value = response.tree;
  } catch (e: any) {
    error.value = e.message || translate('Kon documenten niet laden', 'Unable to load documents');
    console.error('Failed to load tree:', e);
  } finally {
    isLoading.value = false;
  }
}

async function selectDocument(node: any) {
  selectedId.value = node.id;

  try {
    const response = await api.get<{ document: any }>(`/library/documents/${node.id}`);
    selectedDocument.value = response.document;
  } catch (e: any) {
    console.error('Failed to load document:', e);
  }
}

function requestDelete(node: any) {
  if (deletingId.value) return;
  deleteCandidate.value = node;
}

function cancelDelete() {
  if (isDeleteInProgress.value) return;
  deleteCandidate.value = null;
}

async function deleteFromLibrary() {
  if (!deleteCandidate.value || isDeleteInProgress.value) {
    return;
  }

  const node = deleteCandidate.value;
  deletingId.value = node.id;

  try {
    await api.delete(`/documents/${node.id}`);

    if (selectedId.value === node.id) {
      selectedId.value = null;
      selectedDocument.value = null;
    }

    await loadTree();
  } catch (e: any) {
    showDeleteError(typeof e?.message === 'string' ? e.message : undefined);
  } finally {
    deleteCandidate.value = null;
    deletingId.value = null;
  }
}

function showDeleteError(message?: string) {
  deleteError.value = {
    title: translate('Verwijderen mislukt', 'Delete failed'),
    message:
      (message && message.trim()) ||
      translate(
        'Er ging iets mis bij het verwijderen. Probeer het later opnieuw.',
        'Something went wrong while deleting. Please try again later.',
      ),
  };
}

function closeDeleteError() {
  deleteError.value = null;
}
</script>
