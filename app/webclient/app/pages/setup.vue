<template>
  <div class="min-h-screen bg-gray-50 flex justify-center px-4 pt-12 pb-8 relative md:items-center md:pt-4">
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
      </div>

      <div class="bg-white rounded-lg shadow-md p-8">
        <h2 class="text-xl font-semibold text-gray-900 mb-6">
          {{ t('setup.title') }}
        </h2>

        <form @submit.prevent="handleSubmit">
          <div class="mb-6">
            <label for="deviceNumber" class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('setup.label') }}
            </label>
            <div class="flex items-center">
              <span class="inline-flex items-center px-3 py-2 rounded-l-md border border-r-0 border-gray-300 bg-gray-50 text-gray-700 text-sm">
                aitje-
              </span>
              <input
                id="deviceNumber"
                v-model="deviceNumber"
                type="text"
                class="flex-1 min-w-0 block w-full px-3 py-2 rounded-r-md border border-gray-300 focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 outline-none"
                placeholder="1"
                required
                autofocus
              />
            </div>
            <p class="mt-2 text-sm text-gray-500">
              {{ t('setup.helper') }}
            </p>
          </div>

          <button
            type="submit"
            class="w-full bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold py-2 px-4 rounded-md transition-colors"
          >
            {{ t('setup.submit') }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '~/stores/auth'
import { useRouter } from 'vue-router'
import { useI18n } from '~/composables/useI18n'
import LanguageSwitcher from '~/components/common/LanguageSwitcher.vue'

const authStore = useAuthStore()
const router = useRouter()
const { t } = useI18n()

const deviceNumber = ref('')
const isNativeMobileApp = ref(false)

const handleSubmit = () => {
  if (deviceNumber.value.trim()) {
    authStore.setDeviceNumber(deviceNumber.value.trim())
    router.push('/login')
  }
}

onMounted(() => {
  isNativeMobileApp.value = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)

  authStore.loadFromLocalStorage()
  if (authStore.isDeviceConfigured) {
    router.push('/login')
  }
})
</script>
