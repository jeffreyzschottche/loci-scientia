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
      <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-6">
        <h1 class="text-2xl font-bold">Kennisbank Inzicht</h1>
        <button
          class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          :disabled="syncing || !hasGitConfig"
          @click="syncToOs"
        >
          {{ syncing ? t('syncing') : t('push_to_git') }}
        </button>
      </div>

      <div
        v-if="syncStatus"
        class="mb-6 p-4 rounded-lg"
        :class="syncStatus.type === 'error'
          ? 'bg-red-50 text-red-700'
          : syncStatus.type === 'success'
            ? 'bg-green-50 text-green-700'
            : 'bg-blue-50 text-blue-700'"
      >
        {{ syncStatus.message }}
      </div>

      <div class="bg-white rounded-lg shadow p-6 mb-8">
        <div class="flex flex-col md:flex-row md:items-start md:justify-between mb-6">
          <div>
            <h2 class="text-lg font-medium">{{ t('git_configuration') }}</h2>
            <p class="text-sm text-gray-500">Stel de GitHub repo in voor de Sync to OS actie.</p>
          </div>
          <div class="text-sm text-gray-500 mt-2 md:mt-0">
            {{ t('git_last_synced') }}:
            <span class="font-medium text-gray-700">
              {{ gitConfig.last_pushed_at ? formatDateTime(gitConfig.last_pushed_at) : 'Nooit' }}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700">{{ t('git_repo_url') }}</label>
            <input
              v-model="gitConfig.repo_url"
              type="text"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="https://github.com/naam/kennisbank.git"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700">{{ t('git_branch') }}</label>
            <input
              v-model="gitConfig.branch"
              type="text"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="main"
            >
          </div>

          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700">{{ t('git_access_token') }}</label>
            <input
              v-model="gitConfig.access_token"
              type="password"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="ghp_xxxxxxxxx"
            >
            <p class="text-xs text-gray-500 mt-1">{{ t('git_token_hint') }}</p>
          </div>
        </div>

        <div class="flex justify-end mt-6">
          <button
            class="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
            :disabled="savingConfig || !gitConfig.repo_url || !gitConfig.branch"
            @click="saveGitConfig"
          >
            {{ savingConfig ? t('saving') : t('save_configuration') }}
          </button>
        </div>
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
const { t } = useTranslations();

type GitConfigState = {
  repo_url: string;
  branch: string;
  access_token: string;
  has_access_token: boolean;
  last_pushed_at: string | null;
};

type StatusState = {
  type: 'success' | 'error' | 'info';
  message: string;
};

const stats = ref({
  total_documents: 0,
  processed_documents: 0,
  total_sections: 0,
  total_chunks: 0,
  estimated_words: 0,
});
const categories = ref<Record<string, number>>({});
const recentDocuments = ref<any[]>([]);
const gitConfig = ref<GitConfigState>({
  repo_url: '',
  branch: 'main',
  access_token: '',
  has_access_token: false,
  last_pushed_at: null,
});
const savingConfig = ref(false);
const syncing = ref(false);
const syncStatus = ref<StatusState | null>(null);

const hasGitConfig = computed(() => {
  return Boolean(
    gitConfig.value.repo_url &&
      gitConfig.value.branch &&
      (gitConfig.value.has_access_token || gitConfig.value.access_token)
  );
});

onMounted(async () => {
  await Promise.all([loadStats(), loadGitConfig()]);
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

async function loadGitConfig() {
  try {
    const response = await api.get<{ config: (GitConfigState & { has_access_token: boolean }) | null }>('/kennisbank/git-config');

    if (response.config) {
      gitConfig.value = {
        repo_url: response.config.repo_url || '',
        branch: response.config.branch || 'main',
        access_token: '',
        has_access_token: Boolean(response.config.has_access_token),
        last_pushed_at: response.config.last_pushed_at || null,
      };
    } else {
      gitConfig.value = {
        repo_url: '',
        branch: 'main',
        access_token: '',
        has_access_token: false,
        last_pushed_at: null,
      };
    }
  } catch (e) {
    console.error('Failed to load git config:', e);
    syncStatus.value = {
      type: 'error',
      message: (e as Error).message || 'Kon git-config niet laden',
    };
  }
}

async function saveGitConfig() {
  try {
    savingConfig.value = true;
    const payload: Record<string, string> = {
      repo_url: gitConfig.value.repo_url,
      branch: gitConfig.value.branch || 'main',
    };

    if (gitConfig.value.access_token) {
      payload.access_token = gitConfig.value.access_token;
    }

    const response = await api.post<{ config: GitConfigState; message: string }>('/kennisbank/git-config', payload);
    gitConfig.value.has_access_token = response.config.has_access_token ?? Boolean(payload.access_token);
    gitConfig.value.last_pushed_at = response.config.last_pushed_at || gitConfig.value.last_pushed_at;
    gitConfig.value.access_token = '';

    syncStatus.value = { type: 'success', message: t('git_config_saved') };
  } catch (e: any) {
    syncStatus.value = { type: 'error', message: e.message || t('save_failed') };
  } finally {
    savingConfig.value = false;
  }
}

async function syncToOs() {
  if (!hasGitConfig.value) {
    syncStatus.value = { type: 'error', message: t('git_config_required') };
    return;
  }

  try {
    syncing.value = true;
    syncStatus.value = { type: 'info', message: t('syncing') };
    const response = await api.post<{ message: string; last_pushed_at: string | null }>('/kennisbank/push');
    gitConfig.value.last_pushed_at = response.last_pushed_at;
    syncStatus.value = {
      type: 'success',
      message: response.message || 'Sync voltooid',
    };
  } catch (e: any) {
    syncStatus.value = { type: 'error', message: e.message || t('push_failed') };
  } finally {
    syncing.value = false;
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

function formatDateTime(dateStr: string) {
  const date = new Date(dateStr);
  return `${date.toLocaleDateString('nl-NL')} ${date.toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' })}`;
}
</script>
