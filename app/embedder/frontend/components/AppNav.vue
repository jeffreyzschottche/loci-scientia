<template>
  <nav class="bg-loci-white border-b border-loci-gray-100">
    <div class="mx-auto flex h-16 max-w-7xl items-center px-4 sm:px-6 lg:px-8">
      <!-- Logo - fixed width left -->
      <div class="w-32 flex-shrink-0">
        <NuxtLink :to="brandLink" class="flex items-center">
          <img src="/aitje.png" alt="Aitje" class="h-10" />
        </NuxtLink>
      </div>

      <!-- Navigation - centered -->
      <div class="flex min-w-0 flex-1 items-center justify-center space-x-2">
        <template v-if="authStore.isLoggedIn">
          <NuxtLink
            v-for="link in primaryLinks"
            :key="link.to"
            :to="link.to"
            class="rounded-full px-4 py-2 text-sm font-semibold transition-all"
            :class="isActiveRoute(link.to)
              ? 'bg-loci-yellow text-loci-black-deep'
              : 'text-loci-black hover:bg-loci-yellow/10'"
          >
            {{ link.label }}
          </NuxtLink>
        </template>
        <p v-else class="truncate px-2 text-center text-sm font-bold text-loci-black sm:text-xl">
          Kennisbank Management
        </p>
      </div>

      <!-- User info - right aligned -->
      <div class="flex items-center justify-end space-x-4">
        <template v-if="authStore.isLoggedIn">
          <div class="flex items-center space-x-4">
            <div class="relative" ref="languageMenuRef">
              <button
                type="button"
                class="flex items-center gap-2 rounded-full border border-loci-gray-200 bg-loci-white px-3 py-1.5 text-xs font-semibold uppercase text-loci-black shadow-sm transition-all hover:border-loci-yellow hover:bg-loci-yellow/20"
                @click.stop="toggleLanguageMenu"
                :aria-expanded="isLanguageMenuOpen ? 'true' : 'false'"
                aria-haspopup="listbox"
                :aria-label="translate('Taal selecteren', 'Select language')"
              >
                <span class="text-lg leading-none" aria-hidden="true">{{ currentLanguageOption.emoji }}</span>
                <span>{{ currentLanguageOption.shortLabel }}</span>
                <svg
                  class="h-3 w-3 text-loci-gray-500 transition-transform"
                  :class="isLanguageMenuOpen ? 'rotate-180' : ''"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <path d="M5 7l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>

              <transition name="fade-scale">
                <div
                  v-if="isLanguageMenuOpen"
                  class="absolute left-0 z-50 mt-2 w-44 rounded-loci-lg border border-loci-gray-100 bg-loci-white p-2 shadow-xl"
                  role="listbox"
                >
                  <button
                    v-for="option in languageOptions"
                    :key="option.code"
                    class="flex w-full items-center gap-3 rounded-loci px-3 py-2 text-sm transition hover:bg-loci-yellow/10"
                    :class="option.code === currentLanguage ? 'text-loci-black font-semibold' : 'text-loci-gray-600'"
                    type="button"
                    role="option"
                    :aria-selected="option.code === currentLanguage ? 'true' : 'false'"
                    @click.stop="selectLanguage(option.code)"
                  >
                    <span class="text-lg leading-none" aria-hidden="true">{{ option.emoji }}</span>
                    <div class="flex-1 text-left">
                      <p>{{ option.label }}</p>
                      <p class="text-xs text-loci-gray-400">{{ option.subLabel }}</p>
                    </div>
                    <svg
                      v-if="option.code === currentLanguage"
                      class="h-4 w-4 text-loci-yellow"
                      viewBox="0 0 20 20"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path d="M16 6l-7 7-3-3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </button>
                </div>
              </transition>
            </div>
            <span class="text-sm text-loci-gray-500">
              <i>{{ translate('ingelogd als:', 'logged in as:') }}</i>
              <b class="text-loci-black">{{ authStore.user?.name || translate('onbekend', 'unknown') }}</b>
            </span>
            <button
              v-if="authStore.adminImpersonating"
              @click="returnToAdmin"
              class="rounded-full bg-loci-yellow px-4 py-2 text-sm font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover"
            >
              {{ translate('Terug naar admin', 'Back to admin') }}
            </button>
            <button
              @click="handleLogout"
              class="rounded-full border border-loci-gray-200 bg-loci-white px-4 py-2 text-sm font-semibold text-loci-black transition-all hover:border-loci-yellow hover:bg-loci-yellow hover:text-loci-black-deep"
            >
              {{ translate('Uitloggen', 'Logout') }}
            </button>
          </div>
        </template>
        <template v-else>
          <div class="flex items-center space-x-4">
            <NuxtLink
              class="rounded-full bg-loci-yellow px-6 py-2 text-sm font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover"
              to="/"
            >
              {{ translate('Inloggen', 'Login') }}
            </NuxtLink>
          </div>
        </template>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();
const { currentLanguage, setLanguage, translate } = useTranslations();
const kennisbankLabel = computed(() => translate('Kennisbank', 'Knowledge Bank'));
const accountLabel = computed(() => translate('Mijn Account', 'My Account'));

type LanguageCode = 'nl' | 'en';

const languageOptions: Array<{ code: LanguageCode; label: string; subLabel: string; emoji: string; shortLabel: string }> = [
  { code: 'nl', label: 'Nederlands', subLabel: 'NL', emoji: '🇳🇱', shortLabel: 'NL' },
  { code: 'en', label: 'English', subLabel: 'EN', emoji: '🇬🇧', shortLabel: 'EN' },
];

const primaryLinks = computed(() => {
  return [
    { to: '/kennisbank', label: kennisbankLabel.value },
    { to: '/account', label: accountLabel.value },
  ];
});

const brandLink = computed(() => (authStore.isLoggedIn ? '/kennisbank' : '/'));

const currentLanguageOption = computed(() => {
  return languageOptions.find(option => option.code === currentLanguage.value) || languageOptions[0];
});

const isLanguageMenuOpen = ref(false);
const languageMenuRef = ref<HTMLElement | null>(null);

function isActiveRoute(path: string) {
  if (path === '/kennisbank') {
    return route.path.startsWith('/kennisbank');
  }
  return route.path === path;
}

function toggleLanguageMenu() {
  isLanguageMenuOpen.value = !isLanguageMenuOpen.value;
}

function selectLanguage(lang: LanguageCode) {
  if (currentLanguage.value !== lang) {
    setLanguage(lang);
  }
  isLanguageMenuOpen.value = false;
}

function handleOutsideClick(event: MouseEvent) {
  if (!isLanguageMenuOpen.value) return;
  if (!languageMenuRef.value) return;
  if (!languageMenuRef.value.contains(event.target as Node)) {
    isLanguageMenuOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener('click', handleOutsideClick);

  if (typeof document !== 'undefined') {
    document.documentElement.lang = currentLanguage.value;
  }
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick);
});

watch(
  () => currentLanguage.value,
  lang => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = lang;
    }
  },
);

async function handleLogout() {
  try {
    const api = useApi();
    await api.post('/logout');
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    authStore.logout();
    router.push('/');
  }
}

function returnToAdmin() {
  authStore.logout();
  router.push('/admin/cms');
}
</script>

<style scoped>
.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}
</style>
