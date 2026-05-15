<template>
  <div class="mx-auto max-w-7xl px-4 py-12">
    <div class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-6">
      <h1 class="mb-4 text-3xl font-bold text-loci-black">Dashboard</h1>

      <div v-if="authStore.user" class="space-y-4">
        <div>
          <p class="text-loci-gray-500">Welkom terug,</p>
          <p class="text-xl font-semibold text-loci-black">{{ authStore.user.name }}</p>
        </div>

        <div>
          <p class="text-sm text-loci-gray-500">Email</p>
          <p class="text-loci-black">{{ authStore.user.email }}</p>
        </div>

        <div v-if="!authStore.user.email_verified_at" class="rounded-loci border border-loci-yellow bg-loci-yellow/10 p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-loci-black">Verifieer je email</p>
              <p class="text-sm text-loci-gray-500">Controleer je inbox voor een verificatielink</p>
            </div>
            <button
              @click="resendVerification"
              :disabled="resending"
              class="rounded-full bg-loci-yellow px-4 py-2 font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
            >
              {{ resending ? 'Verzenden...' : 'Opnieuw versturen' }}
            </button>
          </div>
          <p v-if="resendMessage" class="mt-2 text-sm text-green-700">{{ resendMessage }}</p>
        </div>

        <div v-else class="flex items-center text-green-600">
          <svg class="mr-2 h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clip-rule="evenodd"
            />
          </svg>
          <span>Email geverifieerd</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'auth',
});

const authStore = useAuthStore();
const resending = ref(false);
const resendMessage = ref('');

async function resendVerification() {
  resending.value = true;
  resendMessage.value = '';

  try {
    const response = await authStore.resendVerification();
    resendMessage.value = response.message;
  } catch (error: any) {
    resendMessage.value = error.message || 'Failed to resend verification email';
  } finally {
    resending.value = false;
  }
}
</script>
