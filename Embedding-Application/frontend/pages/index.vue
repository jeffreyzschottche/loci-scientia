<template>
  <div class="min-h-screen bg-gray-100">
    <AppNav />
    <div class="flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div class="w-full max-w-md rounded-lg bg-white p-8 shadow">
        <h1 class="mb-6 text-center text-3xl font-bold">Login</h1>
        <p class="mb-8 text-center text-sm text-gray-500">
          Meld je aan om toegang te krijgen tot de kennisbank.
        </p>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <div v-if="error" class="rounded bg-red-50 p-3 text-red-600">
            {{ error }}
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">Email</label>
            <input
              v-model="form.email"
              type="email"
              required
              class="w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">Wachtwoord</label>
            <input
              v-model="form.password"
              type="password"
              required
              class="w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div class="flex items-center justify-between text-sm">
            <NuxtLink to="/account/forgot-password" class="text-blue-600 hover:underline">
              Wachtwoord vergeten?
            </NuxtLink>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {{ loading ? 'Aan het inloggen...' : 'Login' }}
          </button>
        </form>

        <p class="mt-4 text-center text-sm text-gray-600">
          Nog geen account?
          <NuxtLink to="/register" class="text-blue-600 hover:underline">
            Registreer hier
          </NuxtLink>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: 'guest',
  layout: false,
});

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const form = reactive({
  email: '',
  password: '',
});

const error = ref('');
const loading = ref(false);

async function handleLogin() {
  error.value = '';
  loading.value = true;

  try {
    await authStore.login(form.email, form.password);
    const redirect = (route.query.redirect as string) || '/kennisbank';
    router.push(redirect);
  } catch (err: any) {
    if (err.data?.errors) {
      error.value = Object.values(err.data.errors).flat().join(', ');
    } else {
      error.value = err.message || 'Login mislukt';
    }
  } finally {
    loading.value = false;
  }
}
</script>
