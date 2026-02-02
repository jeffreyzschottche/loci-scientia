<template>
  <KennisbankTabLayout>
    <div class="flex flex-col h-[calc(100vh-200px)]">
      <div class="flex justify-between items-center mb-4">
        <div>
          <h1 class="text-2xl font-bold text-loci-black">
            {{ translate('Relatiemanager', 'Relationship manager') }}
          </h1>
          <p class="text-sm text-loci-gray-500 mt-1">
            {{ translate('Beheer relaties tussen documenten. Klik op een verbinding om deze te verwijderen.', 'Manage relations between documents. Click a connection to remove it.') }}
          </p>
        </div>
        <button
          class="px-6 py-3 bg-loci-yellow text-loci-black-deep rounded-loci-full font-semibold hover:bg-loci-yellow-hover transition-all flex items-center gap-2"
          @click="showAddRelationModal = true"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          {{ translate('Nieuwe Relatie', 'New relation') }}
        </button>
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
          v-model:nodes="nodes"
          v-model:edges="edges"
          :default-viewport="{ zoom: 0.8, x: 100, y: 100 }"
          :min-zoom="0.2"
          :max-zoom="2"
          fit-view-on-init
          @edge-click="onEdgeClick"
        >
          <Background pattern-color="#e5e7eb" :gap="20" />
          <Controls />
          <MiniMap />

          <!-- Custom Document Node -->
          <template #node-document="nodeProps">
            <KennisbankDocumentNode :data="nodeProps.data" />
          </template>
        </VueFlow>
      </div>

      <!-- Legend -->
      <div class="mt-4 p-4 bg-loci-white rounded-loci-lg border border-loci-gray-100">
        <h3 class="text-sm font-medium text-loci-black mb-2">
          {{ translate('Legenda relatietypes', 'Relation type legend') }}
        </h3>
        <div class="flex flex-wrap gap-4">
          <div v-for="(color, type) in edgeColors" :key="type" class="flex items-center gap-2">
            <div class="w-6 h-0.5" :style="{ backgroundColor: color }"></div>
            <span class="text-xs text-loci-gray-500">{{ getRelationLabel(type) }}</span>
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
  </KennisbankTabLayout>
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

const store = useKennisbankStore();
const { graphNodes, graphEdges, graphCategories, documentRelationTypes, isLoading } = storeToRefs(store);
const { translate } = useTranslations();

const showAddRelationModal = ref(false);
const selectedEdge = ref<Edge | null>(null);
const allDocuments = ref<Document[]>([]);

// Edge colors by relation type
const edgeColors: Record<string, string> = {
  references: '#3b82f6',    // blue
  extends: '#10b981',       // green
  contradicts: '#ef4444',   // red
  supplements: '#8b5cf6',   // purple
  parent_of: '#f59e0b',     // amber
  related_to: '#6b7280',    // gray
};

const relationLabelMap: Record<string, { nl: string; en: string }> = {
  references: { nl: 'Verwijst naar', en: 'References' },
  extends: { nl: 'Breidt uit', en: 'Extends' },
  contradicts: { nl: 'Tegenspreekt', en: 'Contradicts' },
  supplements: { nl: 'Vult aan', en: 'Supplements' },
  parent_of: { nl: 'Is ouder van', en: 'Parent of' },
  related_to: { nl: 'Gerelateerd aan', en: 'Related to' },
};

const translatedRelationTypes = computed(() => {
  const result: Record<string, string> = {};
  Object.keys(documentRelationTypes.value).forEach((key) => {
    result[key] = getRelationLabel(key);
  });
  return result;
});

// Convert graph data to Vue Flow format
const nodes = computed<Node[]>(() => {
  if (!graphNodes.value.length) return [];

  // Calculate positions by category
  const categoryList = Object.keys(graphCategories.value);

  return graphNodes.value.map((node, index) => {
    const categoryIndex = categoryList.indexOf(node.category || 'Geen categorie');
    const nodesInCategory = graphCategories.value[node.category || 'Geen categorie'] || [];
    const positionInCategory = nodesInCategory.indexOf(node.id);

    // Arrange in clusters by category
    const clusterX = (categoryIndex >= 0 ? categoryIndex : 0) * 350;
    const clusterY = (positionInCategory >= 0 ? positionInCategory : index) * 120;

    return {
      id: node.id,
      type: 'document',
      position: { x: clusterX + 100, y: clusterY + 100 },
      data: {
        label: node.title,
        category: node.category,
        priority: node.priority,
      },
      draggable: true,
    };
  });
});

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

function getRelationLabel(type: string) {
  const mapping = relationLabelMap[type];
  if (mapping) {
    return translate(mapping.nl, mapping.en);
  }
  const fallback = documentRelationTypes.value[type] || type;
  return translate(fallback, fallback);
}

function onEdgeClick(event: EdgeMouseEvent) {
  selectedEdge.value = event.edge;
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

onMounted(async () => {
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
</style>
