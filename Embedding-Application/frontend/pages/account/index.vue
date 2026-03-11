<template>
  <div class="mx-auto max-w-5xl px-4 py-12">
    <div class="space-y-6">
      <section class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
        <div class="mb-6 border-b border-loci-gray-100 pb-4">
          <h1 class="text-2xl font-semibold text-loci-black">
            {{ translate('Mijn account', 'My Account') }}
          </h1>
          <p class="text-sm text-loci-gray-500">
            {{ translate('Werk je profielgegevens bij en beheer je beveiliging.', 'Update your profile details and manage your security settings.') }}
          </p>
        </div>

        <form @submit.prevent="handleProfileSave" class="space-y-4">
          <div v-if="profileSuccess" class="rounded-loci border border-green-200 bg-green-50 p-3 text-sm text-green-700">
            {{ profileSuccess }}
          </div>
          <div v-if="profileError" class="rounded-loci border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {{ profileError }}
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-loci-black">
              {{ translate('Naam', 'Name') }}
            </label>
            <input
              v-model="profileForm.name"
              type="text"
              required
              class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-loci-black">
              {{ translate('Email', 'Email') }}
            </label>
            <input
              v-model="profileForm.email"
              type="email"
              required
              class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            />
            <p class="mt-1 text-xs text-loci-gray-500">
              {{ translate('Bij het wijzigen van je email moet je deze opnieuw verifiëren via de knop hieronder.', 'Changing your email requires re-verification via the button below.') }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="profileSaving"
            class="w-full rounded-loci-full bg-loci-yellow py-3 font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
          >
            {{ profileSaving ? translate('Opslaan...', 'Saving...') : translate('Wijzigingen opslaan', 'Save changes') }}
          </button>
        </form>
      </section>

      <section class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-6">
        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p class="text-sm font-semibold text-loci-black">
              {{ translate('Email verificatie', 'Email verification') }}
            </p>
            <p class="text-sm" :class="emailVerified ? 'text-green-600' : 'text-loci-yellow-hover'">
              {{ emailVerified ? translate('Je email is geverifieerd', 'Your email is verified') : translate('Nog niet geverifieerd', 'Not verified yet') }}
            </p>
            <p class="mt-2 text-xs text-loci-gray-500">
              {{ translate('Verificatie e-mails worden alleen vanaf hier opnieuw verstuurd. Klik op de link in de mail om de verificatie af te ronden.', 'Verification emails can only be resent from here. Click the link in the message to finish verification.') }}
            </p>
          </div>
          <div class="w-full md:w-auto">
            <button
              type="button"
              @click="handleResendVerification"
              :disabled="resendLoading || emailVerified"
              class="w-full rounded-full border border-loci-gray-200 bg-loci-white px-4 py-2 font-semibold text-loci-black transition-all hover:border-loci-yellow hover:bg-loci-yellow hover:text-loci-black-deep disabled:bg-loci-gray-50 disabled:text-loci-gray-400 md:w-auto"
            >
              {{ emailVerified ? translate('Alles up-to-date', 'All set') : resendLoading ? translate('Versturen...', 'Sending...') : translate('Verzend verificatie', 'Send verification') }}
            </button>
          </div>
        </div>
        <p v-if="resendMessage" class="mt-2 text-sm text-green-600">{{ resendMessage }}</p>
        <p v-if="resendError" class="mt-2 text-sm text-red-600">{{ resendError }}</p>
      </section>

      <section class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
        <h2 class="mb-4 text-xl font-semibold text-loci-black">
          {{ translate('Wachtwoord wijzigen', 'Change password') }}
        </h2>
        <form @submit.prevent="handlePasswordChange" class="space-y-4">
          <div v-if="passwordSuccess" class="rounded-loci border border-green-200 bg-green-50 p-3 text-sm text-green-700">
            {{ passwordSuccess }}
          </div>
          <div v-if="passwordError" class="rounded-loci border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {{ passwordError }}
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-loci-black">
              {{ translate('Huidig wachtwoord', 'Current password') }}
            </label>
            <input
              v-model="passwordForm.current_password"
              type="password"
              required
              class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-loci-black">
              {{ translate('Nieuw wachtwoord', 'New password') }}
            </label>
            <input
              v-model="passwordForm.password"
              type="password"
              required
              class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            />
          </div>

          <div>
            <label class="mb-1 block text-sm font-medium text-loci-black">
              {{ translate('Bevestig wachtwoord', 'Confirm password') }}
            </label>
            <input
              v-model="passwordForm.password_confirmation"
              type="password"
              required
              class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            />
          </div>

          <button
            type="submit"
            :disabled="passwordSaving"
            class="w-full rounded-loci-full bg-loci-black py-3 font-semibold text-loci-white transition-all hover:bg-loci-black-deep disabled:bg-loci-gray-400 disabled:text-loci-gray-200"
          >
            {{ passwordSaving ? translate('Bijwerken...', 'Updating...') : translate('Wachtwoord wijzigen', 'Update password') }}
          </button>
        </form>
      </section>

      <section class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-6">
        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 class="text-lg font-semibold text-loci-black">
              {{ translate('Wachtwoord vergeten', 'Forgot password') }}
            </h3>
            <p class="text-sm text-loci-gray-500">
              {{ translate('Verstuur een resetlink naar je huidige emailadres. Deze link verloopt binnen 60 minuten.', 'Send a reset link to your current email address. The link expires after 60 minutes.') }}
            </p>
          </div>
          <div class="w-full md:w-auto">
            <button
              type="button"
              @click="handleForgotPassword"
              :disabled="forgotSending"
              class="w-full rounded-full border border-loci-gray-200 bg-loci-white px-4 py-2 font-semibold text-loci-black transition-all hover:border-loci-yellow hover:bg-loci-yellow hover:text-loci-black-deep disabled:bg-loci-gray-50 disabled:text-loci-gray-400 md:w-auto"
            >
              {{ forgotSending ? translate('Wordt verstuurd...', 'Sending...') : translate('Stuur resetlink', 'Send reset link') }}
            </button>
          </div>
        </div>
        <p v-if="forgotMessage" class="mt-2 text-sm text-green-600">{{ forgotMessage }}</p>
        <p v-if="forgotError" class="mt-2 text-sm text-red-600">{{ forgotError }}</p>
      </section>

      <!-- Git Configuration -->
      <section class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
        <div class="flex flex-col md:flex-row md:items-start md:justify-between mb-6">
          <div>
            <h2 class="text-xl font-semibold text-loci-black">
              {{ translate('Git Configuratie', 'Git configuration') }}
            </h2>
            <p class="text-sm text-loci-gray-500">
              {{ translate('Stel de GitHub repo in voor de Sync to OS actie.', 'Configure the GitHub repo for the Sync to OS action.') }}
            </p>
          </div>
          <div class="text-sm text-loci-gray-500 mt-2 md:mt-0">
            {{ translate('Laatst gesynchroniseerd:', 'Last synced:') }}
            <span class="font-medium text-loci-black">
              {{ gitConfig.last_pushed_at ? formatDateTime(gitConfig.last_pushed_at) : translate('Nooit', 'Never') }}
            </span>
          </div>
        </div>

        <div
          v-if="gitStatus"
          class="mb-6 p-4 rounded-loci border"
          :class="gitStatus.type === 'error'
            ? 'bg-red-50 border-red-200 text-red-700'
            : gitStatus.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-700'
              : 'bg-loci-yellow/10 border-loci-yellow text-loci-black'"
        >
          {{ gitStatus.message }}
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-loci-black">
              {{ translate('Repository URL', 'Repository URL') }}
            </label>
            <input
              v-model="gitConfig.repo_url"
              type="text"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              placeholder="https://github.com/naam/kennisbank.git"
            >
          </div>

          <div>
            <label class="block text-sm font-medium text-loci-black">
              {{ translate('Branch', 'Branch') }}
            </label>
            <input
              v-model="gitConfig.branch"
              type="text"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              placeholder="main"
            >
          </div>

          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-loci-black">
              {{ translate('Access Token', 'Access token') }}
            </label>
            <input
              v-model="gitConfig.access_token"
              type="password"
              class="mt-1 block w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
              placeholder="ghp_xxxxxxxxx"
            >
            <p class="text-xs text-loci-gray-500 mt-1">
              {{ translate('Personal Access Token met repo permissions. Wordt versleuteld opgeslagen.', 'Personal Access Token with repo permissions. Stored encrypted.') }}
            </p>
          </div>
        </div>

        <div class="flex flex-col sm:flex-row justify-end gap-3 mt-6">
          <button
            type="button"
            class="px-6 py-3 bg-loci-black text-loci-white rounded-loci-full font-semibold hover:bg-loci-black-deep transition-all disabled:bg-loci-gray-400 disabled:text-loci-gray-200"
            :disabled="savingGitConfig || !gitConfig.repo_url || !gitConfig.branch"
            @click="saveGitConfig"
          >
            {{ savingGitConfig ? translate('Opslaan...', 'Saving...') : translate('Configuratie opslaan', 'Save configuration') }}
          </button>
          <button
            type="button"
            class="px-6 py-3 bg-loci-yellow text-loci-black-deep rounded-loci-full font-semibold hover:bg-loci-yellow-hover transition-all disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
            :disabled="syncing || !hasGitConfig"
            @click="syncToGit"
          >
            {{ syncing ? translate('Synchroniseren...', 'Syncing...') : translate('Sync naar Git', 'Sync to Git') }}
          </button>
        </div>
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
const api = useApi();
const { translate, currentLanguage } = useTranslations();

type GitConfigState = {
  repo_url: string;
  branch: string;
  access_token: string;
  has_access_token: boolean;
  last_pushed_at: string | null;
};

type StatusState = {
  type: 'success' | 'error' | 'info';
  message: string;
};

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
    profileError.value = extractError(error) || translate('Opslaan van profiel mislukt', 'Failed to save profile');
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
    resendMessage.value = translate('Je emailadres is al geverifieerd.', 'Your email address is already verified.');
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
    resendError.value = extractError(error) || translate('Verificatie email versturen mislukt', 'Failed to send verification email');
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
    passwordError.value = extractError(error) || translate('Wijzigen van wachtwoord mislukt', 'Failed to change password');
  } finally {
    passwordSaving.value = false;
  }
}

const forgotSending = ref(false);
const forgotMessage = ref('');
const forgotError = ref('');

async function handleForgotPassword() {
  if (!authStore.user?.email) {
    forgotError.value = translate('Geen emailadres gevonden voor dit account.', 'No email address found for this account.');
    return;
  }

  forgotSending.value = true;
  forgotMessage.value = '';
  forgotError.value = '';

  try {
    const response = await authStore.forgotPassword(authStore.user.email);
    forgotMessage.value = response.message;
  } catch (error: any) {
    forgotError.value = extractError(error) || translate('Resetlink versturen mislukt', 'Failed to send reset link');
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

// Git Configuration
const gitConfig = ref<GitConfigState>({
  repo_url: '',
  branch: 'main',
  access_token: '',
  has_access_token: false,
  last_pushed_at: null,
});
const savingGitConfig = ref(false);
const syncing = ref(false);
const gitStatus = ref<StatusState | null>(null);

const hasGitConfig = computed(() => {
  return Boolean(
    gitConfig.value.repo_url &&
      gitConfig.value.branch &&
      (gitConfig.value.has_access_token || gitConfig.value.access_token)
  );
});

onMounted(async () => {
  await loadGitConfig();
});

async function loadGitConfig() {
  try {
    const response = await api.get<{ config: (GitConfigState & { has_access_token: boolean }) | null }>('/kennisbank/git-config');

    if (response.config) {
      gitConfig.value = {
        repo_url: response.config.repo_url || '',
        branch: response.config.branch || 'main',
        access_token: '',
        has_access_token: Boolean(response.config.has_access_token),
        last_pushed_at: response.config.last_pushed_at || null,
      };
    }
  } catch (e) {
    console.error('Failed to load git config:', e);
  }
}

async function saveGitConfig() {
  try {
    savingGitConfig.value = true;
    gitStatus.value = null;

    const payload: Record<string, string> = {
      repo_url: gitConfig.value.repo_url,
      branch: gitConfig.value.branch || 'main',
    };

    if (gitConfig.value.access_token) {
      payload.access_token = gitConfig.value.access_token;
    }

    const response = await api.post<{ config: GitConfigState; message: string }>('/kennisbank/git-config', payload);
    gitConfig.value.has_access_token = response.config.has_access_token ?? Boolean(payload.access_token);
    gitConfig.value.last_pushed_at = response.config.last_pushed_at || gitConfig.value.last_pushed_at;
    gitConfig.value.access_token = '';

    gitStatus.value = { type: 'success', message: translate('Configuratie opgeslagen', 'Configuration saved') };
  } catch (e: any) {
    gitStatus.value = { type: 'error', message: extractError(e) || translate('Opslaan mislukt', 'Save failed') };
  } finally {
    savingGitConfig.value = false;
  }
}

async function syncToGit() {
  if (!hasGitConfig.value) {
    gitStatus.value = { type: 'error', message: translate('Configureer eerst de git instellingen', 'Configure your Git settings first') };
    return;
  }

  try {
    syncing.value = true;
    gitStatus.value = { type: 'info', message: translate('Synchroniseren...', 'Syncing...') };
    const response = await api.post<{ message: string; last_pushed_at: string | null }>('/kennisbank/push');
    gitConfig.value.last_pushed_at = response.last_pushed_at;
    gitStatus.value = {
      type: 'success',
      message: response.message || translate('Sync voltooid', 'Sync completed'),
    };
  } catch (e: any) {
    gitStatus.value = { type: 'error', message: extractError(e) || translate('Sync mislukt', 'Sync failed') };
  } finally {
    syncing.value = false;
  }
}

function formatDateTime(dateStr: string) {
  const date = new Date(dateStr);
  const locale = currentLanguage.value === 'en' ? 'en-US' : 'nl-NL';
  return `${date.toLocaleDateString(locale)} ${date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })}`;
}
</script>
