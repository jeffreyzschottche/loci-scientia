<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Tab Navigation -->
    <div class="bg-white border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav class="flex space-x-8">
          <NuxtLink
            to="/kennisbank/upload"
            class="py-4 px-1 border-b-2 font-medium text-sm border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          >
            Uploaden
          </NuxtLink>
          <NuxtLink
            to="/kennisbank/library"
            class="py-4 px-1 border-b-2 font-medium text-sm border-blue-500 text-blue-600"
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
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="flex gap-4" style="height: calc(100vh - 200px);">
        <!-- Left Panel: Tree -->
        <div class="w-80 bg-white rounded-lg shadow flex flex-col">
          <div class="p-4 border-b">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Zoeken..."
              class="w-full px-4 py-2 border rounded-lg"
            >
          </div>

          <div class="flex-1 overflow-auto p-4">
            <div v-if="isLoading" class="text-center py-8">
              <p class="text-gray-500">Laden...</p>
            </div>

            <div v-else-if="error" class="text-center py-8">
              <p class="text-red-500">{{ error }}</p>
            </div>

            <div v-else-if="tree.length === 0" class="text-center py-8 text-gray-500">
              <p>Geen documenten gevonden</p>
              <NuxtLink to="/kennisbank/upload" class="text-blue-600 hover:underline mt-2 block">
                Upload je eerste document
              </NuxtLink>
            </div>

            <div v-else>
              <div
                v-for="node in tree"
                :key="node.id"
                class="p-2 hover:bg-gray-100 rounded cursor-pointer"
                :class="{ 'bg-blue-100': selectedId === node.id }"
                @click="selectDocument(node)"
              >
                <div class="flex items-start justify-between gap-2">
                  <div class="flex-1 min-w-0">
                    <p class="font-medium truncate" :title="node.title">{{ node.title }}</p>
                    <p class="text-sm text-gray-500">{{ node.category || 'Geen categorie' }}</p>
                  </div>
                  <button
                    type="button"
                    class="text-red-600 hover:text-red-800 disabled:opacity-50"
                    title="Verwijderen uit kennisbank"
                    :disabled="deletingId === node.id"
                    @click.stop="deleteFromLibrary(node)"
                  >
                    <svg
                      v-if="deletingId !== node.id"
                      class="h-5 w-5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    <svg
                      v-else
                      class="h-5 w-5 animate-spin"
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

        <!-- Right Panel: Preview -->
        <div class="flex-1 bg-white rounded-lg shadow flex flex-col">
          <div v-if="!selectedDocument" class="flex-1 flex items-center justify-center text-gray-500">
            <p>Selecteer een document</p>
          </div>

          <template v-else>
            <div class="p-4 border-b">
              <h2 class="text-lg font-medium">{{ selectedDocument.title }}</h2>
              <p class="text-sm text-gray-500">{{ selectedDocument.category || 'Geen categorie' }}</p>
            </div>

            <div class="flex-1 overflow-auto p-4">
              <div v-if="selectedDocument.sections" class="space-y-6">
                <div v-for="section in selectedDocument.sections" :key="section.id">
                  <h3 class="font-semibold border-b pb-2">{{ section.title }}</h3>
                  <p class="mt-2 whitespace-pre-wrap text-gray-700">{{ section.text }}</p>
                </div>
              </div>
              <div v-else class="text-gray-500">
                <p>Geen secties gevonden</p>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
});

const api = useApi();

const searchQuery = ref('');
const isLoading = ref(true);
const error = ref<string | null>(null);
const tree = ref<any[]>([]);
const selectedId = ref<number | null>(null);
const selectedDocument = ref<any | null>(null);
const deletingId = ref<number | null>(null);

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
    error.value = e.message || 'Kon documenten niet laden';
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

  const confirmed = confirm(`Weet je zeker dat je "${node.title}" wilt verwijderen uit de kennisbank?`);
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
    alert(e.message || 'Verwijderen mislukt');
  } finally {
    deletingId.value = null;
  }
}
</script>
