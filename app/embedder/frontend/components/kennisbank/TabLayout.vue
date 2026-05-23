<template>
  <div class="min-h-screen bg-loci-gray-50">
    <!-- Tab Navigation -->
    <div class="bg-loci-white border-b border-loci-gray-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav
          class="flex flex-col gap-3 py-4 md:flex-row md:items-center md:justify-between md:gap-0"
          aria-label="Tabs"
        >
          <div class="-mx-4 flex items-center space-x-2 overflow-x-auto px-4 md:mx-0 md:px-0">
            <NuxtLink
              to="/kennisbank/upload"
              class="flex-shrink-0 whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-semibold transition-all"
              :class="isActive('/kennisbank/upload')
                ? 'bg-loci-yellow text-loci-black-deep'
                : 'bg-loci-gray-50 text-loci-gray-500 hover:bg-loci-gray-200 hover:text-loci-black'"
            >
              {{ translate('Uploaden', 'Upload') }}
            </NuxtLink>
            <NuxtLink
              to="/kennisbank/library"
              class="flex-shrink-0 whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-semibold transition-all"
              :class="isActive('/kennisbank/library')
                ? 'bg-loci-yellow text-loci-black-deep'
                : 'bg-loci-gray-50 text-loci-gray-500 hover:bg-loci-gray-200 hover:text-loci-black'"
            >
              {{ translate('Bibliotheek', 'Library') }}
            </NuxtLink>
            <NuxtLink
              to="/kennisbank/priorities"
              class="flex-shrink-0 whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-semibold transition-all"
              :class="isActive('/kennisbank/priorities')
                ? 'bg-loci-yellow text-loci-black-deep'
                : 'bg-loci-gray-50 text-loci-gray-500 hover:bg-loci-gray-200 hover:text-loci-black'"
            >
              {{ translate('Prioriteiten', 'Priorities') }}
            </NuxtLink>
            <NuxtLink
              to="/kennisbank/insights"
              class="flex-shrink-0 whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-semibold transition-all"
              :class="isActive('/kennisbank/insights')
                ? 'bg-loci-yellow text-loci-black-deep'
                : 'bg-loci-gray-50 text-loci-gray-500 hover:bg-loci-gray-200 hover:text-loci-black'"
            >
              {{ translate('Inzicht', 'Insights') }}
            </NuxtLink>
          </div>

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
const { translate } = useTranslations();

function isActive(path: string) {
  return route.path.startsWith(path);
}
</script>
