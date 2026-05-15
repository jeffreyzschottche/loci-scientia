<template>
  <div class="select-none">
    <div
      class="flex items-center px-2 py-1.5 rounded cursor-pointer group"
      :class="{
        'bg-blue-100 text-blue-900': isSelected,
        'hover:bg-gray-100': !isSelected,
      }"
      :style="{ paddingLeft: `${depth * 16 + 8}px` }"
      @click="$emit('select', node)"
    >
      <!-- Expand/Collapse toggle -->
      <button
        v-if="hasChildren"
        class="p-0.5 mr-1 hover:bg-gray-200 rounded"
        @click.stop="isExpanded = !isExpanded"
      >
        <svg
          class="h-4 w-4 text-gray-500 transition-transform"
          :class="{ 'rotate-90': isExpanded }"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
      <span v-else class="w-5" />

      <!-- Icon -->
      <span class="mr-2 text-sm">
        {{ getIcon() }}
      </span>

      <!-- Title -->
      <span class="flex-1 truncate text-sm">{{ node.title }}</span>

      <!-- Status badge (for documents) -->
      <span
        v-if="node.type === 'document' && node.status"
        class="ml-2 w-2 h-2 rounded-full flex-shrink-0"
        :class="getStatusDotClass()"
      />
    </div>

    <!-- Children -->
    <div v-if="hasChildren && isExpanded">
      <TreeNode
        v-for="child in node.children"
        :key="child.id + '-' + child.type"
        :node="child"
        :depth="depth + 1"
        :selected-id="selectedId"
        :selected-type="selectedType"
        @select="(n: TreeNodeType) => $emit('select', n)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TreeNode as TreeNodeType } from '~/types/Kennisbank';

const props = defineProps<{
  node: TreeNodeType;
  depth?: number;
  selectedId?: number;
  selectedType?: 'document' | 'section';
}>();

defineEmits<{
  (e: 'select', node: TreeNodeType): void;
}>();

const depth = props.depth ?? 0;
const isExpanded = ref(depth === 0); // Auto-expand root level

const hasChildren = computed(() => {
  return props.node.children && props.node.children.length > 0;
});

const isSelected = computed(() => {
  return props.selectedId === props.node.id && props.selectedType === props.node.type;
});

function getIcon() {
  if (props.node.type === 'section') {
    return '📄';
  }

  // Document icons based on status
  switch (props.node.status) {
    case 'formatted':
      return '📗';
    case 'processing':
      return '⏳';
    case 'failed':
      return '❌';
    default:
      return '📁';
  }
}

function getStatusDotClass() {
  switch (props.node.status) {
    case 'formatted':
      return 'bg-green-500';
    case 'processing':
      return 'bg-blue-500 animate-pulse';
    case 'failed':
      return 'bg-red-500';
    default:
      return 'bg-gray-300';
  }
}
</script>
