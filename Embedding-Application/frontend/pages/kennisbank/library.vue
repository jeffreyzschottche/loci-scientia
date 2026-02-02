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
                      @click.stop="deleteFromLibrary(doc)"
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

async function deleteFromLibrary(node: any) {
  if (deletingId.value) return;

  const confirmed = confirm(
    translate(
      `Weet je zeker dat je "${node.title}" wilt verwijderen uit de kennisbank?`,
      `Are you sure you want to remove "${node.title}" from the knowledge base?`,
    ),
  );
  if (!confirmed) return;

  deletingId.value = node.id;

  try {
    await api.delete(`/documents/${node.id}`);

    if (selectedId.value === node.id) {
      selectedId.value = null;
      selectedDocument.value = null;
    }

    await loadTree();
  } catch (e: any) {
    alert(e.message || translate('Verwijderen mislukt', 'Delete failed'));
  } finally {
    deletingId.value = null;
  }
}
</script>
