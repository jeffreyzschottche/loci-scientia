<template>
  <div class="min-h-screen bg-loci-gray-50">
    <!-- Tab Navigation -->
    <div class="bg-loci-white border-b border-loci-gray-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav class="flex items-center justify-between py-4" aria-label="Tabs">
          <div class="flex items-center space-x-2">
            <NuxtLink
              to="/kennisbank/upload"
              class="rounded-full px-5 py-2.5 text-sm font-semibold transition-all"
              :class="isActive('/kennisbank/upload')
                ? 'bg-loci-yellow text-loci-black-deep'
                : 'bg-loci-gray-50 text-loci-gray-500 hover:bg-loci-gray-200 hover:text-loci-black'"
            >
              {{ translate('Uploaden', 'Upload') }}
            </NuxtLink>
            <NuxtLink
              to="/kennisbank/library"
              class="rounded-full px-5 py-2.5 text-sm font-semibold transition-all"
              :class="isActive('/kennisbank/library')
                ? 'bg-loci-yellow text-loci-black-deep'
                : 'bg-loci-gray-50 text-loci-gray-500 hover:bg-loci-gray-200 hover:text-loci-black'"
            >
              {{ translate('Bibliotheek', 'Library') }}
            </NuxtLink>
            <NuxtLink
              to="/kennisbank/priorities"
              class="rounded-full px-5 py-2.5 text-sm font-semibold transition-all"
              :class="isActive('/kennisbank/priorities')
                ? 'bg-loci-yellow text-loci-black-deep'
                : 'bg-loci-gray-50 text-loci-gray-500 hover:bg-loci-gray-200 hover:text-loci-black'"
            >
              {{ translate('Prioriteiten', 'Priorities') }}
            </NuxtLink>
            <NuxtLink
              to="/kennisbank/insights"
              class="rounded-full px-5 py-2.5 text-sm font-semibold transition-all"
              :class="isActive('/kennisbank/insights')
                ? 'bg-loci-yellow text-loci-black-deep'
                : 'bg-loci-gray-50 text-loci-gray-500 hover:bg-loci-gray-200 hover:text-loci-black'"
            >
              {{ translate('Inzicht', 'Insights') }}
            </NuxtLink>
          </div>

          <button
            @click="syncToGit"
            :disabled="syncing"
            class="rounded-full px-5 py-2.5 text-sm font-semibold transition-all bg-loci-yellow text-loci-black-deep hover:bg-loci-black hover:text-loci-white disabled:opacity-50"
          >
            {{ syncing ? translate('Synchroniseren...', 'Syncing...') : translate('Sync naar GitHub', 'Sync to GitHub') }}
          </button>
        </nav>
      </div>
    </div>

    <!-- Sync Status -->
    <div v-if="syncStatus" class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4">
      <div
        class="p-4 rounded-loci border"
        :class="syncStatus.type === 'error'
          ? 'bg-red-50 border-red-200 text-red-700'
          : syncStatus.type === 'success'
            ? 'bg-green-50 border-green-200 text-green-700'
            : 'bg-loci-yellow/10 border-loci-yellow text-loci-black'"
      >
        {{ syncStatus.message }}
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute();
const api = useApi();
const { translate } = useTranslations();

const syncing = ref(false);
const syncStatus = ref<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

function isActive(path: string) {
  return route.path.startsWith(path);
}

async function syncToGit() {
  try {
    syncing.value = true;
    syncStatus.value = { type: 'info', message: translate('Synchroniseren...', 'Syncing...') };
    const response = await api.post<{ message: string }>('/kennisbank/push');
    syncStatus.value = {
      type: 'success',
      message: response.message || translate('Sync voltooid', 'Sync completed'),
    };
    setTimeout(() => {
      syncStatus.value = null;
    }, 5000);
  } catch (e: any) {
    syncStatus.value = {
      type: 'error',
      message: e?.data?.message || e?.message || translate('Sync mislukt. Controleer je Git configuratie in Mijn Account.', 'Sync failed. Check your Git configuration under My Account.'),
    };
  } finally {
    syncing.value = false;
  }
}
</script>
