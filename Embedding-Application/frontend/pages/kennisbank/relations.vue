<template>
  <component :is="isFullscreen ? 'div' : KennisbankTabLayout" :class="isFullscreen ? 'fixed inset-0 z-50 bg-loci-cream' : ''">
    <div :class="isFullscreen ? 'h-screen flex flex-col p-4' : 'flex flex-col h-[calc(100vh-200px)]'">
      <!-- Header -->
      <div class="flex justify-between items-center mb-4">
        <div>
          <h1 class="text-2xl font-bold text-loci-black">
            {{ translate('Relatiemanager', 'Relationship manager') }}
          </h1>
          <p v-if="!isFullscreen" class="text-sm text-loci-gray-500 mt-1">
            {{ translate('Beheer relaties tussen documenten. Klik op een verbinding om deze te verwijderen.', 'Manage relations between documents. Click a connection to remove it.') }}
          </p>
        </div>
        <div class="flex items-center gap-3">
          <!-- Fullscreen toggle -->
          <button
            class="p-2 rounded-lg border border-loci-gray-200 hover:bg-loci-gray-50 transition-all"
            :title="isFullscreen ? translate('Sluiten', 'Close') : translate('Volledig scherm', 'Full screen')"
            @click="toggleFullscreen"
          >
            <svg v-if="!isFullscreen" class="w-5 h-5 text-loci-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
            <svg v-else class="w-5 h-5 text-loci-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          <!-- New relation button -->
          <button
            class="px-6 py-3 bg-loci-yellow text-loci-black-deep rounded-loci-full font-semibold hover:bg-loci-yellow-hover transition-all flex items-center gap-2"
            :class="{ 'ring-2 ring-loci-yellow ring-offset-2': showAddRelationModal }"
            @click="toggleAddRelationMode"
          >
            <svg v-if="!showAddRelationModal" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            {{ showAddRelationModal ? translate('Annuleren', 'Cancel') : translate('Nieuwe Relatie', 'New relation') }}
          </button>
        </div>
      </div>

      <!-- Info banner when creating relation -->
      <div v-if="showAddRelationModal" class="mb-4 p-3 bg-loci-yellow/20 border border-loci-yellow rounded-lg flex items-center gap-3">
        <svg class="w-5 h-5 text-loci-black flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="text-sm text-loci-black">
          {{ translate('Relaties zijn tijdelijk verborgen. Selecteer hieronder bron en doel document.', 'Relations are temporarily hidden. Select source and target document below.') }}
        </span>
      </div>

      <!-- Loading state -->
      <div v-if="isLoading" class="flex-1 flex items-center justify-center bg-loci-white rounded-loci-lg border border-loci-gray-100">
        <div class="text-center">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-loci-yellow mx-auto"></div>
          <p class="mt-4 text-loci-gray-500">{{ translate('Laden...', 'Loading...') }}</p>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="nodes.length === 0" class="flex-1 flex items-center justify-center bg-loci-white rounded-loci-lg border border-loci-gray-100">
        <div class="text-center">
          <svg class="mx-auto h-12 w-12 text-loci-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 class="mt-2 text-sm font-medium text-loci-black">{{ translate('Geen documenten', 'No documents') }}</h3>
          <p class="mt-1 text-sm text-loci-gray-500">
            {{ translate('Upload eerst documenten om relaties te kunnen aanmaken.', 'Upload documents before creating relations.') }}
          </p>
        </div>
      </div>

      <!-- Vue Flow Mindmap -->
      <div v-else class="flex-1 bg-loci-white rounded-loci-lg border border-loci-gray-100 overflow-hidden">
        <VueFlow
          v-model:nodes="flowNodes"
          v-model:edges="visibleEdges"
          :default-viewport="{ zoom: 0.7, x: 50, y: 50 }"
          :min-zoom="0.1"
          :max-zoom="2"
          fit-view-on-init
          @edge-click="onEdgeClick"
        >
          <Background pattern-color="#e5e7eb" :gap="20" />
          <Controls position="bottom-right" />
          <MiniMap position="bottom-left" />

          <!-- Custom Category Label Node -->
          <template #node-category="nodeProps">
            <div
              class="px-4 py-2 rounded-lg font-bold text-sm shadow-sm"
              :style="{ backgroundColor: nodeProps.data.color + '30', borderColor: nodeProps.data.color, borderWidth: '2px' }"
            >
              {{ nodeProps.data.label }}
              <span class="ml-2 text-xs font-normal opacity-70">({{ nodeProps.data.count }})</span>
            </div>
          </template>

          <!-- Custom Document Node -->
          <template #node-document="nodeProps">
            <KennisbankDocumentNode :data="nodeProps.data" />
          </template>
        </VueFlow>
      </div>

      <!-- Legend -->
      <div v-if="!showAddRelationModal" class="mt-4 p-4 bg-loci-white rounded-loci-lg border border-loci-gray-100">
        <div class="flex flex-wrap items-center gap-6">
          <!-- Relation types -->
          <div>
            <h3 class="text-xs font-medium text-loci-gray-400 uppercase tracking-wide mb-2">
              {{ translate('Relatietypes', 'Relation types') }}
            </h3>
            <div class="flex flex-wrap gap-3">
              <div v-for="(color, type) in edgeColors" :key="type" class="flex items-center gap-2">
                <div class="w-6 h-0.5" :style="{ backgroundColor: color }"></div>
                <span class="text-xs text-loci-gray-600">{{ getRelationLabel(type) }}</span>
              </div>
            </div>
          </div>

          <!-- Category colors -->
          <div class="border-l border-loci-gray-200 pl-6">
            <h3 class="text-xs font-medium text-loci-gray-400 uppercase tracking-wide mb-2">
              {{ translate('Categorieen', 'Categories') }}
            </h3>
            <div class="flex flex-wrap gap-3">
              <div v-for="(color, category) in categoryColorMap" :key="category" class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full" :style="{ backgroundColor: color }"></div>
                <span class="text-xs text-loci-gray-600">{{ category }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Relation Modal -->
    <KennisbankRelationModal
      v-if="showAddRelationModal"
      :documents="allDocuments"
      :relation-types="translatedRelationTypes"
      @close="showAddRelationModal = false"
      @create="handleCreateRelation"
    />

    <!-- Delete Confirmation -->
    <div v-if="selectedEdge" class="fixed inset-0 bg-loci-black/50 flex items-center justify-center z-50">
      <div class="bg-loci-white rounded-loci-lg border border-loci-gray-100 p-6 max-w-sm">
        <h3 class="text-lg font-semibold mb-2 text-loci-black">
          {{ translate('Relatie verwijderen?', 'Remove relation?') }}
        </h3>
        <p class="text-loci-gray-500 mb-4">
          {{ translate('Weet je zeker dat je deze relatie wilt verwijderen?', 'Are you sure you want to delete this relation?') }}
        </p>
        <div class="flex justify-end gap-3">
          <button
            class="px-4 py-2 rounded-full border border-loci-gray-200 text-loci-black font-semibold hover:bg-loci-gray-50 transition-all"
            @click="selectedEdge = null"
          >
            {{ translate('Annuleren', 'Cancel') }}
          </button>
          <button
            class="px-4 py-2 bg-red-500 text-white rounded-full font-semibold hover:bg-red-600 transition-all"
            @click="handleDeleteRelation"
          >
            {{ translate('Verwijderen', 'Delete') }}
          </button>
        </div>
      </div>
    </div>
  </component>
</template>

<script setup lang="ts">
import { VueFlow } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import { MiniMap } from '@vue-flow/minimap';
import type { Node, Edge, EdgeMouseEvent } from '@vue-flow/core';
import type { Document } from '~/types/Kennisbank';

// Import Vue Flow styles
import '@vue-flow/core/dist/style.css';
import '@vue-flow/core/dist/theme-default.css';
import '@vue-flow/controls/dist/style.css';
import '@vue-flow/minimap/dist/style.css';

definePageMeta({
  middleware: 'auth',
});

const KennisbankTabLayout = resolveComponent('KennisbankTabLayout');

const store = useKennisbankStore();
const { graphNodes, graphEdges, graphCategories, documentRelationTypes, isLoading } = storeToRefs(store);
const { translate } = useTranslations();

const isFullscreen = ref(false);
const showAddRelationModal = ref(false);
const selectedEdge = ref<Edge | null>(null);
const allDocuments = ref<Document[]>([]);

// Category colors - consistent per category
const categoryColorPalette = [
  '#3b82f6', // blue
  '#10b981', // green
  '#8b5cf6', // purple
  '#f59e0b', // amber
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f43f5e', // rose
  '#6366f1', // indigo
  '#84cc16', // lime
  '#14b8a6', // teal
];

// Edge colors by relation type
const edgeColors: Record<string, string> = {
  references: '#3b82f6',
  extends: '#10b981',
  contradicts: '#ef4444',
  supplements: '#8b5cf6',
  parent_of: '#f59e0b',
  related_to: '#6b7280',
};

const relationLabelMap: Record<string, { nl: string; en: string }> = {
  references: { nl: 'Verwijst naar', en: 'References' },
  extends: { nl: 'Breidt uit', en: 'Extends' },
  contradicts: { nl: 'Tegenspreekt', en: 'Contradicts' },
  supplements: { nl: 'Vult aan', en: 'Supplements' },
  parent_of: { nl: 'Is ouder van', en: 'Parent of' },
  related_to: { nl: 'Gerelateerd aan', en: 'Related to' },
};

// Generate consistent color for category
const categoryColorMap = computed(() => {
  const map: Record<string, string> = {};
  const categories = Object.keys(graphCategories.value);
  categories.forEach((category, index) => {
    map[category] = categoryColorPalette[index % categoryColorPalette.length];
  });
  return map;
});

const translatedRelationTypes = computed(() => {
  const result: Record<string, string> = {};
  Object.keys(documentRelationTypes.value).forEach((key) => {
    result[key] = getRelationLabel(key);
  });
  return result;
});

// Convert graph data to Vue Flow format with category clusters
const nodes = computed<Node[]>(() => {
  if (!graphNodes.value.length) return [];

  const categoryList = Object.keys(graphCategories.value);
  const allNodes: Node[] = [];

  // Create category label nodes and position document nodes
  categoryList.forEach((category, catIndex) => {
    const categoryColor = categoryColorMap.value[category] || '#6b7280';
    const nodesInCategory = graphCategories.value[category] || [];

    // Calculate cluster position - arrange in a grid
    const cols = Math.ceil(Math.sqrt(categoryList.length));
    const row = Math.floor(catIndex / cols);
    const col = catIndex % cols;
    const clusterX = col * 450;
    const clusterY = row * 400;

    // Add category label node
    allNodes.push({
      id: `category-${category}`,
      type: 'category',
      position: { x: clusterX, y: clusterY },
      data: {
        label: category,
        color: categoryColor,
        count: nodesInCategory.length,
      },
      draggable: true,
      selectable: false,
    });

    // Add document nodes in a cluster below the category label
    nodesInCategory.forEach((nodeId, nodeIndex) => {
      const node = graphNodes.value.find(n => n.id === nodeId);
      if (!node) return;

      // Arrange in rows of 3
      const nodeRow = Math.floor(nodeIndex / 3);
      const nodeCol = nodeIndex % 3;

      allNodes.push({
        id: node.id,
        type: 'document',
        position: {
          x: clusterX + (nodeCol * 220),
          y: clusterY + 60 + (nodeRow * 100),
        },
        data: {
          label: node.title,
          category: node.category,
          priority: node.priority,
          color: categoryColor,
        },
        draggable: true,
      });
    });
  });

  return allNodes;
});

// Flow nodes (mutable copy for dragging)
const flowNodes = ref<Node[]>([]);

// Watch for nodes changes and update flowNodes
watch(nodes, (newNodes) => {
  flowNodes.value = [...newNodes];
}, { immediate: true });

const edges = computed<Edge[]>(() => {
  return graphEdges.value.map(edge => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: getRelationLabel(edge.relation_type),
    type: 'smoothstep',
    animated: edge.relation_type === 'contradicts',
    style: {
      stroke: edgeColors[edge.relation_type] || edgeColors.related_to,
      strokeWidth: 2,
    },
    labelStyle: {
      fill: '#374151',
      fontSize: 11,
    },
    labelBgStyle: {
      fill: '#ffffff',
    },
    data: {
      relation_type: edge.relation_type,
    },
  }));
});

// Hide edges when adding new relation
const visibleEdges = computed(() => {
  if (showAddRelationModal.value) {
    return [];
  }
  return edges.value;
});

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value;
}

function toggleAddRelationMode() {
  showAddRelationModal.value = !showAddRelationModal.value;
}

function getRelationLabel(type: string) {
  const mapping = relationLabelMap[type];
  if (mapping) {
    return translate(mapping.nl, mapping.en);
  }
  const fallback = documentRelationTypes.value[type] || type;
  return translate(fallback, fallback);
}

function onEdgeClick(event: EdgeMouseEvent) {
  if (!showAddRelationModal.value) {
    selectedEdge.value = event.edge;
  }
}

async function handleCreateRelation(data: { sourceId: number; targetId: number; relationType: string }) {
  try {
    await store.createDocumentRelation(data.sourceId, data.targetId, data.relationType);
    showAddRelationModal.value = false;
  } catch (error) {
    console.error('Failed to create relation:', error);
  }
}

async function handleDeleteRelation() {
  if (!selectedEdge.value) return;

  try {
    await store.deleteDocumentRelation(parseInt(selectedEdge.value.id));
    selectedEdge.value = null;
  } catch (error) {
    console.error('Failed to delete relation:', error);
  }
}

// Handle ESC key to exit fullscreen
onMounted(async () => {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (showAddRelationModal.value) {
        showAddRelationModal.value = false;
      } else if (isFullscreen.value) {
        isFullscreen.value = false;
      }
    }
  });

  await Promise.all([
    store.fetchGraph(),
    store.fetchDocumentRelationTypes(),
    store.fetchDocuments(),
  ]);
  allDocuments.value = store.documents.filter(d => d.status === 'formatted');
});
</script>

<style>
.vue-flow__edge-path {
  stroke-width: 2;
}

.vue-flow__edge.selected .vue-flow__edge-path {
  stroke-width: 3;
}

.vue-flow__node-document {
  cursor: grab;
}

.vue-flow__node-document:active {
  cursor: grabbing;
}

.vue-flow__node-category {
  cursor: grab;
}

.vue-flow__minimap {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
}
</style>
