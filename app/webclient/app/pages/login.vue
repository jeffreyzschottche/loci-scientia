<template>
  <div class="min-h-screen bg-gray-50 flex justify-center px-4 pt-12 pb-8 relative overflow-y-auto md:items-center md:pt-4">
    <div
      class="absolute right-4 z-20"
      :class="isNativeMobileApp ? 'top-[calc(env(safe-area-inset-top)+0.5rem)]' : 'top-4'"
    >
      <LanguageSwitcher />
    </div>
    <div class="max-w-md w-full">
      <div class="text-center mb-8">
        <img src="/aitje-logox.png" alt="AITJE" class="mx-auto" style="width: 200px; height: 125px;" />
        <p class="text-gray-600">{{ t('common.tagline') }}</p>
        <p v-if="authStore.deviceNumber" class="text-sm text-gray-500 mt-2">
          {{ t('login.connectedWith', { device: authStore.deviceNumber }) }}
        </p>
      </div>

      <div class="bg-white rounded-lg shadow-md p-8">
        <h2 class="text-xl font-semibold text-gray-900 mb-2">
          {{ t('login.title') }}
        </h2>
        <p class="text-sm text-gray-600 mb-6">
          {{ t('login.connectTo', { url: baseUrlDisplay }) }}
        </p>

        <form @submit.prevent="handleLogin">
          <div class="mb-4">
            <label for="username" class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('login.username') }}
            </label>
            <input
              id="username"
              v-model="username"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 outline-none"
              required
              autofocus
            />
          </div>

          <div class="mb-6">
            <label for="password" class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('login.password') }}
            </label>
            <input
              id="password"
              v-model="password"
              type="password"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 outline-none"
              required
            />
          </div>

          <div v-if="error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p class="text-sm font-medium text-red-800 mb-2">{{ t('login.errorTitle') }}</p>
            <p class="text-sm text-red-600 whitespace-pre-line">{{ error }}</p>
          </div>

          <button
            type="submit"
            :disabled="isLoading"
            class="w-full bg-yellow-400 hover:bg-yellow-500 disabled:bg-gray-300 disabled:cursor-not-allowed text-gray-900 font-semibold py-2 px-4 rounded-md transition-colors"
          >
            {{ isLoading ? t('login.loading') : t('login.submit') }}
          </button>

          <button
            type="button"
            @click="changeDevice"
            class="w-full mt-3 text-sm text-gray-600 hover:text-gray-900 underline"
          >
            {{ t('login.changeDevice') }}
          </button>
        </form>
      </div>

      <p class="mt-5 text-center text-sm leading-6 text-gray-500">
        {{ t('login.footerPrefix') }}
        <a
          href="https://aitje.com"
          target="_blank"
          rel="noopener noreferrer"
          class="font-medium text-gray-800 underline decoration-yellow-400 underline-offset-4 hover:text-gray-950"
        >
          {{ t('login.footerLink') }}
        </a>
        {{ t('login.footerSuffix') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '~/stores/auth'
import { useAitjeApi } from '~/composables/useAitjeApi'
import { useRouter } from 'vue-router'
import { useI18n } from '~/composables/useI18n'
import LanguageSwitcher from '~/components/common/LanguageSwitcher.vue'

const authStore = useAuthStore()
const { signon } = useAitjeApi()
const router = useRouter()
const { t } = useI18n()

const username = ref('')
const password = ref('')
const error = ref('')
const isLoading = ref(false)
const isNativeMobileApp = ref(false)
const baseUrlDisplay = computed(() => authStore.baseUrl || '—')

const handleLogin = async () => {
  error.value = ''
  isLoading.value = true

  try {
    const response = await signon(username.value, password.value)
    authStore.setAuthData(response.token, response.expires_at, username.value)
    router.push('/')
  } catch (e: any) {
    const aitjeError = e as Error
    error.value = aitjeError.message || t('errors.loginGeneric')
  } finally {
    isLoading.value = false
  }
}

const changeDevice = () => {
  authStore.clearAll()
  router.push({ path: '/setup', query: { changeDevice: '1' } })
}

onMounted(() => {
  isNativeMobileApp.value = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)

  authStore.loadFromLocalStorage()

  if (!authStore.isDeviceConfigured) {
    router.push('/setup')
  } else if (authStore.isAuthenticated) {
    router.push('/')
  }
})
</script>
