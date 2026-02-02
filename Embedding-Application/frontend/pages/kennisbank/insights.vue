<template>
  <KennisbankTabLayout>
    <div>
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-loci-black">
          {{ translate('Kennisbank Inzicht', 'Knowledge base insights') }}
        </h1>
      </div>

      <!-- Stats -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-loci-white rounded-loci-lg border border-loci-gray-100 p-6">
          <p class="text-sm text-loci-gray-500">{{ translate('Documenten', 'Documents') }}</p>
          <p class="text-3xl font-bold text-loci-black">{{ stats.total_documents }}</p>
        </div>
        <div class="bg-loci-white rounded-loci-lg border border-loci-gray-100 p-6">
          <p class="text-sm text-loci-gray-500">{{ translate('Secties', 'Sections') }}</p>
          <p class="text-3xl font-bold text-loci-black">{{ stats.total_sections }}</p>
        </div>
        <div class="bg-loci-white rounded-loci-lg border border-loci-gray-100 p-6">
          <p class="text-sm text-loci-gray-500">Chunks</p>
          <p class="text-3xl font-bold text-loci-black">{{ stats.total_chunks }}</p>
        </div>
        <div class="bg-loci-white rounded-loci-lg border border-loci-gray-100 p-6">
          <p class="text-sm text-loci-gray-500">{{ translate('Woorden (est.)', 'Words (est.)') }}</p>
          <p class="text-3xl font-bold text-loci-black">{{ formatNumber(stats.estimated_words) }}</p>
        </div>
      </div>

      <!-- Categories -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-loci-white rounded-loci-lg border border-loci-gray-100">
          <div class="px-6 py-4 border-b border-loci-gray-100">
            <h2 class="text-lg font-medium text-loci-black">
              {{ translate('Categorieën', 'Categories') }}
            </h2>
          </div>
          <div class="p-6">
            <div v-if="Object.keys(categories).length === 0" class="text-loci-gray-500">
              {{ translate('Nog geen categorieën', 'No categories yet') }}
            </div>
            <div v-else class="space-y-3">
              <div v-for="(count, category) in categories" :key="category" class="flex justify-between">
                <span class="text-loci-black">{{ category }}</span>
                <span class="text-loci-gray-500">{{ count }} {{ translate('documenten', 'documents') }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-loci-white rounded-loci-lg border border-loci-gray-100">
          <div class="px-6 py-4 border-b border-loci-gray-100">
            <h2 class="text-lg font-medium text-loci-black">
              {{ translate('Recent verwerkt', 'Recently processed') }}
            </h2>
          </div>
          <div class="divide-y divide-loci-gray-100">
            <div v-if="recentDocuments.length === 0" class="p-6 text-loci-gray-500">
              {{ translate('Nog geen documenten', 'No documents yet') }}
            </div>
            <div
              v-for="doc in recentDocuments"
              :key="doc.id"
              class="px-6 py-4"
            >
              <p class="font-medium text-loci-black">{{ doc.title }}</p>
              <p class="text-sm text-loci-gray-500">{{ formatDate(doc.updated_at) }}</p>
            </div>
          </div>
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
const { translate, currentLanguage } = useTranslations();

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

function formatNumber(num: number) {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

function formatDate(dateStr: string) {
  const locale = currentLanguage.value === 'en' ? 'en-US' : 'nl-NL';
  return new Date(dateStr).toLocaleDateString(locale);
}
</script>
