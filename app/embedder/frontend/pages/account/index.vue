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

    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
});

const authStore = useAuthStore();
const { translate } = useTranslations();
</script>
