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
            class="py-4 px-1 border-b-2 font-medium text-sm border-blue-500 text-blue-600"
          >
            Inzicht
          </NuxtLink>
        </nav>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">Kennisbank Inzicht</h1>
        <button
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          @click="exportManifest"
        >
          Exporteer JSON-LD
        </button>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-white rounded-lg shadow p-6">
          <p class="text-sm text-gray-500">Documenten</p>
          <p class="text-3xl font-bold">{{ stats.total_documents }}</p>
        </div>
        <div class="bg-white rounded-lg shadow p-6">
          <p class="text-sm text-gray-500">Secties</p>
          <p class="text-3xl font-bold">{{ stats.total_sections }}</p>
        </div>
        <div class="bg-white rounded-lg shadow p-6">
          <p class="text-sm text-gray-500">Chunks</p>
          <p class="text-3xl font-bold">{{ stats.total_chunks }}</p>
        </div>
        <div class="bg-white rounded-lg shadow p-6">
          <p class="text-sm text-gray-500">Woorden (est.)</p>
          <p class="text-3xl font-bold">{{ formatNumber(stats.estimated_words) }}</p>
        </div>
      </div>

      <!-- Categories -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b">
            <h2 class="text-lg font-medium">Categorieen</h2>
          </div>
          <div class="p-6">
            <div v-if="Object.keys(categories).length === 0" class="text-gray-500">
              Nog geen categorieen
            </div>
            <div v-else class="space-y-3">
              <div v-for="(count, category) in categories" :key="category" class="flex justify-between">
                <span>{{ category }}</span>
                <span class="text-gray-500">{{ count }} documenten</span>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b">
            <h2 class="text-lg font-medium">Recent verwerkt</h2>
          </div>
          <div class="divide-y">
            <div v-if="recentDocuments.length === 0" class="p-6 text-gray-500">
              Nog geen documenten
            </div>
            <div
              v-for="doc in recentDocuments"
              :key="doc.id"
              class="px-6 py-4"
            >
              <p class="font-medium">{{ doc.title }}</p>
              <p class="text-sm text-gray-500">{{ formatDate(doc.updated_at) }}</p>
            </div>
          </div>
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

const stats = ref({
  total_documents: 0,
  processed_documents: 0,
  total_sections: 0,
  total_chunks: 0,
  estimated_words: 0,
});
const categories = ref<Record<string, number>>({});
const recentDocuments = ref<any[]>([]);

onMounted(async () => {
  await loadStats();
});

async function loadStats() {
  try {
    const response = await api.get<{
      stats: typeof stats.value;
      categories: Record<string, number>;
      recent_documents: any[];
    }>('/insights/stats');

    stats.value = response.stats;
    categories.value = response.categories;
    recentDocuments.value = response.recent_documents;
  } catch (e) {
    console.error('Failed to load stats:', e);
  }
}

async function exportManifest() {
  try {
    const response = await api.get<Record<string, any>>('/insights/export/manifest');

    const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/ld+json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kennisbank-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e: any) {
    alert(e.message || 'Export mislukt');
  }
}

function formatNumber(num: number) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('nl-NL');
}
</script>
