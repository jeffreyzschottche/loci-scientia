<template>
  <NuxtLayout name="auth">
    <div class="rounded-lg bg-white p-8 shadow">
      <h2 class="mb-6 text-center text-2xl font-bold">Login</h2>

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

        <div class="flex items-center justify-between">
          <NuxtLink to="/account/forgot-password" class="text-sm text-blue-600 hover:underline">
            Wachtwoord vergeten?
          </NuxtLink>
        </div>

        <p v-if="loginAttemptWarning" class="rounded border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">
          {{ loginAttemptWarning }}
        </p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {{ loading ? 'Aan het inloggen...' : 'Login' }}
        </button>
      </form>

      <p class="mt-4 text-center text-sm text-gray-600">
        Geen toegang? We hebben ook een mail gestuurd. Bekijk je mailbox en spammap om te controleren of je de uitnodiging misschien over het hoofd hebt gezien.
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
const router = useRouter();
const route = useRoute();

const form = reactive({
  email: '',
  password: '',
});

const error = ref('');
const loading = ref(false);
const loginAttemptWarning = ref('');

async function handleLogin() {
  error.value = '';
  loginAttemptWarning.value = '';
  loading.value = true;

  try {
    await authStore.login(form.email, form.password);
    const redirect = (route.query.redirect as string) || '/kennisbank';
    router.push(redirect);
  } catch (err: any) {
    if (err.data?.errors) {
      error.value = Object.values(err.data.errors).flat().join(', ');
    } else {
      error.value = err.message || 'Login failed';
    }

    loginAttemptWarning.value = buildAttemptWarning(err.data?.meta);
  } finally {
    loading.value = false;
  }
}

function buildAttemptWarning(meta?: { attempts: number; max_attempts: number; remaining: number; retry_after_seconds?: number | null }) {
  if (!meta || meta.attempts < 3) {
    return '';
  }

  if (meta.remaining <= 0) {
    return '5/5 gedaan. Probeer het na een uur weer.';
  }

  return `${meta.attempts}/${meta.max_attempts} gedaan, nog ${meta.remaining} ${meta.remaining === 1 ? 'poging' : 'pogingen'} over. Na 5 mislukte pogingen wordt inloggen voor een uur geblokkeerd.`;
}
</script>
