<template>
  <NuxtLayout name="auth">
    <div class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
      <h2 class="mb-6 text-center text-2xl font-bold text-loci-black">Wachtwoord resetten</h2>

      <div v-if="success" class="mb-4 rounded-loci border border-green-200 bg-green-50 p-3 text-green-600">
        {{ success }}
        <NuxtLink to="/" class="mt-2 block font-semibold text-loci-black hover:text-loci-yellow-hover">
          Ga naar login
        </NuxtLink>
      </div>

      <form v-else @submit.prevent="handleSubmit" class="space-y-4">
        <div v-if="error" class="rounded-loci border border-red-200 bg-red-50 p-3 text-red-600">
          {{ error }}
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-loci-black">Email</label>
          <input
            v-model="form.email"
            type="email"
            required
            class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
          />
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-loci-black">Nieuw wachtwoord</label>
          <input
            v-model="form.password"
            type="password"
            required
            class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
          />
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-loci-black">
            Bevestig wachtwoord
          </label>
          <input
            v-model="form.password_confirmation"
            type="password"
            required
            class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
          />
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full rounded-loci-full bg-loci-yellow py-3 font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
        >
          {{ loading ? 'Resetten...' : 'Wachtwoord resetten' }}
        </button>
      </form>
    </div>
  </NuxtLayout>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'guest',
  layout: false,
});

const authStore = useAuthStore();
const route = useRoute();

const form = reactive({
  token: (route.query.token as string) || '',
  email: (route.query.email as string) || '',
  password: '',
  password_confirmation: '',
});

const error = ref('');
const success = ref('');
const loading = ref(false);

async function handleSubmit() {
  error.value = '';
  success.value = '';
  loading.value = true;

  try {
    const response = await authStore.resetPassword(
      form.token,
      form.email,
      form.password,
      form.password_confirmation
    );
    success.value = response.message;
  } catch (err: any) {
    if (err.data?.errors) {
      error.value = Object.values(err.data.errors).flat().join(', ');
    } else {
      error.value = err.message || 'Failed to reset password';
    }
  } finally {
    loading.value = false;
  }
}
</script>
