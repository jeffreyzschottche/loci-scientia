<template>
  <div class="mx-auto max-w-5xl px-4 py-12">
    <div class="space-y-6">
      <section class="rounded-lg bg-white p-8 shadow">
        <div class="mb-6 border-b pb-4">
          <h1 class="text-2xl font-semibold">Mijn account</h1>
          <p class="text-sm text-gray-500">Werk je profielgegevens bij en beheer je beveiliging.</p>
        </div>

        <form @submit.prevent="handleProfileSave" class="space-y-4">
          <div v-if="profileSuccess" class="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-700">
            {{ profileSuccess }}
          </div>
          <div v-if="profileError" class="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {{ profileError }}
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">Naam</label>
            <input
              v-model="profileForm.name"
              type="text"
              required
              class="w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">Email</label>
            <input
              v-model="profileForm.email"
              type="email"
              required
              class="w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p class="mt-1 text-xs text-gray-500">
              Bij het wijzigen van je email moet je deze opnieuw verifiëren via de knop hieronder.
            </p>
          </div>

          <button
            type="submit"
            :disabled="profileSaving"
            class="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {{ profileSaving ? 'Opslaan...' : 'Wijzigingen opslaan' }}
          </button>
        </form>
      </section>

      <section class="rounded-lg bg-white p-6 shadow">
        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p class="text-sm font-semibold text-gray-700">Email verificatie</p>
            <p class="text-sm" :class="emailVerified ? 'text-green-600' : 'text-yellow-600'">
              {{ emailVerified ? 'Je email is geverifieerd' : 'Nog niet geverifieerd' }}
            </p>
            <p class="mt-2 text-xs text-gray-500">
              Verificatie e-mails worden alleen vanaf hier opnieuw verstuurd. Klik op de link in de mail om de verificatie
              af te ronden.
            </p>
          </div>
          <div class="w-full md:w-auto">
            <button
              type="button"
              @click="handleResendVerification"
              :disabled="resendLoading || emailVerified"
              class="w-full rounded bg-yellow-600 px-4 py-2 text-white hover:bg-yellow-700 disabled:opacity-50 md:w-auto"
            >
              {{ emailVerified ? 'Alles up-to-date' : resendLoading ? 'Versturen...' : 'Verzend verificatie' }}
            </button>
          </div>
        </div>
        <p v-if="resendMessage" class="mt-2 text-sm text-green-600">{{ resendMessage }}</p>
        <p v-if="resendError" class="mt-2 text-sm text-red-600">{{ resendError }}</p>
      </section>

      <section class="rounded-lg bg-white p-8 shadow">
        <h2 class="mb-4 text-xl font-semibold">Wachtwoord wijzigen</h2>
        <form @submit.prevent="handlePasswordChange" class="space-y-4">
          <div v-if="passwordSuccess" class="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-700">
            {{ passwordSuccess }}
          </div>
          <div v-if="passwordError" class="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {{ passwordError }}
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">Huidig wachtwoord</label>
            <input
              v-model="passwordForm.current_password"
              type="password"
              required
              class="w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">Nieuw wachtwoord</label>
            <input
              v-model="passwordForm.password"
              type="password"
              required
              class="w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700">Bevestig wachtwoord</label>
            <input
              v-model="passwordForm.password_confirmation"
              type="password"
              required
              class="w-full rounded border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            :disabled="passwordSaving"
            class="w-full rounded bg-slate-800 py-2 text-white hover:bg-slate-900 disabled:opacity-50"
          >
            {{ passwordSaving ? 'Bijwerken...' : 'Wachtwoord wijzigen' }}
          </button>
        </form>
      </section>

      <section class="rounded-lg bg-white p-6 shadow">
        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 class="text-lg font-semibold">Wachtwoord vergeten</h3>
            <p class="text-sm text-gray-600">
              Verstuur een resetlink naar je huidige emailadres. Deze link verloopt binnen 60 minuten.
            </p>
          </div>
          <div class="w-full md:w-auto">
            <button
              type="button"
              @click="handleForgotPassword"
              :disabled="forgotSending"
              class="w-full rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600 disabled:opacity-50 md:w-auto"
            >
              {{ forgotSending ? 'Wordt verstuurd...' : 'Stuur resetlink' }}
            </button>
          </div>
        </div>
        <p v-if="forgotMessage" class="mt-2 text-sm text-green-600">{{ forgotMessage }}</p>
        <p v-if="forgotError" class="mt-2 text-sm text-red-600">{{ forgotError }}</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

definePageMeta({
  middleware: 'auth',
});

const authStore = useAuthStore();

const profileForm = reactive({
  name: authStore.user?.name || '',
  email: authStore.user?.email || '',
});

watch(
  () => authStore.user,
  (user) => {
    if (user) {
      profileForm.name = user.name;
      profileForm.email = user.email;
    }
  },
  { immediate: true }
);

const profileSaving = ref(false);
const profileSuccess = ref('');
const profileError = ref('');

async function handleProfileSave() {
  profileSaving.value = true;
  profileSuccess.value = '';
  profileError.value = '';

  try {
    const response = await authStore.updateProfile({
      name: profileForm.name,
      email: profileForm.email,
    });
    profileSuccess.value = response.message;
  } catch (error: any) {
    profileError.value = extractError(error) || 'Opslaan van profiel mislukt';
  } finally {
    profileSaving.value = false;
  }
}

const emailVerified = computed(() => Boolean(authStore.user?.email_verified_at));
const resendLoading = ref(false);
const resendMessage = ref('');
const resendError = ref('');

async function handleResendVerification() {
  if (emailVerified.value) {
    resendMessage.value = 'Je emailadres is al geverifieerd.';
    resendError.value = '';
    return;
  }

  resendLoading.value = true;
  resendMessage.value = '';
  resendError.value = '';

  try {
    const response = await authStore.resendVerification();
    resendMessage.value = response.message;
  } catch (error: any) {
    resendError.value = extractError(error) || 'Verificatie email versturen mislukt';
  } finally {
    resendLoading.value = false;
  }
}

const passwordForm = reactive({
  current_password: '',
  password: '',
  password_confirmation: '',
});
const passwordSaving = ref(false);
const passwordSuccess = ref('');
const passwordError = ref('');

async function handlePasswordChange() {
  passwordSaving.value = true;
  passwordSuccess.value = '';
  passwordError.value = '';

  try {
    const response = await authStore.changePassword({ ...passwordForm });
    passwordSuccess.value = response.message;
    passwordForm.current_password = '';
    passwordForm.password = '';
    passwordForm.password_confirmation = '';
  } catch (error: any) {
    passwordError.value = extractError(error) || 'Wijzigen van wachtwoord mislukt';
  } finally {
    passwordSaving.value = false;
  }
}

const forgotSending = ref(false);
const forgotMessage = ref('');
const forgotError = ref('');

async function handleForgotPassword() {
  if (!authStore.user?.email) {
    forgotError.value = 'Geen emailadres gevonden voor dit account.';
    return;
  }

  forgotSending.value = true;
  forgotMessage.value = '';
  forgotError.value = '';

  try {
    const response = await authStore.forgotPassword(authStore.user.email);
    forgotMessage.value = response.message;
  } catch (error: any) {
    forgotError.value = extractError(error) || 'Resetlink versturen mislukt';
  } finally {
    forgotSending.value = false;
  }
}

function extractError(error: any): string | undefined {
  if (error?.data?.errors) {
    return Object.values(error.data.errors).flat().join(', ');
  }

  return error?.data?.message || error?.message;
}
</script>
