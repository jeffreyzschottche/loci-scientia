/**
 * Multilingual translations composable for Vue frontend.
 * Supports Dutch (nl) and English (en).
 */

interface Translations {
  [key: string]: {
    nl: string;
    en: string;
  };
}

const translations: Translations = {
  // Navigation
  not_logged_in: {
    nl: "Niet ingelogd",
    en: "Not logged in",
  },
  kennisbank: {
    nl: "Kennisbank",
    en: "Knowledge Bank",
  },

  // Kennisbank page
  pushing: {
    nl: "Pushen...",
    en: "Pushing...",
  },
  push_to_git: {
    nl: "Sync naar OS",
    en: "Sync to OS",
  },
  upload_document: {
    nl: "Document Uploaden",
    en: "Upload Document",
  },
  click_to_upload: {
    nl: "Klik om te uploaden",
    en: "Click to upload",
  },
  coming_soon: {
    nl: "Binnenkort",
    en: "Coming soon",
  },
  uploading: {
    nl: "Uploaden...",
    en: "Uploading...",
  },
  documents: {
    nl: "Documenten",
    en: "Documents",
  },
  no_documents_yet: {
    nl: "Nog geen documenten geüpload.",
    en: "No documents uploaded yet.",
  },
  document: {
    nl: "Document",
    en: "Document",
  },
  size: {
    nl: "Grootte",
    en: "Size",
  },
  status: {
    nl: "Status",
    en: "Status",
  },
  chunks: {
    nl: "Chunks",
    en: "Chunks",
  },
  date: {
    nl: "Datum",
    en: "Date",
  },
  actions: {
    nl: "Acties",
    en: "Actions",
  },
  processing: {
    nl: "Bezig...",
    en: "Processing...",
  },
  embed: {
    nl: "Embedden",
    en: "Embed",
  },
  delete: {
    nl: "Verwijder",
    en: "Delete",
  },
  git_configuration: {
    nl: "Git Configuratie",
    en: "Git Configuration",
  },
  save_configuration: {
    nl: "Configuratie Opslaan",
    en: "Save Configuration",
  },
  saving: {
    nl: "Opslaan...",
    en: "Saving...",
  },
  syncing: {
    nl: "Syncen...",
    en: "Syncing...",
  },
  last_pushed: {
    nl: "Laatst gepusht:",
    en: "Last pushed:",
  },
  git_repo_url: {
    nl: "GitHub repo URL",
    en: "GitHub repo URL",
  },
  git_branch: {
    nl: "Branch",
    en: "Branch",
  },
  git_access_token: {
    nl: "GitHub token (PAT)",
    en: "GitHub token (PAT)",
  },
  git_last_synced: {
    nl: "Laatst gesynct",
    en: "Last synced",
  },
  git_token_hint: {
    nl: "Laat leeg om het bestaande token te behouden",
    en: "Leave empty to keep the existing token",
  },
  git_config_required: {
    nl: "Vul eerst je Git-configuratie in.",
    en: "Please configure Git first.",
  },
  error_loading_documents: {
    nl: "Fout bij laden documenten",
    en: "Error loading documents",
  },
  upload_failed: {
    nl: "Upload mislukt",
    en: "Upload failed",
  },
  uploaded: {
    nl: "geüpload",
    en: "uploaded",
  },
  document_embedded: {
    nl: "Document embedded",
    en: "Document embedded",
  },
  embedding_failed: {
    nl: "Embedding mislukt",
    en: "Embedding failed",
  },
  confirm_delete: {
    nl: "Weet je zeker dat je dit document wilt verwijderen?",
    en: "Are you sure you want to delete this document?",
  },
  document_deleted: {
    nl: "Document verwijderd",
    en: "Document deleted",
  },
  delete_failed: {
    nl: "Verwijderen mislukt",
    en: "Delete failed",
  },
  git_config_saved: {
    nl: "Git configuratie opgeslagen",
    en: "Git configuration saved",
  },
  save_failed: {
    nl: "Opslaan mislukt",
    en: "Save failed",
  },
  push_failed: {
    nl: "Push mislukt",
    en: "Push failed",
  },

  // Status labels
  status_uploaded: {
    nl: "Geüpload",
    en: "Uploaded",
  },
  status_processing: {
    nl: "Verwerken...",
    en: "Processing...",
  },
  status_embedded: {
    nl: "Embedded",
    en: "Embedded",
  },
  status_failed: {
    nl: "Mislukt",
    en: "Failed",
  },
};

// Global reactive language state
const currentLanguage = ref<"nl" | "en">("nl");

/**
 * Check if we should use English based on environment or localStorage
 */
function detectLanguage(): "nl" | "en" {
  // Check localStorage first (client-side only)
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("language");
    if (stored === "en-US" || stored === "en") {
      return "en";
    }
    if (stored === "nl-NL" || stored === "nl") {
      return "nl";
    }
  }
  return "nl";
}

/**
 * Set the current language
 */
function setLanguage(lang: "nl" | "en") {
  currentLanguage.value = lang;
  if (typeof window !== "undefined") {
    localStorage.setItem("language", lang === "en" ? "en-US" : "nl-NL");
  }
}

/**
 * Quick inline translation helper for components
 */
function translate(nl: string, en?: string) {
  if (currentLanguage.value === "nl") {
    return nl;
  }
  return en ?? nl;
}

/**
 * Get translated text
 */
function t(key: string, replacements?: Record<string, string>): string {
  const lang = currentLanguage.value;

  if (!(key in translations)) {
    return key;
  }

  let text = translations[key][lang] || translations[key].nl || key;

  if (replacements) {
    Object.entries(replacements).forEach(([k, v]) => {
      text = text.replace(new RegExp(`{${k}}`, "g"), v);
    });
  }

  return text;
}

export function useTranslations() {
  // Initialize language on first use
  onMounted(() => {
    currentLanguage.value = detectLanguage();
  });

  return {
    t,
    translate,
    currentLanguage: readonly(currentLanguage),
    setLanguage,
    isEnglish: computed(() => currentLanguage.value === "en"),
    isDutch: computed(() => currentLanguage.value === "nl"),
  };
}
