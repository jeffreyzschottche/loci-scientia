<template>
  <div class="min-h-screen bg-loci-gray-50">
    <AppNav />

    <main class="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <section v-if="!adminToken" class="mx-auto max-w-md rounded-loci-lg border border-loci-gray-100 bg-loci-white p-8">
        <h1 class="text-center text-3xl font-bold text-loci-black">Admin CMS</h1>
        <p class="mt-3 text-center text-sm text-loci-gray-500">
          Log in met de admin-gegevens uit de serveromgeving.
        </p>

        <form class="mt-8 space-y-4" @submit.prevent="loginAdmin">
          <div v-if="adminError" class="rounded-loci border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {{ adminError }}
          </div>

          <div>
            <label class="mb-1 block text-sm font-semibold text-loci-black">Email</label>
            <input
              v-model="adminForm.email"
              type="email"
              required
              class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            >
          </div>

          <div>
            <label class="mb-1 block text-sm font-semibold text-loci-black">Wachtwoord</label>
            <input
              v-model="adminForm.password"
              type="password"
              required
              class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 text-loci-black focus:border-loci-yellow focus:outline-none"
            >
          </div>

          <button
            type="submit"
            :disabled="adminLoading"
            class="w-full rounded-loci-full bg-loci-yellow py-3 font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
          >
            {{ adminLoading ? 'Inloggen...' : 'Admin login' }}
          </button>
        </form>
      </section>

      <div v-else class="space-y-6">
        <div class="flex flex-col gap-4 border-b border-loci-gray-100 pb-6 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 class="text-3xl font-bold text-loci-black">Admin CMS</h1>
            <p class="mt-1 text-sm text-loci-gray-500">
              Beheer klantaccounts, GitHub-koppelingen en toegang.
            </p>
          </div>
          <button
            type="button"
            class="rounded-loci-full border border-loci-gray-200 bg-loci-white px-5 py-2 text-sm font-semibold text-loci-black transition-all hover:border-loci-yellow hover:bg-loci-yellow"
            @click="logoutAdmin"
          >
            Admin uitloggen
          </button>
        </div>

        <section class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-6">
          <h2 class="text-xl font-semibold text-loci-black">Klantaccount aanmaken</h2>
          <form class="mt-4 grid gap-4 md:grid-cols-2" @submit.prevent="createUser">
            <div v-if="createMessage" class="rounded-loci border border-green-200 bg-green-50 p-3 text-sm text-green-700 md:col-span-2">
              {{ createMessage }}
            </div>
            <div v-if="createError" class="rounded-loci border border-red-200 bg-red-50 p-3 text-sm text-red-700 md:col-span-2">
              {{ createError }}
            </div>

            <div>
              <label class="mb-1 block text-sm font-semibold text-loci-black">Bedrijfsnaam</label>
              <input v-model="createForm.name" required class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 focus:border-loci-yellow focus:outline-none">
            </div>
            <div>
              <label class="mb-1 block text-sm font-semibold text-loci-black">Email</label>
              <input v-model="createForm.email" type="email" required class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 focus:border-loci-yellow focus:outline-none">
            </div>
            <div>
              <label class="mb-1 block text-sm font-semibold text-loci-black">Tijdelijk wachtwoord</label>
              <input v-model="createForm.password" type="password" required class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 focus:border-loci-yellow focus:outline-none">
            </div>
            <div>
              <label class="mb-1 block text-sm font-semibold text-loci-black">Bevestig wachtwoord</label>
              <input v-model="createForm.password_confirmation" type="password" required class="w-full rounded-loci border border-loci-gray-300 bg-loci-cream px-4 py-3 focus:border-loci-yellow focus:outline-none">
            </div>
            <div class="md:col-span-2">
              <button
                type="submit"
                :disabled="creating"
                class="rounded-loci-full bg-loci-yellow px-6 py-3 font-semibold text-loci-black-deep transition-all hover:bg-loci-yellow-hover disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
              >
                {{ creating ? 'Aanmaken...' : 'Account aanmaken' }}
              </button>
            </div>
          </form>
        </section>

        <section class="space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-semibold text-loci-black">Klantaccounts</h2>
            <button
              type="button"
              class="rounded-loci-full border border-loci-gray-200 bg-loci-white px-4 py-2 text-sm font-semibold text-loci-black hover:border-loci-yellow hover:bg-loci-yellow"
              @click="loadUsers"
            >
              Verversen
            </button>
          </div>

          <div v-if="usersError" class="rounded-loci border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {{ usersError }}
          </div>

          <article
            v-for="user in users"
            :key="user.id"
            class="rounded-loci-lg border border-loci-gray-100 bg-loci-white p-6"
          >
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h3 class="text-lg font-semibold text-loci-black">{{ user.name }}</h3>
                <p class="text-sm text-loci-gray-500">{{ user.email }}</p>
                <div class="mt-3 flex flex-wrap gap-2 text-xs font-semibold">
                  <span class="rounded-full bg-loci-cream px-3 py-1 text-loci-black">
                    {{ user.documents_count }} documenten
                  </span>
                </div>
              </div>

              <button
                type="button"
                class="rounded-loci-full bg-loci-black px-5 py-2 text-sm font-semibold text-loci-white transition-all hover:bg-loci-black-deep"
                @click="impersonate(user)"
              >
                Bekijk als gebruiker
              </button>
            </div>
          </article>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { apiFetch } from '~/services/apiFetch';
import type { User } from '~/types/User';

definePageMeta({
  layout: false,
});

type AdminUser = User & {
  documents_count: number;
};

const router = useRouter();
const authStore = useAuthStore();

const adminToken = ref('');
const adminLoading = ref(false);
const adminError = ref('');
const users = ref<AdminUser[]>([]);
const usersError = ref('');
const creating = ref(false);
const createMessage = ref('');
const createError = ref('');

const adminForm = reactive({
  email: '',
  password: '',
});

const createForm = reactive({
  name: '',
  email: '',
  password: '',
  password_confirmation: '',
});

onMounted(async () => {
  adminToken.value = localStorage.getItem('admin_token') || '';
  if (adminToken.value) {
    await loadUsers();
  }
});

async function adminRequest<T>(endpoint: string, options: RequestInit = {}) {
  return apiFetch<T>(endpoint, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      Authorization: `Bearer ${adminToken.value}`,
      ...(options.headers as Record<string, string> | undefined),
    },
  });
}

async function loginAdmin() {
  adminLoading.value = true;
  adminError.value = '';

  try {
    const response = await apiFetch<{ token: string; admin: { email: string } }>('/admin/login', {
      method: 'POST',
      body: JSON.stringify(adminForm),
    });

    adminToken.value = response.token;
    localStorage.setItem('admin_token', response.token);
    adminForm.password = '';
    await loadUsers();
  } catch (error: any) {
    adminError.value = extractError(error) || 'Admin login mislukt';
  } finally {
    adminLoading.value = false;
  }
}

async function logoutAdmin() {
  try {
    await adminRequest('/admin/logout', { method: 'POST' });
  } catch {
    //
  } finally {
    adminToken.value = '';
    localStorage.removeItem('admin_token');
    users.value = [];
  }
}

async function loadUsers() {
  usersError.value = '';

  try {
    const response = await adminRequest<{ users: AdminUser[] }>('/admin/users');
    users.value = response.users.map(hydrateUser);
  } catch (error: any) {
    if (error.status === 401) {
      adminToken.value = '';
      localStorage.removeItem('admin_token');
    }
    usersError.value = extractError(error) || 'Klantaccounts laden mislukt';
  }
}

async function createUser() {
  creating.value = true;
  createMessage.value = '';
  createError.value = '';

  try {
    const response = await adminRequest<{ message: string; user: AdminUser }>('/admin/users', {
      method: 'POST',
      body: JSON.stringify(createForm),
    });

    users.value.unshift(hydrateUser(response.user));
    createMessage.value = response.message;
    createForm.name = '';
    createForm.email = '';
    createForm.password = '';
    createForm.password_confirmation = '';
  } catch (error: any) {
    createError.value = extractError(error) || 'Klantaccount aanmaken mislukt';
  } finally {
    creating.value = false;
  }
}

async function impersonate(user: AdminUser) {
  const response = await adminRequest<{ token: string; user: User }>(`/admin/users/${user.id}/impersonate`, {
    method: 'POST',
  });

  authStore.setSession(response.token, response.user);
  authStore.setAdminImpersonation(true);
  router.push('/kennisbank');
}

function hydrateUser(user: AdminUser): AdminUser {
  return { ...user };
}

function extractError(error: any): string | undefined {
  if (error?.data?.errors) {
    return Object.values(error.data.errors).flat().join(', ');
  }

  return error?.data?.message || error?.message;
}
</script>
