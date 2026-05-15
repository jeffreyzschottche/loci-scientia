<template>
  <NuxtLayout name="auth">
    <div class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8 text-center">
      <div v-if="loading" class="py-8">
        <p class="text-loci-gray-500">Je email wordt gecontroleerd...</p>
      </div>

      <div v-else-if="success" class="space-y-4 py-8">
        <div class="text-green-600">
          <svg class="mx-auto h-16 w-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 class="text-xl font-semibold text-loci-black">Email bevestigd</h3>
        <p class="text-loci-gray-500">Je kunt nu inloggen en naar de kennisbank gaan.</p>
        <div class="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <NuxtLink to="/" class="rounded-full bg-loci-yellow px-6 py-2 font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover">
            Ga naar login
          </NuxtLink>
          <NuxtLink to="/kennisbank" class="rounded-full border border-loci-gray-200 bg-loci-white px-6 py-2 font-semibold text-loci-black transition-all hover:border-loci-yellow hover:bg-loci-yellow hover:text-loci-black-deep">
            Open kennisbank
          </NuxtLink>
        </div>
      </div>

      <div v-else class="space-y-4 py-8">
        <div class="text-red-600">
          <svg class="mx-auto h-16 w-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h3 class="text-xl font-semibold text-loci-black">Verificatie mislukt</h3>
        <p class="text-loci-gray-500">{{ error }}</p>
        <NuxtLink to="/account" class="inline-flex justify-center rounded-full bg-loci-yellow px-6 py-2 font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover">
          Ga naar Mijn Account
        </NuxtLink>
      </div>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
import { apiFetch } from '~/services/apiFetch';

definePageMeta({
  layout: false,
});

const route = useRoute();
const loading = ref(true);
const success = ref(false);
const error = ref('Er ontbreekt een geldige verificatielink.');

onMounted(async () => {
  const verificationUrl = route.query.url as string;

  if (!verificationUrl) {
    loading.value = false;
    return;
  }

  try {
    await apiFetch(verificationUrl);
    success.value = true;
    error.value = '';
  } catch (err: any) {
    error.value = err?.data?.message || err?.message || 'Verificatie mislukt';
  } finally {
    loading.value = false;
  }
});
</script>
