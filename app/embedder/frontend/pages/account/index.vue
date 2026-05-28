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

      <section class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-xl font-semibold text-loci-black">
              {{ translate('Kennisbank backup', 'Knowledge base backup') }}
            </h2>
            <p class="text-sm text-loci-gray-500">
              {{ translate('Download een ZIP-bestand met alle kennis uit deze kennisbank.', 'Download a ZIP file with all knowledge from this knowledge base.') }}
            </p>
          </div>
          <button
            type="button"
            class="inline-flex min-h-11 items-center justify-center rounded-loci px-5 py-2.5 text-sm font-semibold text-loci-black-deep transition-all disabled:cursor-not-allowed disabled:opacity-60"
            :class="isExporting ? 'bg-loci-gray-200' : 'bg-loci-yellow hover:bg-loci-yellow-hover'"
            :disabled="isExporting"
            @click="downloadBackup"
          >
            {{ isExporting ? translate('Backup maken...', 'Creating backup...') : translate('Backup kennisbank', 'Back up knowledge base') }}
          </button>
        </div>
        <p v-if="exportError" class="mt-4 rounded-loci border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {{ exportError }}
        </p>
      </section>

    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
});

const authStore = useAuthStore();
const { translate } = useTranslations();
const api = useApi();
const isExporting = ref(false);
const exportError = ref('');

async function downloadBackup() {
  isExporting.value = true;
  exportError.value = '';
  try {
    const { blob, filename } = await api.download('/insights/export/backup');
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (e: any) {
    exportError.value = e?.message || translate('Backup downloaden mislukt.', 'Backup download failed.');
  } finally {
    isExporting.value = false;
  }
}
</script>
