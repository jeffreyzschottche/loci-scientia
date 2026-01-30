<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
      <h2 class="text-lg font-semibold mb-4">Nieuwe Relatie Toevoegen</h2>

      <form @submit.prevent="handleSubmit">
        <div class="space-y-4">
          <!-- Source Document -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Brondocument
            </label>
            <select
              v-model="form.sourceId"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            >
              <option value="">Selecteer document...</option>
              <option v-for="doc in documents" :key="doc.id" :value="doc.id">
                {{ doc.title }}
              </option>
            </select>
          </div>

          <!-- Relation Type -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Relatietype
            </label>
            <select
              v-model="form.relationType"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            >
              <option v-for="(label, type) in relationTypes" :key="type" :value="type">
                {{ label }}
              </option>
            </select>
          </div>

          <!-- Target Document -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Doeldocument
            </label>
            <select
              v-model="form.targetId"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            >
              <option value="">Selecteer document...</option>
              <option
                v-for="doc in availableTargets"
                :key="doc.id"
                :value="doc.id"
              >
                {{ doc.title }}
              </option>
            </select>
          </div>

          <!-- Relation explanation -->
          <div v-if="form.sourceId && form.targetId && form.relationType" class="p-3 bg-gray-50 rounded-lg">
            <p class="text-sm text-gray-600">
              <span class="font-medium">{{ getDocTitle(form.sourceId) }}</span>
              <span class="text-blue-600 mx-1">{{ relationTypes[form.relationType] }}</span>
              <span class="font-medium">{{ getDocTitle(form.targetId) }}</span>
            </p>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button
            type="button"
            class="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            @click="$emit('close')"
          >
            Annuleren
          </button>
          <button
            type="submit"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!isValid || isSubmitting"
          >
            {{ isSubmitting ? 'Bezig...' : 'Toevoegen' }}
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

const isSubmitting = ref(false);

const form = reactive({
  sourceId: null as number | null,
  targetId: null as number | null,
  relationType: 'references',
});

// Filter out source document from target options
const availableTargets = computed(() => {
  return props.documents.filter(doc => doc.id !== form.sourceId);
});

const isValid = computed(() => {
  return form.sourceId && form.targetId && form.relationType;
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
