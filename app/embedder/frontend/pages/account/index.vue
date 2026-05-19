<template>
  <div class="mx-auto max-w-5xl px-4 py-12">
    <div class="space-y-6">
      <section class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
        <div class="mb-6 border-b border-loci-gray-100 pb-4">
          <h1 class="text-2xl font-semibold text-loci-black">
            {{ translate('Mijn account', 'My Account') }}
          </h1>
          <p class="text-sm text-loci-gray-500">
            {{ translate('Dit bedrijfsaccount wordt beheerd door Aitje.', 'This company account is managed by Aitje.') }}
          </p>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm font-medium text-loci-black">
              {{ translate('Naam', 'Name') }}
            </label>
            <div class="rounded-loci border border-loci-gray-200 bg-loci-cream px-4 py-3 text-loci-black">
              {{ authStore.user?.name || translate('Onbekend', 'Unknown') }}
            </div>
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-loci-black">
              {{ translate('Email', 'Email') }}
            </label>
            <div class="rounded-loci border border-loci-gray-200 bg-loci-cream px-4 py-3 text-loci-black">
              {{ authStore.user?.email || translate('Onbekend', 'Unknown') }}
            </div>
          </div>
        </div>

        <p class="mt-4 text-sm text-loci-gray-500">
          {{ translate('Neem contact op met Aitje om accountgegevens of toegang te wijzigen.', 'Contact Aitje to change account details or access.') }}
        </p>
      </section>

      <!-- Sync naar Aitje-device (LAN push, vervangt de oude Git-koppeling) -->
      <section class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
        <div class="flex flex-col md:flex-row md:items-start md:justify-between mb-6">
          <div>
            <h2 class="text-xl font-semibold text-loci-black">
              {{ translate('Sync naar Aitje-device', 'Sync to Aitje device') }}
            </h2>
            <p class="text-sm text-loci-gray-500">
              {{ translate(
                'Verstuur je kennisbank rechtstreeks naar het Aitje-apparaat in dit netwerk. Geen Git, geen cloud — alles blijft lokaal.',
                'Push your knowledge base directly to the Aitje device on this network. No Git, no cloud — everything stays local.'
              ) }}
            </p>
          </div>
          <div class="text-sm text-loci-gray-500 mt-2 md:mt-0">
            {{ translate('Laatst gesynchroniseerd:', 'Last synced:') }}
            <span class="font-medium text-loci-black">
              {{ lastPushedAt ? formatDateTime(lastPushedAt) : translate('Nooit', 'Never') }}
            </span>
          </div>
        </div>

        <div
          v-if="syncStatus"
          class="mb-6 p-4 rounded-loci border"
          :class="syncStatus.type === 'error'
            ? 'bg-red-50 border-red-200 text-red-700'
            : syncStatus.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-700'
              : 'bg-loci-yellow/10 border-loci-yellow text-loci-black'"
        >
          {{ syncStatus.message }}
        </div>

        <div class="flex justify-end">
          <button
            type="button"
            class="px-6 py-3 bg-loci-yellow text-loci-black-deep rounded-loci-full font-semibold hover:bg-loci-yellow-hover transition-all disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
            :disabled="syncing"
            @click="syncToDevice"
          >
            {{ syncing
              ? translate('Synchroniseren...', 'Syncing...')
              : translate('Sync naar device', 'Sync to device') }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

definePageMeta({
  middleware: 'auth',
});

const authStore = useAuthStore();
const api = useApi();
const { translate, currentLanguage } = useTranslations();

type StatusState = {
  type: 'success' | 'error' | 'info';
  message: string;
};

function extractError(error: any): string | undefined {
  if (error?.data?.errors) {
    return Object.values(error.data.errors).flat().join(', ');
  }
  return error?.data?.message || error?.message;
}

const syncing = ref(false);
const syncStatus = ref<StatusState | null>(null);
const lastPushedAt = ref<string | null>(null);

async function syncToDevice() {
  try {
    syncing.value = true;
    syncStatus.value = { type: 'info', message: translate('Synchroniseren...', 'Syncing...') };

    const response = await api.post<{
      message: string;
      last_pushed_at: string | null;
    }>('/kennisbank/push');

    lastPushedAt.value = response.last_pushed_at;
    syncStatus.value = {
      type: 'success',
      message: response.message || translate('Sync voltooid', 'Sync completed'),
    };
  } catch (e: any) {
    syncStatus.value = {
      type: 'error',
      message: extractError(e) || translate('Sync mislukt', 'Sync failed'),
    };
  } finally {
    syncing.value = false;
  }
}

function formatDateTime(dateStr: string) {
  const date = new Date(dateStr);
  const locale = currentLanguage.value === 'en' ? 'en-US' : 'nl-NL';
  return `${date.toLocaleDateString(locale)} ${date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })}`;
}
</script>
