import { defineStore } from 'pinia';
import type {
  Document,
  DocumentSection,
  DocumentRelation,
  TreeNode,
  KennisbankStats,
  Export,
  DocumentResponse,
  DocumentsResponse,
  TreeResponse,
  SectionResponse,
  StatsResponse,
  StatusResponse,
  RelationTypesResponse,
  ExportsResponse,
  CategoriesResponse,
  GraphNode,
  GraphEdge,
  GraphResponse,
  PriorityCategoriesResponse,
  PriorityUpdate,
} from '~/types/Kennisbank';

export const useKennisbankStore = defineStore('kennisbank', () => {
  // State
  const documents = ref<Document[]>([]);
  const tree = ref<TreeNode[]>([]);
  const selectedDocument = ref<Document | null>(null);
  const selectedSection = ref<DocumentSection | null>(null);
  const stats = ref<KennisbankStats | null>(null);
  const categories = ref<Record<string, number>>({});
  const relationTypes = ref<Record<string, string>>({});
  const documentRelationTypes = ref<Record<string, string>>({});
  const exports = ref<Export[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // Upload state
  const uploadProgress = ref<Map<number, StatusResponse>>(new Map());

  // Graph state (for mindmap)
  const graphNodes = ref<GraphNode[]>([]);
  const graphEdges = ref<GraphEdge[]>([]);
  const graphCategories = ref<Record<string, string[]>>({});

  // Priority state
  const priorityCategories = ref<Record<string, Document[]>>({});

  // API helper
  const api = useApi();

  // Actions - Documents
  async function fetchDocuments() {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await api.get<DocumentsResponse>('/documents');
      documents.value = response.documents;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  async function uploadDocument(file: File, metadata: {
    title?: string;
    category?: string;
    version_tag?: string;
    description?: string;
    parent_id?: number;
  } = {}) {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata.title) formData.append('title', metadata.title);
    if (metadata.category) formData.append('category', metadata.category);
    if (metadata.version_tag) formData.append('version_tag', metadata.version_tag);
    if (metadata.description) formData.append('description', metadata.description);
    if (metadata.parent_id) formData.append('parent_id', String(metadata.parent_id));

    const response = await api.post<DocumentResponse>('/documents', formData);
    documents.value.unshift(response.document);
    return response;
  }

  async function saveMapping(documentId: number, mapping: Record<string, any>) {
    const response = await api.post<DocumentResponse>(`/documents/${documentId}/mapping`, { mapping });
    updateDocumentInState(response.document);
    return response.document;
  }

  async function processDocument(documentId: number) {
    const response = await api.post<DocumentResponse>(`/documents/${documentId}/process`);
    updateDocumentInState(response.document);
    return response.document;
  }

  async function getDocumentStatus(documentId: number): Promise<StatusResponse> {
    const response = await api.get<StatusResponse>(`/documents/${documentId}/status`);
    uploadProgress.value.set(documentId, response);
    return response;
  }

  async function deleteDocument(documentId: number) {
    await api.delete(`/documents/${documentId}`);
    documents.value = documents.value.filter(d => d.id !== documentId);
    if (selectedDocument.value?.id === documentId) {
      selectedDocument.value = null;
    }
  }

  // Actions - Library
  async function fetchTree() {
    isLoading.value = true;
    try {
      const response = await api.get<TreeResponse>('/library/tree');
      tree.value = response.tree;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchDocument(documentId: number) {
    const response = await api.get<DocumentResponse>(`/library/documents/${documentId}`);
    selectedDocument.value = response.document;
    return response;
  }

  async function fetchSection(sectionId: number) {
    const response = await api.get<SectionResponse>(`/library/sections/${sectionId}`);
    selectedSection.value = response.section;
    return response;
  }

  async function updateDocument(documentId: number, data: Partial<Document>) {
    const response = await api.patch<{ document: Document }>(`/library/documents/${documentId}`, data);
    selectedDocument.value = response.document;
    updateDocumentInState(response.document);
    return response.document;
  }

  async function updateSection(sectionId: number, data: Partial<DocumentSection>) {
    const response = await api.patch<{ section: DocumentSection }>(`/library/sections/${sectionId}`, data);
    selectedSection.value = response.section;
    return response.section;
  }

  async function moveDocument(documentId: number, parentId: number | null, position?: number) {
    const response = await api.patch<{ document: Document }>(`/library/documents/${documentId}/move`, {
      parent_id: parentId,
      position,
    });
    updateDocumentInState(response.document);
    await fetchTree(); // Refresh tree
    return response.document;
  }

  async function addRelation(sectionId: number, targetSectionId: number, relationType: string) {
    const response = await api.post<{ relation: any }>(`/library/sections/${sectionId}/relations`, {
      target_section_id: targetSectionId,
      relation_type: relationType,
    });
    // Refresh section to get updated relations
    if (selectedSection.value?.id === sectionId) {
      await fetchSection(sectionId);
    }
    return response.relation;
  }

  async function removeRelation(relationId: number) {
    await api.delete(`/library/relations/${relationId}`);
    // Refresh current section if selected
    if (selectedSection.value) {
      await fetchSection(selectedSection.value.id);
    }
  }

  async function fetchRelationTypes() {
    const response = await api.get<RelationTypesResponse>('/library/relation-types');
    relationTypes.value = response.types;
    return response.types;
  }

  async function searchSections(query: string, category?: string) {
    const params = new URLSearchParams({ query });
    if (category) params.append('category', category);
    const response = await api.get<{ sections: DocumentSection[] }>(`/library/search?${params}`);
    return response.sections;
  }

  // Actions - Insights
  async function fetchStats() {
    const response = await api.get<StatsResponse>('/insights/stats');
    stats.value = response.stats;
    categories.value = response.categories;
    return response;
  }

  async function fetchCategories() {
    const response = await api.get<CategoriesResponse>('/insights/categories');
    return response.categories;
  }

  async function exportManifest(category?: string, versionTag?: string) {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (versionTag) params.append('version_tag', versionTag);
    const response = await api.get<Record<string, any>>(`/insights/export/manifest?${params}`);
    return response;
  }

  async function exportChunks(category?: string) {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    const response = await api.get<Record<string, any>>(`/insights/export/chunks?${params}`);
    return response;
  }

  async function createExport(format: 'manifest' | 'chunks', category?: string) {
    const response = await api.post<{ export: Export; download_url: string }>('/insights/exports', {
      format,
      category,
    });
    exports.value.unshift(response.export);
    return response;
  }

  async function fetchExports() {
    const response = await api.get<ExportsResponse>('/insights/exports');
    exports.value = response.exports;
    return response.exports;
  }

  // Actions - Document Relations (Mindmap)
  async function fetchGraph() {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await api.get<GraphResponse>('/relations/graph');
      graphNodes.value = response.nodes;
      graphEdges.value = response.edges;
      graphCategories.value = response.categories;
      return response;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchDocumentRelationTypes() {
    const response = await api.get<RelationTypesResponse>('/relations/types');
    documentRelationTypes.value = response.types;
    return response.types;
  }

  async function createDocumentRelation(
    sourceDocumentId: number,
    targetDocumentId: number,
    relationType: string
  ) {
    const response = await api.post<{ relation: DocumentRelation }>('/relations', {
      source_document_id: sourceDocumentId,
      target_document_id: targetDocumentId,
      relation_type: relationType,
    });
    await fetchGraph(); // Refresh graph
    return response.relation;
  }

  async function deleteDocumentRelation(relationId: number) {
    await api.delete(`/relations/${relationId}`);
    await fetchGraph(); // Refresh graph
  }

  // Actions - Priorities
  async function fetchPriorities() {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await api.get<PriorityCategoriesResponse>('/priorities');
      priorityCategories.value = response.categories;
      return response.categories;
    } catch (e: any) {
      error.value = e.message;
      throw e;
    } finally {
      isLoading.value = false;
    }
  }

  async function updateDocumentPriority(documentId: number, priority: number) {
    const response = await api.patch<{ document: Document }>(`/priorities/${documentId}`, {
      priority,
    });
    updateDocumentInState(response.document);
    return response.document;
  }

  async function bulkUpdatePriorities(priorities: PriorityUpdate[]) {
    await api.post('/priorities/bulk', { priorities });
    await fetchPriorities(); // Refresh
  }

  // Helper
  function updateDocumentInState(doc: Document) {
    const index = documents.value.findIndex(d => d.id === doc.id);
    if (index !== -1) {
      documents.value[index] = doc;
    }
  }

  function clearSelection() {
    selectedDocument.value = null;
    selectedSection.value = null;
  }

  return {
    // State
    documents,
    tree,
    selectedDocument,
    selectedSection,
    stats,
    categories,
    relationTypes,
    documentRelationTypes,
    exports,
    isLoading,
    error,
    uploadProgress,
    graphNodes,
    graphEdges,
    graphCategories,
    priorityCategories,

    // Actions
    fetchDocuments,
    uploadDocument,
    saveMapping,
    processDocument,
    getDocumentStatus,
    deleteDocument,
    fetchTree,
    fetchDocument,
    fetchSection,
    updateDocument,
    updateSection,
    moveDocument,
    addRelation,
    removeRelation,
    fetchRelationTypes,
    searchSections,
    fetchStats,
    fetchCategories,
    exportManifest,
    exportChunks,
    createExport,
    fetchExports,
    clearSelection,
    // Graph/Relations
    fetchGraph,
    fetchDocumentRelationTypes,
    createDocumentRelation,
    deleteDocumentRelation,
    // Priorities
    fetchPriorities,
    updateDocumentPriority,
    bulkUpdatePriorities,
  };
});
