<template>
  <NuxtLayout name="auth">
    <div class="rounded-lg bg-white p-8 shadow">
      <h2 class="mb-6 text-center text-2xl font-bold">Reset Password</h2>

      <div v-if="success" class="mb-4 rounded bg-green-50 p-3 text-green-600">
        {{ success }}
      </div>

      <form v-else @submit.prevent="handleSubmit" class="space-y-4">
        <div v-if="error" class="rounded bg-red-50 p-3 text-red-600">
          {{ error }}
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Email</label>
          <input
            v-model="email"
            type="email"
            required
            class="w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {{ loading ? 'Sending...' : 'Send Reset Link' }}
        </button>
      </form>

      <p class="mt-4 text-center text-sm text-gray-600">
        <NuxtLink to="/login" class="text-blue-600 hover:underline">
          Back to login
        </NuxtLink>
      </p>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'guest',
  layout: false,
});

const authStore = useAuthStore();

const email = ref('');
const error = ref('');
const success = ref('');
const loading = ref(false);

async function handleSubmit() {
  error.value = '';
  success.value = '';
  loading.value = true;

  try {
    const response = await authStore.forgotPassword(email.value);
    success.value = response.message;
  } catch (err: any) {
    if (err.data?.errors) {
      error.value = Object.values(err.data.errors).flat().join(', ');
    } else {
      error.value = err.message || 'Failed to send reset link';
    }
  } finally {
    loading.value = false;
  }
}
</script>
