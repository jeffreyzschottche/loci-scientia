<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Tab Navigation -->
    <div class="bg-white border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav class="flex space-x-8" aria-label="Tabs">
          <NuxtLink
            to="/kennisbank/upload"
            class="py-4 px-1 border-b-2 font-medium text-sm"
            :class="isActive('/kennisbank/upload')
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          >
            Uploaden
          </NuxtLink>
          <NuxtLink
            to="/kennisbank/library"
            class="py-4 px-1 border-b-2 font-medium text-sm"
            :class="isActive('/kennisbank/library')
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          >
            Bibliotheek
          </NuxtLink>
          <NuxtLink
            to="/kennisbank/relations"
            class="py-4 px-1 border-b-2 font-medium text-sm"
            :class="isActive('/kennisbank/relations')
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          >
            Relaties
          </NuxtLink>
          <NuxtLink
            to="/kennisbank/priorities"
            class="py-4 px-1 border-b-2 font-medium text-sm"
            :class="isActive('/kennisbank/priorities')
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          >
            Prioriteiten
          </NuxtLink>
          <NuxtLink
            to="/kennisbank/insights"
            class="py-4 px-1 border-b-2 font-medium text-sm"
            :class="isActive('/kennisbank/insights')
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
          >
            Inzicht
          </NuxtLink>
        </nav>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute();

function isActive(path: string) {
  return route.path.startsWith(path);
}
</script>
