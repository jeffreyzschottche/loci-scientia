<template>
  <nav class="bg-white shadow">
    <div class="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
      <NuxtLink :to="brandLink" class="text-xl font-bold">Embedding Platform</NuxtLink>

      <div class="flex items-center space-x-6">
        <NuxtLink
          v-for="link in primaryLinks"
          :key="link.to"
          :to="link.to"
          class="text-sm font-medium text-gray-700 transition hover:text-blue-600"
        >
          {{ link.label }}
        </NuxtLink>
      </div>

      <div class="flex items-center space-x-4">
        <template v-if="authStore.isLoggedIn">
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-700">
              Ingelogd als : {{ authStore.user?.name || 'onbekend' }}
            </span>
            <button
              @click="handleLogout"
              class="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
            >
              Logout
            </button>
          </div>
        </template>
        <template v-else>
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-500">Niet ingelogd</span>
            <NuxtLink
              class="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              to="/"
            >
              Login
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
const kennisbankLabel = 'Kennisbank';
const accountLabel = 'Mijn Account';

const primaryLinks = computed(() => {
  if (authStore.isLoggedIn) {
    return [
      { to: '/kennisbank', label: kennisbankLabel },
      { to: '/account', label: accountLabel },
    ];
  }

  return [
    { to: '/', label: 'Login' },
    { to: '/register', label: 'Register' },
  ];
});

const brandLink = computed(() => (authStore.isLoggedIn ? '/kennisbank' : '/'));

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
</script>
