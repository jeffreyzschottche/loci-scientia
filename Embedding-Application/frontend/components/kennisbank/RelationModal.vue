<template>
  <div class="fixed inset-0 bg-loci-black/50 flex items-center justify-center z-50 p-4">
    <div class="bg-loci-white rounded-loci-lg shadow-xl w-full max-w-lg p-6">
      <h2 class="text-lg font-semibold mb-4 text-loci-black">
        {{ translate('Nieuwe Relatie Toevoegen', 'Add New Relation') }}
      </h2>

      <form @submit.prevent="handleSubmit">
        <div class="space-y-4">
          <!-- Source Section -->
          <div class="p-4 bg-loci-cream rounded-loci">
            <h3 class="text-sm font-medium text-loci-black mb-3 flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-loci-yellow text-loci-black-deep text-xs flex items-center justify-center font-bold">1</span>
              {{ translate('Brondocument', 'Source document') }}
            </h3>

            <div class="grid grid-cols-2 gap-3">
              <!-- Source Category -->
              <div>
                <label class="block text-xs font-medium text-loci-gray-500 mb-1">
                  {{ translate('Categorie', 'Category') }}
                </label>
                <select
                  v-model="sourceCategory"
                  class="w-full border border-loci-gray-300 rounded-loci px-3 py-2 bg-loci-white text-loci-black focus:ring-2 focus:ring-loci-yellow focus:border-loci-yellow text-sm"
                >
                  <option value="">{{ translate('Alle categorieën', 'All categories') }}</option>
                  <option v-for="cat in categories" :key="cat" :value="cat">
                    {{ cat }}
                  </option>
                </select>
              </div>

              <!-- Source Document -->
              <div>
                <label class="block text-xs font-medium text-loci-gray-500 mb-1">
                  {{ translate('Document', 'Document') }}
                </label>
                <select
                  v-model="form.sourceId"
                  class="w-full border border-loci-gray-300 rounded-loci px-3 py-2 bg-loci-white text-loci-black focus:ring-2 focus:ring-loci-yellow focus:border-loci-yellow text-sm"
                  required
                >
                  <option value="">{{ translate('Selecteer...', 'Select...') }}</option>
                  <option v-for="doc in sourceDocuments" :key="doc.id" :value="doc.id">
                    {{ doc.title }}
                  </option>
                </select>
              </div>
            </div>
          </div>

          <!-- Relation Type -->
          <div class="flex items-center gap-3">
            <div class="flex-1 h-px bg-loci-gray-200"></div>
            <div class="flex-shrink-0">
              <select
                v-model="form.relationType"
                class="border border-loci-gray-300 rounded-full px-4 py-2 bg-loci-white text-loci-black focus:ring-2 focus:ring-loci-yellow focus:border-loci-yellow text-sm font-medium"
                required
              >
                <option v-for="(label, type) in relationTypes" :key="type" :value="type">
                  {{ label }}
                </option>
              </select>
            </div>
            <div class="flex-1 h-px bg-loci-gray-200"></div>
          </div>

          <!-- Target Section -->
          <div class="p-4 bg-loci-cream rounded-loci">
            <h3 class="text-sm font-medium text-loci-black mb-3 flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-loci-yellow text-loci-black-deep text-xs flex items-center justify-center font-bold">2</span>
              {{ translate('Doeldocument', 'Target document') }}
            </h3>

            <div class="grid grid-cols-2 gap-3">
              <!-- Target Category -->
              <div>
                <label class="block text-xs font-medium text-loci-gray-500 mb-1">
                  {{ translate('Categorie', 'Category') }}
                </label>
                <select
                  v-model="targetCategory"
                  class="w-full border border-loci-gray-300 rounded-loci px-3 py-2 bg-loci-white text-loci-black focus:ring-2 focus:ring-loci-yellow focus:border-loci-yellow text-sm"
                >
                  <option value="">{{ translate('Alle categorieën', 'All categories') }}</option>
                  <option v-for="cat in categories" :key="cat" :value="cat">
                    {{ cat }}
                  </option>
                </select>
              </div>

              <!-- Target Document -->
              <div>
                <label class="block text-xs font-medium text-loci-gray-500 mb-1">
                  {{ translate('Document', 'Document') }}
                </label>
                <select
                  v-model="form.targetId"
                  class="w-full border border-loci-gray-300 rounded-loci px-3 py-2 bg-loci-white text-loci-black focus:ring-2 focus:ring-loci-yellow focus:border-loci-yellow text-sm"
                  required
                >
                  <option value="">{{ translate('Selecteer...', 'Select...') }}</option>
                  <option v-for="doc in targetDocuments" :key="doc.id" :value="doc.id">
                    {{ doc.title }}
                  </option>
                </select>
              </div>
            </div>
          </div>

          <!-- Relation Preview -->
          <div v-if="form.sourceId && form.targetId && form.relationType" class="p-4 bg-loci-yellow/10 border border-loci-yellow rounded-loci">
            <p class="text-sm text-loci-black text-center">
              <span class="font-semibold">{{ getDocTitle(form.sourceId) }}</span>
              <span class="mx-2 px-2 py-0.5 bg-loci-yellow rounded-full text-xs font-medium">
                {{ relationTypes[form.relationType] }}
              </span>
              <span class="font-semibold">{{ getDocTitle(form.targetId) }}</span>
            </p>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button
            type="button"
            class="px-5 py-2 text-loci-black hover:bg-loci-gray-50 rounded-loci-full border border-loci-gray-200 font-medium transition-colors"
            @click="$emit('close')"
          >
            {{ translate('Annuleren', 'Cancel') }}
          </button>
          <button
            type="submit"
            class="px-5 py-2 bg-loci-yellow text-loci-black-deep rounded-loci-full font-semibold hover:bg-loci-yellow-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!isValid || isSubmitting"
          >
            {{ isSubmitting ? translate('Bezig...', 'Processing...') : translate('Toevoegen', 'Add') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Document } from '~/types/Kennisbank';

const props = defineProps<{
  documents: Document[];
  relationTypes: Record<string, string>;
}>();

const emit = defineEmits<{
  close: [];
  create: [{ sourceId: number; targetId: number; relationType: string }];
}>();

const { translate } = useTranslations();

const isSubmitting = ref(false);
const sourceCategory = ref('');
const targetCategory = ref('');

const form = reactive({
  sourceId: null as number | null,
  targetId: null as number | null,
  relationType: 'references',
});

// Get unique categories from documents
const categories = computed(() => {
  const cats = new Set<string>();
  props.documents.forEach(doc => {
    if (doc.category) {
      cats.add(doc.category);
    }
  });
  return Array.from(cats).sort();
});

// Filter source documents by category
const sourceDocuments = computed(() => {
  if (!sourceCategory.value) {
    return props.documents;
  }
  return props.documents.filter(doc => doc.category === sourceCategory.value);
});

// Filter target documents by category and exclude source
const targetDocuments = computed(() => {
  let docs = props.documents.filter(doc => doc.id !== form.sourceId);
  if (targetCategory.value) {
    docs = docs.filter(doc => doc.category === targetCategory.value);
  }
  return docs;
});

// Reset source document when category changes
watch(sourceCategory, () => {
  form.sourceId = null;
});

// Reset target document when category changes
watch(targetCategory, () => {
  form.targetId = null;
});

// Reset target if it becomes the same as source
watch(() => form.sourceId, (newSourceId) => {
  if (form.targetId === newSourceId) {
    form.targetId = null;
  }
});

const isValid = computed(() => {
  return form.sourceId && form.targetId && form.relationType && form.sourceId !== form.targetId;
});

function getDocTitle(id: number | null): string {
  if (!id) return '';
  const doc = props.documents.find(d => d.id === id);
  return doc?.title || '';
}

async function handleSubmit() {
  if (!isValid.value) return;

  isSubmitting.value = true;
  try {
    emit('create', {
      sourceId: form.sourceId!,
      targetId: form.targetId!,
      relationType: form.relationType,
    });
  } finally {
    isSubmitting.value = false;
  }
}
</script>
