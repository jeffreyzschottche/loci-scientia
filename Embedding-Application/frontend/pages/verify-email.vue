<template>
  <NuxtLayout name="auth">
    <div class="rounded-lg bg-white p-8 text-center shadow">
      <div v-if="loading" class="py-8">
        <p class="text-gray-600">Je email wordt gecontroleerd...</p>
      </div>

      <div v-else-if="success" class="space-y-4 py-8">
        <div class="text-green-600">
          <svg class="mx-auto h-16 w-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 class="text-xl font-semibold">Email bevestigd</h3>
        <p class="text-gray-600">Je kunt nu inloggen en naar de kennisbank gaan.</p>
        <div class="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <NuxtLink to="/" class="rounded bg-blue-600 px-6 py-2 text-white hover:bg-blue-700">
            Ga naar login
          </NuxtLink>
          <NuxtLink to="/kennisbank" class="rounded border border-blue-600 px-6 py-2 text-blue-600 hover:bg-blue-50">
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
        <h3 class="text-xl font-semibold">Verificatie mislukt</h3>
        <p class="text-gray-600">{{ error }}</p>
        <NuxtLink to="/account" class="inline-flex justify-center rounded bg-yellow-600 px-6 py-2 text-white hover:bg-yellow-700">
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
