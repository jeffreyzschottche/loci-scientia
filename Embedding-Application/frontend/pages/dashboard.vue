<template>
  <div class="mx-auto max-w-7xl px-4 py-12">
    <div class="rounded-lg bg-white p-6 shadow">
      <h1 class="mb-4 text-3xl font-bold">Dashboard</h1>

      <div v-if="authStore.user" class="space-y-4">
        <div>
          <p class="text-gray-600">Welcome back,</p>
          <p class="text-xl font-semibold">{{ authStore.user.name }}</p>
        </div>

        <div>
          <p class="text-sm text-gray-600">Email</p>
          <p>{{ authStore.user.email }}</p>
        </div>

        <div v-if="!authStore.user.email_verified_at" class="border-l-4 border-yellow-400 bg-yellow-50 p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-yellow-800">Please verify your email</p>
              <p class="text-sm text-yellow-700">Check your inbox for a verification link</p>
            </div>
            <button
              @click="resendVerification"
              :disabled="resending"
              class="rounded bg-yellow-600 px-4 py-2 text-white hover:bg-yellow-700 disabled:opacity-50"
            >
              {{ resending ? 'Sending...' : 'Resend' }}
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
          <span>Email verified</span>
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
