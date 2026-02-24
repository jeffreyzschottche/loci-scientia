"""
Multilingual translations for the AITJE application.
Supports Dutch (nl) and English (en).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

# Global language setting - default to Dutch
_current_language: str = "nl"
_language_change_callbacks: list[Callable[[], None]] = []

TRANSLATIONS = {
    # ============================================
    # HEADERBAR
    # ============================================
    "subtitle_local_ai_console": {
        "nl": "Lokale AI-console",
        "en": "Local AI Console",
    },
    "online": {
        "nl": "ONLINE",
        "en": "ONLINE",
    },
    "offline": {
        "nl": "OFFLINE",
        "en": "OFFLINE",
    },

    # ============================================
    # SIDEBAR
    # ============================================
    "sidebar_subtitle": {
        "nl": "Lokale AI console",
        "en": "Local AI Console",
    },
    "nav_chat": {
        "nl": "Chat",
        "en": "Chat",
    },
    "nav_knowledge_bank": {
        "nl": "Kennisbank",
        "en": "Knowledge Bank",
    },
    "nav_maps": {
        "nl": "Maps",
        "en": "Maps",
    },
    "nav_contacts": {
        "nl": "Contacten",
        "en": "Contacts",
    },
    "nav_network": {
        "nl": "Netwerk",
        "en": "Network",
    },
    "nav_devices": {
        "nl": "Connected Devices",
        "en": "Connected Devices",
    },
    "nav_settings": {
        "nl": "Instellingen",
        "en": "Settings",
    },

    # ============================================
    # BOOT SCREEN
    # ============================================
    "boot_starting": {
        "nl": "Lokale AI wordt opgestart...",
        "en": "Starting local AI...",
    },
    "boot_loading_neural": {
        "nl": "Neurale netwerken laden...",
        "en": "Loading neural networks...",
    },
    "boot_preparing_api": {
        "nl": "API endpoints voorbereiden...",
        "en": "Preparing API endpoints...",
    },
    "boot_syncing_devices": {
        "nl": "Devices synchroniseren...",
        "en": "Synchronizing devices...",
    },
    "boot_almost_ready": {
        "nl": "Bijna klaar...",
        "en": "Almost ready...",
    },
    "boot_welcome": {
        "nl": "Welkom! ✓",
        "en": "Welcome! ✓",
    },
    "boot_title": {
        "nl": "AITJE ontwaakt...",
        "en": "AITJE is waking up...",
    },
    "boot_subtitle": {
        "nl": "De antwoorden van het universum worden lokaal opgestart.",
        "en": "The answers of the universe are starting up locally.",
    },

    # ============================================
    # PAGE TITLES
    # ============================================
    "page_title_chat": {
        "nl": "Chat Assistant",
        "en": "Chat Assistant",
    },
    "page_title_kb": {
        "nl": "Kennisbank",
        "en": "Knowledge Bank",
    },
    "page_title_maps": {
        "nl": "Maps",
        "en": "Maps",
    },
    "page_title_contacts": {
        "nl": "Contacten",
        "en": "Contacts",
    },
    "page_title_net": {
        "nl": "Netwerk",
        "en": "Network",
    },
    "page_title_devices": {
        "nl": "Connected Devices & Gebruikersbeheer",
        "en": "Connected Devices & User Management",
    },
    "page_title_settings": {
        "nl": "Instellingen",
        "en": "Settings",
    },

    # ============================================
    # PAGE SUBTITLES
    # ============================================
    "page_subtitle_chat": {
        "nl": "Start een gesprek met je lokale AI-assistent",
        "en": "Start a conversation with your local AI assistant",
    },
    "page_subtitle_kb": {
        "nl": "Beheer kennisbankdocumenten en SD-kaartopslag",
        "en": "Manage knowledge bank documents and SD card storage",
    },
    "page_subtitle_maps": {
        "nl": "Bekijk contactlocaties op de kaart",
        "en": "View contact locations on the map",
    },
    "page_subtitle_contacts": {
        "nl": "Beheer je contacten en bekijk ze op de kaart",
        "en": "Manage your contacts and view them on the map",
    },
    "page_subtitle_net": {
        "nl": "Realtime overzicht van netwerk- en systeemstatus",
        "en": "Real-time overview of network and system status",
    },
    "page_subtitle_devices": {
        "nl": "Beheer verbonden apparaten en gebruikersaccounts voor het systeem",
        "en": "Manage connected devices and user accounts for the system",
    },
    "page_subtitle_settings": {
        "nl": "Beheer de systeeminstellingen en voorkeuren voor AITJE OS",
        "en": "Manage system settings and preferences for AITJE OS",
    },

    # ============================================
    # DIALOG BUTTONS
    # ============================================
    "ok": {
        "nl": "Oké",
        "en": "OK",
    },
    "yes": {
        "nl": "Ja",
        "en": "Yes",
    },
    "no": {
        "nl": "Nee",
        "en": "No",
    },
    "cancel": {
        "nl": "Annuleren",
        "en": "Cancel",
    },
    "save": {
        "nl": "Opslaan",
        "en": "Save",
    },
    "delete": {
        "nl": "Verwijder",
        "en": "Delete",
    },
    "edit": {
        "nl": "Bewerk",
        "en": "Edit",
    },
    "confirm": {
        "nl": "Bevestig",
        "en": "Confirm",
    },
    "error": {
        "nl": "Fout",
        "en": "Error",
    },
    "invalid": {
        "nl": "Ongeldig",
        "en": "Invalid",
    },

    # ============================================
    # SETTINGS PAGE
    # ============================================
    "settings_tab_system": {
        "nl": "Systeem",
        "en": "System",
    },
    "settings_tab_advanced": {
        "nl": "Geavanceerd",
        "en": "Advanced",
    },
    "settings_timezone": {
        "nl": "Tijdzone",
        "en": "Timezone",
    },
    "settings_language": {
        "nl": "Taal",
        "en": "Language",
    },
    "settings_duration": {
        "nl": "Duur",
        "en": "Duration",
    },
    "settings_30_min": {
        "nl": "30 min",
        "en": "30 min",
    },
    "settings_1_hour": {
        "nl": "1 uur",
        "en": "1 hour",
    },
    "settings_4_hours": {
        "nl": "4 uur",
        "en": "4 hours",
    },
    "settings_loading_models": {
        "nl": "Beschikbare modellen laden...",
        "en": "Loading available models...",
    },
    "settings_support_hint": {
        "nl": "Schakel alleen in met expliciete toestemming van de klant. We starten tijdelijk een Tailscale-verbinding voor support en sluiten automatisch.",
        "en": "Enable only with explicit customer permission. We temporarily start a Tailscale connection for support and close automatically.",
    },
    "settings_support_status_loading": {
        "nl": "Support status laden...",
        "en": "Loading support status...",
    },
    "settings_enable_support": {
        "nl": "Activeer ondersteuning",
        "en": "Enable support",
    },
    "settings_stop_support": {
        "nl": "Stop ondersteuning",
        "en": "Stop support",
    },
    "settings_could_not_save_timezone": {
        "nl": "Kon tijdzone niet opslaan:",
        "en": "Could not save timezone:",
    },
    "settings_could_not_save_language": {
        "nl": "Kon taal niet opslaan:",
        "en": "Could not save language:",
    },
    "settings_backend_not_reachable": {
        "nl": "Backend niet bereikbaar; lokaal modellenlijstje geladen.",
        "en": "Backend not reachable; loaded local model list.",
    },
    "settings_could_not_fetch_models": {
        "nl": "Kon modellen niet ophalen:",
        "en": "Could not fetch models:",
    },
    "settings_current_model": {
        "nl": "Huidig model:",
        "en": "Current model:",
    },
    "settings_no_active_model": {
        "nl": "Geen actief model ingesteld.",
        "en": "No active model set.",
    },
    "settings_model_already_active": {
        "nl": "Model {model} is al actief.",
        "en": "Model {model} is already active.",
    },
    "settings_ollama_fetching": {
        "nl": "Ollama haalt {model} op...",
        "en": "Ollama is fetching {model}...",
    },
    "settings_switch_failed": {
        "nl": "Switchen mislukt:",
        "en": "Switch failed:",
    },
    "settings_ollama_busy": {
        "nl": "Ollama bezig",
        "en": "Ollama busy",
    },
    "settings_could_not_load_support": {
        "nl": "Kon support status niet laden:",
        "en": "Could not load support status:",
    },
    "settings_enable_remote_support": {
        "nl": "Remote support inschakelen",
        "en": "Enable remote support",
    },
    "settings_enable_remote_support_confirm": {
        "nl": "Dit opent tijdelijke SSH-toegang voor support. Schakel alleen in met expliciete toestemming. Doorgaan?",
        "en": "This opens temporary SSH access for support. Enable only with explicit permission. Continue?",
    },
    "settings_activating_support": {
        "nl": "Ondersteuning activeren...",
        "en": "Activating support...",
    },
    "settings_disable_remote_support": {
        "nl": "Remote support uitschakelen",
        "en": "Disable remote support",
    },
    "settings_disable_remote_support_confirm": {
        "nl": "Weet je zeker dat je de supporttoegang wilt afsluiten?",
        "en": "Are you sure you want to close support access?",
    },
    "settings_closing_support": {
        "nl": "Ondersteuning afsluiten...",
        "en": "Closing support...",
    },
    "settings_bearer_token_required": {
        "nl": "Backend verwacht een Bearer token. Stel BACKEND_BEARER_TOKEN in op het apparaat.",
        "en": "Backend expects a Bearer token. Set BACKEND_BEARER_TOKEN on the device.",
    },
    "settings_active": {
        "nl": "Actief",
        "en": "Active",
    },
    "settings_until": {
        "nl": "tot",
        "en": "until",
    },
    "settings_session": {
        "nl": "sessie",
        "en": "session",
    },
    "settings_disabled": {
        "nl": "Uitgeschakeld",
        "en": "Disabled",
    },
    "settings_last_error": {
        "nl": "laatste fout:",
        "en": "last error:",
    },
    "settings_use": {
        "nl": "Gebruik",
        "en": "Use",
    },

    # ============================================
    # DEVICES PAGE
    # ============================================
    "devices_unknown_device": {
        "nl": "Onbekend apparaat",
        "en": "Unknown device",
    },
    "devices_add_device": {
        "nl": "+ Apparaat toevoegen",
        "en": "+ Add Device",
    },
    "devices_total_devices": {
        "nl": "Totaal: {count} apparaten",
        "en": "Total: {count} devices",
    },
    "devices_no_devices_found": {
        "nl": "Geen apparaten gevonden.",
        "en": "No devices found.",
    },
    "devices_edit_device": {
        "nl": "Apparaat bewerken",
        "en": "Edit Device",
    },
    "devices_new_device_user": {
        "nl": "Nieuw apparaat & gebruiker",
        "en": "New device & user",
    },
    "devices_show": {
        "nl": "Toon",
        "en": "Show",
    },
    "devices_hide": {
        "nl": "Verberg",
        "en": "Hide",
    },
    "devices_username": {
        "nl": "Naam gebruiker",
        "en": "Username",
    },
    "devices_email": {
        "nl": "E-mail",
        "en": "Email",
    },
    "devices_password": {
        "nl": "Wachtwoord",
        "en": "Password",
    },
    "devices_repeat_password": {
        "nl": "Herhaal wachtwoord",
        "en": "Repeat password",
    },
    "devices_phone": {
        "nl": "Telefoon (06)",
        "en": "Phone",
    },
    "devices_device_name": {
        "nl": "Device naam",
        "en": "Device name",
    },
    "devices_username_device_required": {
        "nl": "Naam gebruiker en device naam zijn verplicht.",
        "en": "Username and device name are required.",
    },
    "devices_passwords_dont_match": {
        "nl": "De wachtwoorden komen niet overeen.",
        "en": "Passwords do not match.",
    },
    "devices_could_not_save": {
        "nl": "Device kon niet worden opgeslagen:",
        "en": "Device could not be saved:",
    },
    "devices_confirm_delete": {
        "nl": "Weet je zeker dat je '{device_name}' wilt verwijderen?",
        "en": "Are you sure you want to delete '{device_name}'?",
    },
    "devices_could_not_delete": {
        "nl": "Device kon niet worden verwijderd:",
        "en": "Device could not be deleted:",
    },

    # ============================================
    # CONTACTS PAGE
    # ============================================
    "contacts_unknown": {
        "nl": "Onbekend",
        "en": "Unknown",
    },
    "contacts_no_location_linked": {
        "nl": "Geen locatie gekoppeld",
        "en": "No location linked",
    },
    "contacts_on_map": {
        "nl": "Op kaart",
        "en": "On map",
    },
    "contacts_link_location": {
        "nl": "Locatie koppelen",
        "en": "Link location",
    },
    "contacts_add_contact": {
        "nl": "+ Contact toevoegen",
        "en": "+ Add Contact",
    },
    "contacts_search": {
        "nl": "Zoek contacten…",
        "en": "Search contacts…",
    },
    "contacts_total": {
        "nl": "Totaal: {count} contacten",
        "en": "Total: {count} contacts",
    },
    "contacts_no_contacts_found": {
        "nl": "Geen contacten gevonden.",
        "en": "No contacts found.",
    },
    "contacts_no_location": {
        "nl": "Geen locatie",
        "en": "No location",
    },
    "contacts_no_gps_location": {
        "nl": "Dit contact heeft nog geen GPS-locatie.",
        "en": "This contact doesn't have a GPS location yet.",
    },
    "contacts_could_not_save": {
        "nl": "Contact kon niet worden opgeslagen:",
        "en": "Contact could not be saved:",
    },
    "contacts_edit_contact": {
        "nl": "Contact bewerken",
        "en": "Edit Contact",
    },
    "contacts_could_not_update": {
        "nl": "Contact kon niet worden bijgewerkt:",
        "en": "Contact could not be updated:",
    },
    "contacts_confirm_delete": {
        "nl": "Weet je zeker dat je {name} wilt verwijderen?",
        "en": "Are you sure you want to delete {name}?",
    },
    "contacts_could_not_delete": {
        "nl": "Kon contact niet verwijderen:",
        "en": "Could not delete contact:",
    },
    "contacts_add_location": {
        "nl": "Locatie toevoegen",
        "en": "Add location",
    },
    "contacts_add_location_confirm": {
        "nl": "Wil je via de kaart een locatie koppelen?",
        "en": "Do you want to link a location via the map?",
    },

    # ============================================
    # CONTACT FORM
    # ============================================
    "contact_form_new_contact": {
        "nl": "Nieuw contact",
        "en": "New contact",
    },
    "contact_form_name": {
        "nl": "Naam",
        "en": "Name",
    },
    "contact_form_company": {
        "nl": "Bedrijf",
        "en": "Company",
    },
    "contact_form_email": {
        "nl": "E-mail",
        "en": "Email",
    },
    "contact_form_phone": {
        "nl": "Telefoon",
        "en": "Phone",
    },
    "contact_form_notes": {
        "nl": "Notities",
        "en": "Notes",
    },
    "contact_form_label": {
        "nl": "Label",
        "en": "Label",
    },
    "contact_form_street": {
        "nl": "Straat",
        "en": "Street",
    },
    "contact_form_city": {
        "nl": "Plaats",
        "en": "City",
    },
    "contact_form_region": {
        "nl": "Regio",
        "en": "Region",
    },
    "contact_form_country": {
        "nl": "Land",
        "en": "Country",
    },
    "contact_form_context": {
        "nl": "Context",
        "en": "Context",
    },
    "contact_form_save_map": {
        "nl": "Opslaan + kaart",
        "en": "Save + map",
    },
    "contact_form_name_required": {
        "nl": "Naam is verplicht.",
        "en": "Name is required.",
    },

    # ============================================
    # NETWORK PAGE
    # ============================================
    "network_total_today": {
        "nl": "TOTAAL VANDAAG",
        "en": "TOTAL TODAY",
    },
    "network_api_usage": {
        "nl": "Hoe vaak de API is gebruikt.",
        "en": "How often the API was used.",
    },
    "network_active_users": {
        "nl": "ACTIEVE GEBRUIKERS",
        "en": "ACTIVE USERS",
    },
    "network_customers_apps": {
        "nl": "Aantal klanten of apps vandaag.",
        "en": "Number of customers or apps today.",
    },
    "network_avg_response_time": {
        "nl": "GEM. REACTIETIJD",
        "en": "AVG. RESPONSE TIME",
    },
    "network_avg_wait_time": {
        "nl": "Gemiddelde wachttijd.",
        "en": "Average wait time.",
    },
    "network_na": {
        "nl": "n.v.t.",
        "en": "N/A",
    },
    "network_no_measurements": {
        "nl": "Nog geen metingen.",
        "en": "No measurements yet.",
    },
    "network_open_wifi_config": {
        "nl": "Open WiFi configuratie",
        "en": "Open WiFi configuration",
    },

    # ============================================
    # KNOWLEDGE PAGE
    # ============================================
    "kb_upload_document": {
        "nl": "⬆ Upload Document",
        "en": "⬆ Upload Document",
    },
    "kb_sd_card_capacity": {
        "nl": "SD Kaart Capaciteit",
        "en": "SD Card Capacity",
    },
    "kb_used": {
        "nl": "{used} GB gebruikt ({percent}%)",
        "en": "{used} GB used ({percent}%)",
    },
    "kb_knowledge_bank_size": {
        "nl": "Kennisbank Grootte",
        "en": "Knowledge Bank Size",
    },
    "kb_available": {
        "nl": "Beschikbaar: {available} GB",
        "en": "Available: {available} GB",
    },
    "kb_total_documents": {
        "nl": "Totaal Documenten",
        "en": "Total Documents",
    },
    "kb_indexed": {
        "nl": "{count} geïndexeerd",
        "en": "{count} indexed",
    },
    "kb_vector_db_status": {
        "nl": "Vector Database Status",
        "en": "Vector Database Status",
    },
    "kb_vector_db_title": {
        "nl": "Vector Database Status",
        "en": "Vector Database Status",
    },
    "kb_total_vectors": {
        "nl": "Totaal Vectors",
        "en": "Total Vectors",
    },
    "kb_embedding_model": {
        "nl": "Embedding Model",
        "en": "Embedding Model",
    },
    "kb_database_engine": {
        "nl": "Database Engine",
        "en": "Database Engine",
    },
    "kb_index_status": {
        "nl": "Index Status",
        "en": "Index Status",
    },
    "kb_optimal": {
        "nl": "Optimaal",
        "en": "Optimal",
    },
    "kb_documents": {
        "nl": "Kennisbank Documenten",
        "en": "Knowledge Bank Documents",
    },
    "kb_document": {
        "nl": "Document",
        "en": "Document",
    },
    "kb_type": {
        "nl": "Type",
        "en": "Type",
    },
    "kb_size": {
        "nl": "Grootte",
        "en": "Size",
    },
    "kb_status": {
        "nl": "Status",
        "en": "Status",
    },
    "kb_vectors": {
        "nl": "Vectors",
        "en": "Vectors",
    },
    "kb_upload_date": {
        "nl": "Upload Datum",
        "en": "Upload Date",
    },
    "kb_indexed_status": {
        "nl": "Geïndexeerd",
        "en": "Indexed",
    },
    "kb_processing": {
        "nl": "Verwerken…",
        "en": "Processing…",
    },
    # Additional keys used by knowledge_page.py
    "kb_table_document": {
        "nl": "Document",
        "en": "Document",
    },
    "kb_table_type": {
        "nl": "Type",
        "en": "Type",
    },
    "kb_table_size": {
        "nl": "Grootte",
        "en": "Size",
    },
    "kb_table_status": {
        "nl": "Status",
        "en": "Status",
    },
    "kb_table_vectors": {
        "nl": "Vectors",
        "en": "Vectors",
    },
    "kb_table_upload_date": {
        "nl": "Upload Datum",
        "en": "Upload Date",
    },
    "kb_status_indexed": {
        "nl": "Geïndexeerd",
        "en": "Indexed",
    },
    "kb_status_processing": {
        "nl": "Verwerken…",
        "en": "Processing…",
    },
    "kb_sync_button": {
        "nl": "Sync kennisbank",
        "en": "Sync knowledge base",
    },
    "kb_syncing": {
        "nl": "Sync bezig…",
        "en": "Sync in progress…",
    },
    "kb_sync_last": {
        "nl": "Laatst gesynct",
        "en": "Last synced",
    },
    "kb_sync_never": {
        "nl": "Nog nooit gesynct",
        "en": "Never synced",
    },
    "kb_sync_error": {
        "nl": "Sync mislukt",
        "en": "Sync failed",
    },
    "kb_sync_success": {
        "nl": "Sync voltooid",
        "en": "Sync completed",
    },
    "kb_sync_starting": {
        "nl": "Sync wordt gestart...",
        "en": "Starting sync...",
    },
    "kb_sync_need_token": {
        "nl": "Backend token vereist voor sync.",
        "en": "Backend token required for sync.",
    },
    "kb_sync_pending": {
        "nl": "In afwachting",
        "en": "Pending",
    },
    "kb_stat_documents": {
        "nl": "Documenten",
        "en": "Documents",
    },
    "kb_stat_chunks": {
        "nl": "Chunks",
        "en": "Chunks",
    },
    "kb_stat_vectors": {
        "nl": "Vectors",
        "en": "Vectors",
    },
    "kb_stat_documents_detail": {
        "nl": "{count} documenten geladen",
        "en": "{count} documents loaded",
    },
    "kb_stat_chunks_detail": {
        "nl": "{count} chunks geïndexeerd",
        "en": "{count} chunks indexed",
    },
    "kb_stat_vectors_detail": {
        "nl": "{count} vectors in database",
        "en": "{count} vectors in database",
    },
    "kb_table_category": {
        "nl": "Categorie",
        "en": "Category",
    },
    "kb_table_priority": {
        "nl": "Prioriteit",
        "en": "Priority",
    },
    "kb_table_chunks": {
        "nl": "Chunks",
        "en": "Chunks",
    },
    "kb_table_content_date": {
        "nl": "Datum",
        "en": "Date",
    },
    "kb_table_relations": {
        "nl": "Relaties",
        "en": "Relations",
    },
    "kb_relations_title": {
        "nl": "Document relaties",
        "en": "Document relations",
    },
    "kb_relations_for": {
        "nl": "Relaties voor {document}",
        "en": "Relations for {document}",
    },
    "kb_relations_target": {
        "nl": "Doel",
        "en": "Target",
    },
    "kb_relations_type": {
        "nl": "Type",
        "en": "Type",
    },
    "kb_relations_none": {
        "nl": "Geen relaties gevonden",
        "en": "No relations found",
    },

    # ============================================
    # VUE KENNISBANK PAGE
    # ============================================
    "vue_not_logged_in": {
        "nl": "Niet ingelogd",
        "en": "Not logged in",
    },
    "vue_pushing": {
        "nl": "Pushen...",
        "en": "Pushing...",
    },
    "vue_push_to_git": {
        "nl": "Push naar Git",
        "en": "Push to Git",
    },
    "vue_upload_document": {
        "nl": "Document Uploaden",
        "en": "Upload Document",
    },
    "vue_click_to_upload": {
        "nl": "Klik om te uploaden",
        "en": "Click to upload",
    },
    "vue_coming_soon": {
        "nl": "Binnenkort",
        "en": "Coming soon",
    },
    "vue_uploading": {
        "nl": "Uploaden...",
        "en": "Uploading...",
    },
    "vue_documents": {
        "nl": "Documenten",
        "en": "Documents",
    },
    "vue_no_documents_yet": {
        "nl": "Nog geen documenten geüpload.",
        "en": "No documents uploaded yet.",
    },
    "vue_size": {
        "nl": "Grootte",
        "en": "Size",
    },
    "vue_chunks": {
        "nl": "Chunks",
        "en": "Chunks",
    },
    "vue_date": {
        "nl": "Datum",
        "en": "Date",
    },
    "vue_actions": {
        "nl": "Acties",
        "en": "Actions",
    },
    "vue_processing": {
        "nl": "Bezig...",
        "en": "Processing...",
    },
    "vue_embed": {
        "nl": "Embedden",
        "en": "Embed",
    },
    "vue_delete": {
        "nl": "Verwijder",
        "en": "Delete",
    },
    "vue_git_configuration": {
        "nl": "Git Configuratie",
        "en": "Git Configuration",
    },
    "vue_save_configuration": {
        "nl": "Configuratie Opslaan",
        "en": "Save Configuration",
    },
    "vue_saving": {
        "nl": "Opslaan...",
        "en": "Saving...",
    },
    "vue_last_pushed": {
        "nl": "Laatst gepusht:",
        "en": "Last pushed:",
    },
    "vue_error_loading_documents": {
        "nl": "Fout bij laden documenten",
        "en": "Error loading documents",
    },
    "vue_upload_failed": {
        "nl": "Upload mislukt",
        "en": "Upload failed",
    },
    "vue_uploaded": {
        "nl": "geüpload",
        "en": "uploaded",
    },
    "vue_document_embedded": {
        "nl": "Document embedded",
        "en": "Document embedded",
    },
    "vue_embedding_failed": {
        "nl": "Embedding mislukt",
        "en": "Embedding failed",
    },
    "vue_confirm_delete": {
        "nl": "Weet je zeker dat je dit document wilt verwijderen?",
        "en": "Are you sure you want to delete this document?",
    },
    "vue_document_deleted": {
        "nl": "Document verwijderd",
        "en": "Document deleted",
    },
    "vue_delete_failed": {
        "nl": "Verwijderen mislukt",
        "en": "Delete failed",
    },
    "vue_git_config_saved": {
        "nl": "Git configuratie opgeslagen",
        "en": "Git configuration saved",
    },
    "vue_save_failed": {
        "nl": "Opslaan mislukt",
        "en": "Save failed",
    },
    "vue_push_failed": {
        "nl": "Push mislukt",
        "en": "Push failed",
    },
    "vue_status_uploaded": {
        "nl": "Geüpload",
        "en": "Uploaded",
    },
    "vue_status_processing": {
        "nl": "Verwerken...",
        "en": "Processing...",
    },
    "vue_status_failed": {
        "nl": "Mislukt",
        "en": "Failed",
    },

    # ============================================
    # CHAT PAGE
    # ============================================
    "chat_start_new": {
        "nl": "Start nieuwe chat",
        "en": "Start new chat",
    },
    "chat_welcome": {
        "nl": "Welkom bij AITJE…",
        "en": "Welcome to AITJE…",
    },
    "chat_placeholder": {
        "nl": "Stel een vraag aan Aitje.",
        "en": "Ask Aitje a question.",
    },
    "chat_send": {
        "nl": "Stuur",
        "en": "Send",
    },
    "chat_mode_label": {
        "nl": "Mode",
        "en": "Mode",
    },
    "chat_mode_hint": {
        "nl": "Prompt-template",
        "en": "Prompt template",
    },
    "chat_mode_default": {
        "nl": "Standaard",
        "en": "Default",
    },
    "chat_error_prefix": {
        "nl": "[fout]",
        "en": "[error]",
    },
    "chat_error_401": {
        "nl": "401 Unauthorized: backend verwacht een Bearer token. Vraag een token op via /api/v1/signon en zet AITJE_BEARER_TOKEN in de omgeving.",
        "en": "401 Unauthorized: backend expects a Bearer token. Request a token via /api/v1/signon and set AITJE_BEARER_TOKEN in the environment.",
    },
    "chat_empty_response": {
        "nl": "<leeg antwoord>",
        "en": "<empty response>",
    },
    "chat_no_valid_response": {
        "nl": "Geen geldig antwoord van backend",
        "en": "No valid response from backend",
    },
    "chat_could_not_fetch_devices": {
        "nl": "Kon geen apparaatlijst ophalen voor automatische login:",
        "en": "Could not fetch device list for automatic login:",
    },
    "chat_no_devices_found": {
        "nl": "Geen apparaten gevonden voor auto-login.",
        "en": "No devices found for auto-login.",
    },
    "chat_incomplete_device_data": {
        "nl": "Onvolledige apparaatgegevens voor auto-login.",
        "en": "Incomplete device data for auto-login.",
    },
    "chat_signon_no_token": {
        "nl": "Sign-on gaf geen token terug.",
        "en": "Sign-on did not return a token.",
    },
    "chat_auto_token_failed": {
        "nl": "Automatisch token ophalen mislukt:",
        "en": "Automatic token retrieval failed:",
    },
    "chat_no_response": {
        "nl": "Geen antwoord beschikbaar.",
        "en": "No response available.",
    },
    "chat_in_queue": {
        "nl": "In wachtrij... positie {position}",
        "en": "In queue... position {position}",
    },
    "chat_role_user": {
        "nl": "IK",
        "en": "ME",
    },
    "chat_role_assistant": {
        "nl": "AITJE",
        "en": "AITJE",
    },
    "chat_copy": {
        "nl": "Kopieer",
        "en": "Copy",
    },
    "chat_print": {
        "nl": "Print",
        "en": "Print",
    },
    "chat_copied": {
        "nl": "Gekopieerd",
        "en": "Copied",
    },

    # ============================================
    # KNOWLEDGE PAGE (additional)
    # ============================================
    "kb_sd_used": {
        "nl": "{used} GB gebruikt ({percent}%)",
        "en": "{used} GB used ({percent}%)",
    },
    "kb_vector_db_title": {
        "nl": "Vector Database Status",
        "en": "Vector Database Status",
    },
    "kb_table_document": {
        "nl": "Document",
        "en": "Document",
    },
    "kb_table_type": {
        "nl": "Type",
        "en": "Type",
    },
    "kb_table_size": {
        "nl": "Grootte",
        "en": "Size",
    },
    "kb_table_status": {
        "nl": "Status",
        "en": "Status",
    },
    "kb_table_vectors": {
        "nl": "Vectors",
        "en": "Vectors",
    },
    "kb_table_upload_date": {
        "nl": "Upload Datum",
        "en": "Upload Date",
    },
    "kb_status_indexed": {
        "nl": "Geïndexeerd",
        "en": "Indexed",
    },
    "kb_status_processing": {
        "nl": "Verwerken…",
        "en": "Processing…",
    },

    # ============================================
    # MAPS PAGE
    # ============================================
    "maps_unknown": {
        "nl": "Onbekend",
        "en": "Unknown",
    },
    "maps_no_location_info": {
        "nl": "Geen locatie-informatie",
        "en": "No location information",
    },
    "maps_loading": {
        "nl": "Offline kaart wordt geladen…",
        "en": "Loading offline map…",
    },
    "maps_labeled_location": {
        "nl": "Gelabelde locatie",
        "en": "Labeled location",
    },
    "maps_click_to_pin": {
        "nl": "Klik op de kaart om een locatie te pinnen…",
        "en": "Click on the map to pin a location…",
    },
    "maps_add_location": {
        "nl": "Voeg locatie toe",
        "en": "Add location",
    },
    "maps_locations": {
        "nl": "Locaties",
        "en": "Locations",
    },
    "maps_view_contacts": {
        "nl": "Bekijk contactlocaties op de kaart",
        "en": "View contact locations on the map",
    },
    "maps_reload": {
        "nl": "Herlaad",
        "en": "Reload",
    },
    "maps_reload_contacts": {
        "nl": "Herlaad contacten",
        "en": "Reload contacts",
    },
    "maps_no_contacts_with_gps": {
        "nl": "Nog geen contacten met GPS-coördinaten. Koppel een locatie om deze hier te tonen.",
        "en": "No contacts with GPS coordinates yet. Link a location to show them here.",
    },
    "maps_edit_contact": {
        "nl": "Bewerk contact",
        "en": "Edit contact",
    },
    "maps_remove_location": {
        "nl": "Verwijder locatie",
        "en": "Remove location",
    },
    "maps_delete_contact": {
        "nl": "Verwijder contact",
        "en": "Delete contact",
    },
    "maps_link_location_to_contact": {
        "nl": "Locatie koppelen aan contact",
        "en": "Link location to contact",
    },
    "maps_unknown_location": {
        "nl": "Onbekende locatie",
        "en": "Unknown location",
    },
    "maps_location": {
        "nl": "Locatie",
        "en": "Location",
    },
    "maps_gps": {
        "nl": "GPS",
        "en": "GPS",
    },
    "maps_select_contact": {
        "nl": "Selecteer contact",
        "en": "Select contact",
    },
    "maps_contact": {
        "nl": "Contact",
        "en": "Contact",
    },
    "maps_new_contact": {
        "nl": "Nieuw contact…",
        "en": "New contact…",
    },
    "maps_no_contact_selected": {
        "nl": "Geen contact",
        "en": "No contact",
    },
    "maps_select_a_contact": {
        "nl": "Selecteer een contact.",
        "en": "Select a contact.",
    },
    "maps_could_not_load_contacts": {
        "nl": "Kon contacten niet laden:",
        "en": "Could not load contacts:",
    },
    "maps_could_not_update_contact": {
        "nl": "Contact kon niet worden bijgewerkt:",
        "en": "Contact could not be updated:",
    },
    "maps_remove_location_title": {
        "nl": "Locatie verwijderen",
        "en": "Remove location",
    },
    "maps_remove_location_confirm": {
        "nl": "Weet je zeker dat je de locatie voor dit contact wilt verwijderen?",
        "en": "Are you sure you want to remove the location for this contact?",
    },
    "maps_could_not_remove_location": {
        "nl": "Locatie kon niet worden verwijderd:",
        "en": "Location could not be removed:",
    },
    "maps_delete_contact_title": {
        "nl": "Contact verwijderen",
        "en": "Delete contact",
    },
    "maps_delete_contact_confirm": {
        "nl": "Weet je zeker dat je {name} wilt verwijderen?",
        "en": "Are you sure you want to delete {name}?",
    },
    "maps_could_not_delete_contact": {
        "nl": "Contact kon niet worden verwijderd:",
        "en": "Contact could not be deleted:",
    },
    "maps_no_gps_location": {
        "nl": "Dit contact heeft geen GPS-locatie om te tonen.",
        "en": "This contact has no GPS location to show.",
    },
    "maps_contact_unknown": {
        "nl": "Contact onbekend",
        "en": "Contact unknown",
    },
    "maps_contact_no_id": {
        "nl": "Dit contact kan niet gekoppeld worden omdat het geen ID heeft.",
        "en": "This contact cannot be linked because it has no ID.",
    },
    "maps_select_new_location": {
        "nl": "Selecteer op de kaart een nieuwe locatie voor {name}.",
        "en": "Select a new location on the map for {name}.",
    },
    "maps_select_location": {
        "nl": "Selecteer op de kaart een locatie voor {name}.",
        "en": "Select a location on the map for {name}.",
    },
    "maps_link_location": {
        "nl": "Locatie koppelen",
        "en": "Link location",
    },
    "maps_could_not_save_location": {
        "nl": "Locatie kon niet opgeslagen worden:",
        "en": "Location could not be saved:",
    },
    "maps_location_saved": {
        "nl": "Locatie opgeslagen",
        "en": "Location saved",
    },
    "maps_location_linked_to": {
        "nl": "Locatie is gekoppeld aan {name}.",
        "en": "Location has been linked to {name}.",
    },
    "maps_could_not_create_contact": {
        "nl": "Contact kon niet aangemaakt worden:",
        "en": "Contact could not be created:",
    },

    # ============================================
    # SETTINGS PAGE (additional)
    # ============================================
    "settings_ollama_model": {
        "nl": "Ollama model",
        "en": "Ollama model",
    },
    "settings_model": {
        "nl": "Model",
        "en": "Model",
    },
    "settings_remote_support": {
        "nl": "Remote support (Tailscale)",
        "en": "Remote support (Tailscale)",
    },

    # ============================================
    # CONTACT FORM (additional)
    # ============================================
    "contact_form_latitude": {
        "nl": "Latitude",
        "en": "Latitude",
    },
    "contact_form_longitude": {
        "nl": "Longitude",
        "en": "Longitude",
    },
}


def _env_file_path() -> Path:
    """Return path to .env file."""
    return Path(__file__).resolve().parents[2] / ".env"


def _read_env_language() -> str | None:
    """Read LANGUAGE from .env file."""
    path = _env_file_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != "LANGUAGE":
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        return value.strip()
    return None


def get_current_language() -> str:
    """Get the current language code (nl or en)."""
    # Check environment variable first
    env_lang = os.environ.get("LANGUAGE", "")
    if env_lang:
        if "en" in env_lang.lower():
            return "en"
        return "nl"

    # Check .env file
    file_lang = _read_env_language()
    if file_lang:
        if "en" in file_lang.lower():
            return "en"
        return "nl"

    return _current_language


def set_language(lang: str) -> None:
    """Set the current language and notify callbacks."""
    global _current_language
    if lang.lower().startswith("en"):
        _current_language = "en"
    else:
        _current_language = "nl"

    # Notify all registered callbacks
    for callback in _language_change_callbacks:
        try:
            callback()
        except Exception:
            pass


def register_language_change_callback(callback: Callable[[], None]) -> None:
    """Register a callback to be called when language changes."""
    if callback not in _language_change_callbacks:
        _language_change_callbacks.append(callback)


def unregister_language_change_callback(callback: Callable[[], None]) -> None:
    """Unregister a language change callback."""
    if callback in _language_change_callbacks:
        _language_change_callbacks.remove(callback)


def t(key: str, **kwargs) -> str:
    """
    Get translated text for a key.

    Args:
        key: The translation key
        **kwargs: Format arguments to substitute into the string

    Returns:
        The translated string, or the key if not found
    """
    lang = get_current_language()

    if key not in TRANSLATIONS:
        return key

    text = TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get("nl", key))

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass

    return text


# Alias for convenience
_ = t
