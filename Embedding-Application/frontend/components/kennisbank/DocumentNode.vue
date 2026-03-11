<template>
  <div
    class="px-4 py-3 rounded-lg border-2 bg-white shadow-md min-w-[180px] cursor-pointer"
    :class="borderColorClass"
  >
    <div class="text-sm font-medium text-gray-900 truncate max-w-[200px]">
      {{ data.label }}
    </div>
    <div class="mt-1 flex items-center gap-2 flex-wrap">
      <span
        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
        :class="categoryColorClass"
      >
        {{ data.category || 'Geen categorie' }}
      </span>
      <span v-if="data.priority > 0" class="text-xs text-gray-500">
        #{{ data.priority }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  data: {
    label: string;
    category: string | null;
    priority: number;
  };
}>();

// Color coding based on category hash
const categoryColors = [
  { bg: 'bg-blue-100 text-blue-800', border: 'border-blue-300' },
  { bg: 'bg-green-100 text-green-800', border: 'border-green-300' },
  { bg: 'bg-purple-100 text-purple-800', border: 'border-purple-300' },
  { bg: 'bg-amber-100 text-amber-800', border: 'border-amber-300' },
  { bg: 'bg-pink-100 text-pink-800', border: 'border-pink-300' },
  { bg: 'bg-cyan-100 text-cyan-800', border: 'border-cyan-300' },
  { bg: 'bg-rose-100 text-rose-800', border: 'border-rose-300' },
  { bg: 'bg-indigo-100 text-indigo-800', border: 'border-indigo-300' },
];

const colorIndex = computed(() => {
  const category = props.data.category || 'default';
  let hash = 0;
  for (let i = 0; i < category.length; i++) {
    hash = category.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % categoryColors.length;
});

const categoryColorClass = computed(() => categoryColors[colorIndex.value]?.bg ?? 'bg-gray-100 text-gray-800');
const borderColorClass = computed(() => categoryColors[colorIndex.value]?.border ?? 'border-gray-300');
</script>
