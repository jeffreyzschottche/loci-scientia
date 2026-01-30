<template>
  <nav class="bg-white shadow">
    <div class="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
      <NuxtLink to="/" class="text-xl font-bold">Starter Kit</NuxtLink>

      <div class="flex items-center space-x-4">
        <NuxtLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="text-sm text-gray-700 transition hover:text-blue-600"
        >
          {{ link.label }}
        </NuxtLink>
      </div>

      <div class="flex items-center space-x-4">
        <template v-if="authStore.isLoggedIn">
          <span class="text-sm text-gray-700">{{ authStore.user?.name }}</span>
          <button
            @click="handleLogout"
            class="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
          >
            Logout
          </button>
        </template>
        <template v-else>
          <span class="text-sm text-gray-500">{{ t('not_logged_in') }}</span>
        </template>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
const authStore = useAuthStore();
const router = useRouter();
const { t } = useTranslations();

const navLinks = computed(() => [
  { to: '/', label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/kennisbank', label: t('kennisbank') },
  { to: '/login', label: 'Login' },
  { to: '/register', label: 'Register' },
  { to: '/forgot-password', label: 'Forgot Password' },
  { to: '/reset-password', label: 'Reset Password' },
  { to: '/verify-email', label: 'Verify Email' },
]);

async function handleLogout() {
  try {
    const api = useApi();
    await api.post('/logout');
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    authStore.logout();
    router.push('/login');
  }
}
</script>
