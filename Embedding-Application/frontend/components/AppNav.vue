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
      <div class="flex flex-1 items-center justify-center space-x-2">
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
      </div>

      <!-- User info - right aligned -->
      <div class="flex items-center justify-end space-x-4">
        <template v-if="authStore.isLoggedIn">
          <div class="flex items-center space-x-4">
            <span class="text-sm text-loci-gray-500">
              <i>ingelogd als:</i> <b class="text-loci-black">{{ authStore.user?.name || 'onbekend' }}</b>
            </span>
            <button
              @click="handleLogout"
              class="rounded-full border border-loci-gray-200 bg-loci-white px-4 py-2 text-sm font-semibold text-loci-black transition-all hover:border-loci-yellow hover:bg-loci-yellow hover:text-loci-black-deep"
            >
              Logout
            </button>
          </div>
        </template>
        <template v-else>
          <div class="flex items-center space-x-4">
            <NuxtLink
              class="rounded-full bg-loci-yellow px-6 py-2 text-sm font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover"
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
const route = useRoute();
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

function isActiveRoute(path: string) {
  if (path === '/kennisbank') {
    return route.path.startsWith('/kennisbank');
  }
  return route.path === path;
}

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
