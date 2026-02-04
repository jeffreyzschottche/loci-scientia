<template>
  <KennisbankTabLayout>
    <div>
      <div class="flex justify-between items-center mb-6">
        <div>
          <h1 class="text-2xl font-bold text-loci-black">
            {{ translate('Prioriteitsmanager', 'Priority manager') }}
          </h1>
          <p class="text-sm text-loci-gray-500 mt-1">
            {{ translate('Bepaal de prioriteit van documenten per categorie. Sleep documenten of wijzig de nummers.', 'Set document priorities per category. Drag items or edit the numbers.') }}
          </p>
        </div>
      </div>

      <!-- Loading state -->
      <div v-if="isLoading" class="text-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-loci-yellow mx-auto"></div>
        <p class="mt-4 text-loci-gray-500">{{ translate('Laden...', 'Loading...') }}</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="Object.keys(priorityCategories).length === 0" class="text-center py-12 bg-loci-white rounded-loci-lg border border-loci-gray-100">
        <svg class="mx-auto h-12 w-12 text-loci-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-loci-black">{{ translate('Geen documenten', 'No documents') }}</h3>
        <p class="mt-1 text-sm text-loci-gray-500">
          {{ translate('Upload eerst documenten om prioriteiten te kunnen instellen.', 'Upload documents before setting priorities.') }}
        </p>
      </div>

      <!-- Category columns -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="(docs, category) in priorityCategories"
          :key="category"
          class="bg-loci-white rounded-loci-lg border border-loci-gray-100"
        >
          <div class="px-4 py-3 border-b border-loci-gray-100 bg-loci-gray-50 rounded-t-loci-lg">
            <h2 class="font-medium text-loci-black">{{ category }}</h2>
            <p class="text-sm text-loci-gray-500">
              {{ docs.length }} {{ translate('documenten', 'documents') }}
            </p>
          </div>

          <draggable
            v-model="priorityCategories[category]"
            item-key="id"
            class="p-4 space-y-2 min-h-[200px]"
            ghost-class="opacity-50"
            @end="() => handleDragEnd(category)"
          >
            <template #item="{ element, index }">
              <div
                class="flex items-center gap-3 p-3 bg-loci-gray-50 rounded-loci border border-loci-gray-100 cursor-move hover:bg-loci-yellow/10 transition-colors"
              >
                <!-- Priority badge -->
                <span
                  class="w-8 h-8 flex items-center justify-center bg-loci-yellow text-loci-black-deep rounded-full text-sm font-semibold flex-shrink-0"
                >
                  {{ index + 1 }}
                </span>

                <!-- Document info -->
                <div class="flex-1 min-w-0">
                  <p class="font-medium text-loci-black truncate">{{ element.title }}</p>
                  <p class="text-xs text-loci-gray-500">
                    {{ translate('Huidige prioriteit', 'Current priority') }}:
                    {{ element.priority || translate('niet ingesteld', 'not set') }}
                  </p>
                </div>

                <!-- Drag handle -->
                <div class="flex items-center gap-2 flex-shrink-0">
                  <input
                    v-model.number="element.priority"
                    type="number"
                    min="0"
                    class="w-16 px-2 py-1 border border-loci-gray-300 rounded-loci text-center text-sm focus:border-loci-yellow focus:outline-none bg-loci-cream"
                    @change="() => handlePriorityInput(element)"
                  >
                  <svg class="w-5 h-5 text-loci-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16" />
                  </svg>
                </div>
              </div>
            </template>
          </draggable>
        </div>
      </div>

      <!-- Save button (sticky footer) -->
      <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 translate-y-4"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 translate-y-4"
      >
        <div v-if="hasChanges" class="fixed bottom-6 right-6 flex items-center gap-4">
          <span class="text-sm text-loci-gray-500 bg-loci-white px-3 py-2 rounded-full border border-loci-gray-100">
            {{ pendingChanges.size }} {{ translate('wijzigingen', 'changes') }}
          </span>
          <button
            class="px-6 py-3 bg-loci-yellow text-loci-black-deep rounded-loci-full font-semibold shadow-lg hover:bg-loci-yellow-hover transition-all flex items-center gap-2 disabled:bg-loci-yellow-light disabled:text-loci-gray-400"
            :disabled="isSaving"
            @click="saveAllChanges"
          >
            <svg v-if="isSaving" class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>{{ isSaving ? translate('Opslaan...', 'Saving...') : translate('Wijzigingen Opslaan', 'Save changes') }}</span>
          </button>
        </div>
      </Transition>
    </div>
  </KennisbankTabLayout>
  <teleport to="body">
    <div
      v-if="showUnsavedModal"
      class="fixed inset-0 z-50 flex items-center justify-center px-4"
    >
      <div
        class="absolute inset-0 bg-loci-black/60"
        aria-hidden="true"
        @click="stayOnPage"
      />

      <div
        class="relative w-full max-w-lg bg-loci-white border border-loci-gray-100 rounded-loci-lg shadow-2xl p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="unsaved-modal-title"
        aria-describedby="unsaved-modal-desc"
        tabindex="-1"
      >
        <div class="flex items-start gap-4">
          <div class="flex h-12 w-12 items-center justify-center rounded-full bg-loci-yellow text-loci-black text-xl font-semibold">
            !
          </div>
          <div class="flex-1">
            <h3 id="unsaved-modal-title" class="text-lg font-semibold text-loci-black">
              {{ translate('Onopgeslagen wijzigingen', 'Unsaved changes') }}
            </h3>
            <p id="unsaved-modal-desc" class="mt-2 text-sm text-loci-gray-500">
              {{ translate('Je hebt onopgeslagen wijzigingen. Wil je deze pagina verlaten zonder op te slaan?', 'You have unsaved changes. Leave this page without saving?') }}
            </p>
          </div>
          <button
            type="button"
            class="text-loci-gray-400 hover:text-loci-black"
            :aria-label="translate('Sluiten', 'Close')"
            @click="stayOnPage"
          >
            <span aria-hidden="true">&times;</span>
          </button>
        </div>

        <div class="mt-6 flex justify-end gap-3">
          <button
            type="button"
            class="px-5 py-2 rounded-loci-full border border-loci-gray-200 text-loci-gray-500 hover:text-loci-black hover:border-loci-gray-400 transition"
            @click="stayOnPage"
          >
            {{ translate('Blijven', 'Stay') }}
          </button>
          <button
            type="button"
            class="px-5 py-2 rounded-loci-full bg-loci-black text-loci-white font-semibold hover:bg-loci-black-deep transition"
            @click="leaveWithoutSaving"
          >
            {{ translate('Toch verlaten', 'Leave anyway') }}
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import draggable from 'vuedraggable';
import type { Document } from '~/types/Kennisbank';

definePageMeta({
  middleware: 'auth',
});

const router = useRouter();
const store = useKennisbankStore();
const { priorityCategories, isLoading } = storeToRefs(store);
const { translate } = useTranslations();

const hasChanges = ref(false);
const isSaving = ref(false);
const pendingChanges = ref<Map<number, number>>(new Map());
const showUnsavedModal = ref(false);
const pendingRoutePath = ref<string | null>(null);
const allowRouteLeave = ref(false);

function handleDragEnd(category: string) {
  // Update priorities based on new order
  const docs = priorityCategories.value[category];
  if (!docs) return;

  docs.forEach((doc, index) => {
    const newPriority = index + 1;
    if (doc.priority !== newPriority) {
      doc.priority = newPriority;
      pendingChanges.value.set(doc.id, newPriority);
    }
  });

  hasChanges.value = pendingChanges.value.size > 0;
}

function handlePriorityInput(doc: Document) {
  pendingChanges.value.set(doc.id, doc.priority);
  hasChanges.value = true;
}

async function saveAllChanges() {
  if (pendingChanges.value.size === 0) return;

  isSaving.value = true;

  try {
    const priorities = Array.from(pendingChanges.value.entries()).map(([id, priority]) => ({
      id,
      priority,
    }));

    await store.bulkUpdatePriorities(priorities);
    pendingChanges.value.clear();
    hasChanges.value = false;
  } catch (error) {
    console.error('Failed to save priorities:', error);
  } finally {
    isSaving.value = false;
  }
}

// Warn before leaving with unsaved changes
onBeforeRouteLeave((to, from, next) => {
  if (!hasChanges.value || allowRouteLeave.value) {
    allowRouteLeave.value = false;
    next();
    return;
  }

  pendingRoutePath.value = to.fullPath;
  showUnsavedModal.value = true;
  next(false);
});

onMounted(async () => {
  await store.fetchPriorities();
});

function stayOnPage() {
  showUnsavedModal.value = false;
  pendingRoutePath.value = null;
}

function leaveWithoutSaving() {
  const destination = pendingRoutePath.value;
  showUnsavedModal.value = false;
  pendingRoutePath.value = null;

  if (!destination) return;
  allowRouteLeave.value = true;
  router.push(destination);
}
</script>

<style scoped>
.sortable-ghost {
  opacity: 0.5;
  background: #c8ebfb;
}
</style>
