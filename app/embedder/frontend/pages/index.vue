<template>
  <div class="min-h-screen bg-loci-gray-50">
    <AppNav />
    <div class="flex items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
      <div class="w-full max-w-md rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
        <h1 class="mb-6 text-center text-3xl font-bold text-loci-black">Login</h1>
        <p class="mb-8 text-center text-sm text-loci-gray-500">
          Log in met het bedrijfsaccount dat door Aitje is aangemaakt.
        </p>

        <form @submit.prevent="handleLogin" class="space-y-4">
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
            <label class="mb-1 block text-sm font-medium text-loci-black">Wachtwoord</label>
            <input
              v-model="form.password"
              type="password"
              required
              class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            />
          </div>

          <div class="flex items-center justify-between text-sm">
            <NuxtLink to="/account/forgot-password" class="text-loci-gray-500 hover:text-loci-black">
              Wachtwoord vergeten?
            </NuxtLink>
          </div>

          <p v-if="loginAttemptWarning" class="rounded-loci border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">
            {{ loginAttemptWarning }}
          </p>

          <button
            type="submit"
            :disabled="loading"
            class="w-full rounded-loci-full bg-loci-yellow py-3 font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
          >
            {{ loading ? 'Aan het inloggen...' : 'Login' }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-loci-gray-500">
          Geen toegang? We hebben ook een mail gestuurd. Bekijk je mailbox en spammap om te controleren of je de uitnodiging misschien over het hoofd hebt gezien.
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
      error.value = err.message || 'Login mislukt';
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
