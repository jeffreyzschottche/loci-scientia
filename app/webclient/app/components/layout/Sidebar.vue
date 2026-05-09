<template>
  <aside class="w-64 bg-white border-r border-gray-200 flex flex-col h-screen">
    <div class="p-4 border-b border-gray-200">
      <div class="flex items-center gap-2 mb-1">
        <div class="w-10 h-10 rounded-full bg-black flex items-center justify-center">
          <span class="text-white font-bold text-lg">A</span>
        </div>
        <h1 class="text-xl font-bold text-gray-900">AITJE</h1>
      </div>
      <p class="text-xs text-gray-500 ml-12">{{ t('common.tagline') }}</p>
    </div>

    <nav class="flex-1 p-3 overflow-y-auto">
      <a
        v-for="item in menuItems"
        :key="item.name"
        href="#"
        :class="[
          'flex items-center gap-3 px-3 py-2 rounded-lg mb-1 transition-colors',
          item.active
            ? 'bg-yellow-400 text-gray-900 font-medium'
            : 'text-gray-700 hover:bg-gray-100'
        ]"
      >
        <component :is="item.icon" class="w-5 h-5" />
        <span>{{ item.name }}</span>
      </a>
    </nav>

    <div class="p-4 border-t border-gray-200 space-y-2">
      <div class="flex items-center gap-2">
        <LanguageSwitcher size="xs" class="flex-shrink-0" />
        <button
          @click="handleLogout"
          class="flex-1 text-sm text-red-600 hover:text-red-700 text-left px-3 py-2 hover:bg-red-50 rounded-lg transition-colors"
        >
          {{ t('header.logout') }}
        </button>
      </div>
      <div class="text-xs text-gray-500">AITJE v1.0</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useAuthStore } from '~/stores/auth'
import { useChatStore } from '~/stores/chat'
import { useRouter } from 'vue-router'
import { h, computed } from 'vue'
import LanguageSwitcher from '~/components/common/LanguageSwitcher.vue'
import { useI18n } from '~/composables/useI18n'

const authStore = useAuthStore()
const chatStore = useChatStore()
const router = useRouter()
const { t } = useI18n()

const ChatIcon = () => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  class: 'w-5 h-5'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z'
  })
])

const ApiIcon = () => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  class: 'w-5 h-5'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
  })
])

const BookIcon = () => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  class: 'w-5 h-5'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253'
  })
])

const MapIcon = () => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  class: 'w-5 h-5'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7'
  })
])

const UsersIcon = () => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  class: 'w-5 h-5'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z'
  })
])

const GlobeIcon = () => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  class: 'w-5 h-5'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
  })
])

const DevicesIcon = () => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  class: 'w-5 h-5'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z'
  })
])

const SettingsIcon = () => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  class: 'w-5 h-5'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z'
  }),
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z'
  })
])

const QuestionIcon = () => h('svg', {
  fill: 'none',
  stroke: 'currentColor',
  viewBox: '0 0 24 24',
  class: 'w-5 h-5'
}, [
  h('path', {
    'stroke-linecap': 'round',
    'stroke-linejoin': 'round',
    'stroke-width': '2',
    d: 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
  })
])

const menuItems = computed(() => [
  { name: t('sidebar.chat'), icon: ChatIcon, active: true },
  { name: t('sidebar.api'), icon: ApiIcon, active: false },
  { name: t('sidebar.knowledge'), icon: BookIcon, active: false },
  { name: t('sidebar.maps'), icon: MapIcon, active: false },
  { name: t('sidebar.contacts'), icon: UsersIcon, active: false },
  { name: t('sidebar.network'), icon: GlobeIcon, active: false },
  { name: t('sidebar.connectedDevices'), icon: DevicesIcon, active: false },
  { name: t('sidebar.settings'), icon: SettingsIcon, active: false },
  { name: t('sidebar.faq'), icon: QuestionIcon, active: false },
])

const handleLogout = () => {
  authStore.clearAuth()
  chatStore.clearMessages()
  router.push('/login')
}
</script>
