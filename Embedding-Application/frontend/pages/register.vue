<template>
  <NuxtLayout name="auth">
    <div class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
      <h2 class="mb-6 text-center text-2xl font-bold text-loci-black">Account aanmaken</h2>

      <form @submit.prevent="handleRegister" class="space-y-4">
        <div v-if="error" class="rounded-loci border border-red-200 bg-red-50 p-3 text-red-600">
          {{ error }}
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-loci-black">Naam</label>
          <input
            v-model="form.name"
            type="text"
            required
            class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
          />
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
          {{ loading ? 'Account aanmaken...' : 'Registreren' }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-loci-gray-500">
        Heb je al een account?
        <NuxtLink to="/login" class="font-semibold text-loci-black hover:text-loci-yellow-hover">
          Login hier
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
const router = useRouter();

const form = reactive({
  name: '',
  email: '',
  password: '',
  password_confirmation: '',
});

const error = ref('');
const loading = ref(false);

async function handleRegister() {
  error.value = '';
  loading.value = true;

  try {
    await authStore.register(
      form.name,
      form.email,
      form.password,
      form.password_confirmation
    );
    router.push('/kennisbank');
  } catch (err: any) {
    if (err.data?.errors) {
      error.value = Object.values(err.data.errors).flat().join(', ');
    } else {
      error.value = err.message || 'Registration failed';
    }
  } finally {
    loading.value = false;
  }
}
</script>
