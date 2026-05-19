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
        "nl": "Edge AI-console",
        "en": "Edge AI Console",
    },
    "online": {
        "nl": "ONLINE",
        "en": "ONLINE",
    },
    "offline": {
        "nl": "OFFLINE",
        "en": "OFFLINE",
    },
    "close": {
        "nl": "Sluiten",
        "en": "Close",
    },
    "power_dialog_title": {
        "nl": "App bedienen",
        "en": "App controls",
    },
    "power_dialog_message": {
        "nl": "Wil je de AITJE-app afsluiten of opnieuw opstarten?",
        "en": "Do you want to close or restart the AITJE app?",
    },
    "power_dialog_shutdown": {
        "nl": "Afsluiten",
        "en": "Shut down",
    },
    "power_dialog_restart": {
        "nl": "Opnieuw opstarten",
        "en": "Restart",
    },

    # ============================================
    # SIDEBAR
    # ============================================
    "sidebar_subtitle": {
        "nl": "Edge AI console",
        "en": "Edge AI Console",
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
        "nl": "Gebruikersbeheer",
        "en": "User Management",
    },
    "nav_embedder": {
        "nl": "Embedder",
        "en": "Embedder",
    },
    "nav_settings": {
        "nl": "Instellingen",
        "en": "Settings",
    },

    # ============================================
    # BOOT SCREEN
    # ============================================
    "boot_starting": {
        "nl": "Starting local AI...",
        "en": "Starting local AI...",
    },
    "boot_loading_neural": {
        "nl": "Loading neural networks...",
        "en": "Loading neural networks...",
    },
    "boot_preparing_api": {
        "nl": "Preparing API endpoints...",
        "en": "Preparing API endpoints...",
    },
    "boot_syncing_devices": {
        "nl": "Synchronizing devices...",
        "en": "Synchronizing devices...",
    },
    "boot_almost_ready": {
        "nl": "Almost ready...",
        "en": "Almost ready...",
    },
    "boot_welcome": {
        "nl": "Welcome! ✓",
        "en": "Welcome! ✓",
    },
    "boot_title": {
        "nl": "Aitje is waking up",
        "en": "Aitje is waking up",
    },
    "boot_subtitle": {
        "nl": "",
        "en": "",
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
        "nl": "Gebruikersbeheer",
        "en": "User Management",
    },
    "page_title_embedder": {
        "nl": "Embedder",
        "en": "Embedder",
    },
    "page_title_settings": {
        "nl": "Instellingen",
        "en": "Settings",
    },

    # ============================================
    # PAGE SUBTITLES
    # ============================================
    "page_subtitle_chat": {
        "nl": "Start een gesprek met je Edge AI-assistent",
        "en": "Start a conversation with your Edge AI assistant",
    },
    "chat_disclaimer": {
        "nl": "Aitje is AI en kan ook fouten maken. Controleer belangrijke informatie.",
        "en": "Aitje is AI and can also make mistakes. Verify important information.",
    },
    "page_subtitle_kb": {
        "nl": "Inzage voor kennisbank documenten en opslag",
        "en": "Insight into knowledge base documents and storage",
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
        "nl": "Beheer verbonden apparaten en gebruikersaccounts",
        "en": "Manage connected devices and user accounts",
    },
    "page_subtitle_embedder": {
        "nl": "Open de embedding-applicatie op een ander apparaat in het netwerk",
        "en": "Open the embedding application on another device in the network",
    },
    "page_subtitle_settings": {
        "nl": "Beheer de systeeminstellingen en voorkeuren",
        "en": "Manage system settings and preferences",
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
        "nl": "Chat Voorkeuren",
        "en": "Chat Preferences",
    },
    "settings_tab_ssh": {
        "nl": "Remote support",
        "en": "Remote support",
    },
    "settings_tab_wifi": {
        "nl": "Wifi",
        "en": "WiFi",
    },
    "settings_tab_bluetooth": {
        "nl": "Bluetooth",
        "en": "Bluetooth",
    },
    "settings_wifi_title": {
        "nl": "Wifi configuratie",
        "en": "WiFi configuration",
    },
    "settings_wifi_intro": {
        "nl": "Beheer en bekijk hier de wifi-instellingen van AITJE.",
        "en": "Manage and view AITJE's WiFi settings here.",
    },
    "settings_wifi_status_loading": {
        "nl": "Wifi-informatie laden...",
        "en": "Loading WiFi information...",
    },
    "settings_wifi_open": {
        "nl": "Open wifi-instellingen",
        "en": "Open WiFi settings",
    },
    "settings_wifi_open_failed": {
        "nl": "Kon geen systeemscherm openen voor wifi-instellingen op dit apparaat.",
        "en": "Could not open the system WiFi settings on this device.",
    },
    "settings_wifi_info_unavailable": {
        "nl": "Wifi-informatie is momenteel niet beschikbaar.",
        "en": "WiFi information is currently unavailable.",
    },
    "settings_wifi_connected": {
        "nl": "Verbonden",
        "en": "Connected",
    },
    "settings_wifi_not_connected": {
        "nl": "Niet verbonden",
        "en": "Not connected",
    },
    "settings_wifi_platform": {
        "nl": "Platform",
        "en": "Platform",
    },
    "settings_wifi_state": {
        "nl": "Status",
        "en": "Status",
    },
    "settings_wifi_ssid": {
        "nl": "Netwerk",
        "en": "Network",
    },
    "settings_wifi_interface": {
        "nl": "Interface",
        "en": "Interface",
    },
    "settings_wifi_signal": {
        "nl": "Signaal",
        "en": "Signal",
    },
    "settings_wifi_security": {
        "nl": "Beveiliging",
        "en": "Security",
    },
    "settings_wifi_channel": {
        "nl": "Kanaal",
        "en": "Channel",
    },
    "settings_wifi_ipv4": {
        "nl": "IPv4",
        "en": "IPv4",
    },
    "settings_wifi_ipv6": {
        "nl": "IPv6",
        "en": "IPv6",
    },
    "settings_wifi_gateway": {
        "nl": "Gateway",
        "en": "Gateway",
    },
    "settings_wifi_mac": {
        "nl": "MAC-adres",
        "en": "MAC address",
    },
    "settings_wifi_bssid": {
        "nl": "BSSID",
        "en": "BSSID",
    },
    "settings_wifi_note": {
        "nl": "Opmerking",
        "en": "Note",
    },
    "settings_bluetooth_title": {
        "nl": "Bluetooth configuratie",
        "en": "Bluetooth configuration",
    },
    "settings_bluetooth_intro": {
        "nl": "Koppel en beheer Bluetooth-apparaten zonder AITJE te verlaten.",
        "en": "Pair and manage Bluetooth devices without leaving AITJE.",
    },
    "settings_bluetooth_toggle_on": {
        "nl": "Bluetooth aan",
        "en": "Bluetooth on",
    },
    "settings_bluetooth_toggle_off": {
        "nl": "Bluetooth uit",
        "en": "Bluetooth off",
    },
    "settings_bluetooth_ready": {
        "nl": "Bluetooth staat aan.",
        "en": "Bluetooth is on.",
    },
    "settings_bluetooth_status_loading": {
        "nl": "Bluetooth-informatie laden...",
        "en": "Loading Bluetooth information...",
    },
    "settings_bluetooth_info_unavailable": {
        "nl": "Bluetooth-informatie is momenteel niet beschikbaar.",
        "en": "Bluetooth information is currently unavailable.",
    },
    "settings_bluetooth_refresh": {
        "nl": "Verversen",
        "en": "Refresh",
    },
    "settings_bluetooth_power_on": {
        "nl": "Bluetooth inschakelen",
        "en": "Turn Bluetooth on",
    },
    "settings_bluetooth_repair": {
        "nl": "Bluetooth herstellen",
        "en": "Repair Bluetooth",
    },
    "settings_bluetooth_repairing": {
        "nl": "Bluetooth-stack herstellen...",
        "en": "Repairing Bluetooth stack...",
    },
    "settings_bluetooth_powering_on": {
        "nl": "Bluetooth inschakelen...",
        "en": "Turning Bluetooth on...",
    },
    "settings_bluetooth_power_required": {
        "nl": "Bluetooth staat uit. Schakel Bluetooth eerst in en scan daarna opnieuw.",
        "en": "Bluetooth is off. Turn Bluetooth on first, then scan again.",
    },
    "settings_bluetooth_power_on_failed": {
        "nl": "Bluetooth kon niet worden ingeschakeld. Controleer of de Bluetooth-service actief is en niet door rfkill is geblokkeerd.",
        "en": "Bluetooth could not be turned on. Check that the Bluetooth service is active and not blocked by rfkill.",
    },
    "settings_bluetooth_scan": {
        "nl": "Scannen",
        "en": "Scan",
    },
    "settings_bluetooth_pair_connect": {
        "nl": "Koppelen en verbinden",
        "en": "Pair and connect",
    },
    "settings_bluetooth_forget": {
        "nl": "Vergeten",
        "en": "Forget",
    },
    "settings_bluetooth_connected_devices": {
        "nl": "Verbonden apparaten",
        "en": "Connected devices",
    },
    "settings_bluetooth_scan_results": {
        "nl": "Scanresultaten",
        "en": "Scan results",
    },
    "settings_bluetooth_no_connected_devices": {
        "nl": "Geen verbonden apparaten",
        "en": "No connected devices",
    },
    "settings_bluetooth_no_scan_results": {
        "nl": "Nog geen scanresultaten",
        "en": "No scan results yet",
    },
    "settings_bluetooth_unknown_device": {
        "nl": "Onbekend {kind}",
        "en": "Unknown {kind}",
    },
    "settings_bluetooth_kind_keyboard": {
        "nl": "toetsenbord",
        "en": "keyboard",
    },
    "settings_bluetooth_kind_mouse": {
        "nl": "muis",
        "en": "mouse",
    },
    "settings_bluetooth_kind_audio": {
        "nl": "audioapparaat",
        "en": "audio device",
    },
    "settings_bluetooth_kind_phone": {
        "nl": "telefoon",
        "en": "phone",
    },
    "settings_bluetooth_kind_computer": {
        "nl": "computer",
        "en": "computer",
    },
    "settings_bluetooth_kind_input": {
        "nl": "invoerapparaat",
        "en": "input device",
    },
    "settings_bluetooth_kind_device": {
        "nl": "apparaat",
        "en": "device",
    },
    "settings_bluetooth_scan_failed": {
        "nl": "Scannen is mislukt. Details staan in bluetooth.log.",
        "en": "Scan failed. Details are in bluetooth.log.",
    },
    "settings_bluetooth_pair_failed": {
        "nl": "Koppelen of verbinden is mislukt. Details staan in bluetooth.log.",
        "en": "Pairing or connecting failed. Details are in bluetooth.log.",
    },
    "settings_bluetooth_forget_failed": {
        "nl": "Vergeten is mislukt. Details staan in bluetooth.log.",
        "en": "Forget failed. Details are in bluetooth.log.",
    },
    "settings_bluetooth_toggle_failed": {
        "nl": "Bluetooth kon niet worden omgeschakeld. Details staan in bluetooth.log.",
        "en": "Bluetooth could not be toggled. Details are in bluetooth.log.",
    },
    "settings_bluetooth_scanning": {
        "nl": "Bluetooth-apparaten zoeken...",
        "en": "Scanning for Bluetooth devices...",
    },
    "settings_bluetooth_select_device": {
        "nl": "Selecteer eerst een Bluetooth-apparaat.",
        "en": "Select a Bluetooth device first.",
    },
    "settings_bluetooth_pairing": {
        "nl": "Bluetooth-apparaat koppelen: {device}",
        "en": "Pairing Bluetooth device: {device}",
    },
    "settings_bluetooth_pair_done": {
        "nl": "Bluetooth-koppelactie afgerond.",
        "en": "Bluetooth pairing action completed.",
    },
    "settings_bluetooth_linux_only": {
        "nl": "In-app Bluetooth-koppeling is nu alleen ondersteund op Linux met bluetoothctl.",
        "en": "In-app Bluetooth pairing is currently supported only on Linux with bluetoothctl.",
    },
    "settings_bluetoothctl_missing": {
        "nl": "bluetoothctl is niet beschikbaar op dit apparaat.",
        "en": "bluetoothctl is not available on this device.",
    },
    "settings_bluetooth_adapter": {
        "nl": "Adapter",
        "en": "Adapter",
    },
    "settings_bluetooth_powered": {
        "nl": "Ingeschakeld",
        "en": "Powered",
    },
    "settings_bluetooth_discoverable": {
        "nl": "Vindbaar",
        "en": "Discoverable",
    },
    "settings_bluetooth_pairable": {
        "nl": "Koppelbaar",
        "en": "Pairable",
    },
    "settings_bluetooth_service": {
        "nl": "Service",
        "en": "Service",
    },
    "settings_bluetooth_rfkill": {
        "nl": "Blokkering",
        "en": "Block state",
    },
    "settings_bluetooth_devices": {
        "nl": "Apparaten",
        "en": "Devices",
    },
    "settings_bluetooth_connected": {
        "nl": "verbonden",
        "en": "connected",
    },
    "settings_bluetooth_paired": {
        "nl": "gekoppeld",
        "en": "paired",
    },
    "settings_timezone": {
        "nl": "Tijdzone",
        "en": "Timezone",
    },
    "settings_language": {
        "nl": "Taal",
        "en": "Language",
    },
    "settings_application_language": {
        "nl": "Application Language",
        "en": "Application Language",
    },
    "settings_response_language": {
        "nl": "AITJE reactietaal",
        "en": "AITJE response language",
    },
    "settings_today": {
        "nl": "Datum van vandaag",
        "en": "Today's date",
    },
    "settings_system_information": {
        "nl": "Systeeminformatie",
        "en": "System information",
    },
    "settings_device_prefix": {
        "nl": "Device prefix",
        "en": "Device prefix",
    },
    "settings_device_number": {
        "nl": "Device nummer",
        "en": "Device number",
    },
    "settings_backend_url": {
        "nl": "Backend URL",
        "en": "Backend URL",
    },
    "settings_backend_port": {
        "nl": "Backend poort",
        "en": "Backend port",
    },
    "settings_backend_bind_host": {
        "nl": "Backend bind host",
        "en": "Backend bind host",
    },
    "settings_api_routes_port": {
        "nl": "API routes poort",
        "en": "API routes port",
    },
    "settings_admin_users": {
        "nl": "Admin gebruikers",
        "en": "Admin users",
    },
    "settings_admin_device_id": {
        "nl": "Admin device ID",
        "en": "Admin device ID",
    },
    "settings_ollama_base_url": {
        "nl": "Ollama base URL",
        "en": "Ollama base URL",
    },
    "settings_ollama_model_label": {
        "nl": "Taal model",
        "en": "Language model",
    },
    "settings_qdrant_devices_path": {
        "nl": "Qdrant devices pad",
        "en": "Qdrant devices path",
    },
    "settings_not_set": {
        "nl": "Niet ingesteld",
        "en": "Not set",
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
    "settings_2_hours": {
        "nl": "2 uur",
        "en": "2 hours",
    },
    "settings_loading_models": {
        "nl": "Beschikbare modellen laden...",
        "en": "Loading available models...",
    },
    "settings_support_hint": {
        "nl": "Schakel dit alleen in overleg met het AITJE support team in. We openen tijdelijk een reverse SSH-tunnel en sluiten die automatisch na afloop van de gekozen duur.",
        "en": "Only enable this in coordination with the AITJE support team. We temporarily open a reverse SSH tunnel and close it automatically after the selected duration.",
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
    "settings_could_not_save_response_language": {
        "nl": "Kon AITJE-reactietaal niet opslaan:",
        "en": "Could not save AITJE response language:",
    },
    "settings_could_not_save_today": {
        "nl": "Kon datum van vandaag niet opslaan:",
        "en": "Could not save today's date:",
    },
    "settings_could_not_save_system_preferences": {
        "nl": "Kon systeemvoorkeuren niet opslaan:",
        "en": "Could not save system preferences:",
    },
    "settings_could_not_save_focus_mode": {
        "nl": "Kon focus mode niet opslaan:",
        "en": "Could not save focus mode:",
    },
    "settings_save": {
        "nl": "Opslaan",
        "en": "Save",
    },
    "settings_reset": {
        "nl": "Terugzetten",
        "en": "Reset",
    },
    "settings_new_focus_mode": {
        "nl": "Nieuwe focus mode",
        "en": "New focus mode",
    },
    "settings_add_focus_mode": {
        "nl": "Focus mode toevoegen",
        "en": "Add focus mode",
    },
    "settings_edit_focus_mode": {
        "nl": "Bewerk eigen prompt",
        "en": "Edit custom prompt",
    },
    "settings_view_focus_mode": {
        "nl": "Bekijk prompt",
        "en": "View prompt",
    },
    "settings_delete": {
        "nl": "Verwijderen",
        "en": "Delete",
    },
    "settings_delete_focus_mode": {
        "nl": "Focus mode verwijderen",
        "en": "Delete focus mode",
    },
    "settings_delete_focus_mode_confirm": {
        "nl": "Weet je zeker dat je de focus mode '{mode}' wilt verwijderen?",
        "en": "Are you sure you want to delete the focus mode '{mode}'?",
    },
    "settings_focus_mode_default_info": {
        "nl": "Geen vaste template geselecteerd. AITJE gebruikt dan de standaard assistentprompt.",
        "en": "No fixed template selected. AITJE will use the default assistant prompt.",
    },
    "settings_focus_mode_developer_info": {
        "nl": "Developer mode stuurt AITJE naar technische, concrete en direct uitvoerbare antwoorden met expliciete aannames.",
        "en": "Developer mode steers AITJE toward technical, concrete, implementation-ready answers with explicit assumptions.",
    },
    "settings_focus_mode_finance_info": {
        "nl": "Finance mode legt cijfers, aannames, risico's en berekeningen duidelijk uit zonder te doen alsof het financieel advies is.",
        "en": "Finance mode explains numbers, assumptions, risks, and calculations clearly without posing as financial advice.",
    },
    "settings_focus_mode_law_info": {
        "nl": "Law mode houdt antwoorden neutraal, wijst op jurisdictie en maakt helder onderscheid tussen informatie en juridisch advies.",
        "en": "Law mode keeps answers neutral, flags jurisdiction issues, and clearly separates information from legal advice.",
    },
    "settings_focus_mode_child_info": {
        "nl": "Child mode vereenvoudigt taalgebruik, houdt antwoorden vriendelijk en vermijdt onnodig complexe of gevoelige details.",
        "en": "Child mode simplifies language, keeps answers friendly, and avoids unnecessarily complex or sensitive detail.",
    },
    "settings_focus_mode_custom_info": {
        "nl": "Eigen prompt actief. Preview: {prompt}",
        "en": "Custom prompt active. Preview: {prompt}",
    },
    "settings_focus_mode_custom_info_empty": {
        "nl": "Eigen prompt actief, maar het templatebestand lijkt leeg.",
        "en": "Custom prompt active, but the template file appears empty.",
    },
    "settings_focus_mode_builtin_locked": {
        "nl": "Deze ingebouwde template is alleen-lezen. Maak een eigen focus mode om hem aan te passen.",
        "en": "This built-in template is read-only. Create your own focus mode to customize it.",
    },
    "settings_focus_mode_custom_editable": {
        "nl": "Deze eigen focus mode kun je hier bewerken of verwijderen.",
        "en": "You can edit or delete this custom focus mode here.",
    },
    "settings_focus_mode_default_locked": {
        "nl": "Selecteer een focus mode of maak een nieuwe om een eigen prompt te gebruiken.",
        "en": "Select a focus mode or create a new one to use a custom prompt.",
    },
    "settings_focus_mode_default_prompt_preview": {
        "nl": "De standaardmodus gebruikt de algemene AITJE assistentprompt uit de backend als er geen specifieke focus mode actief is.",
        "en": "Default mode uses the general AITJE assistant prompt from the backend when no specific focus mode is active.",
    },
    "settings_focus_mode_builtin_name_error": {
        "nl": "Deze naam is gereserveerd voor een ingebouwde focus mode.",
        "en": "That name is reserved for a built-in focus mode.",
    },
    "settings_focus_mode_validation_error": {
        "nl": "Vul zowel een naam als een prompt-template in.",
        "en": "Please provide both a name and a prompt template.",
    },
    "settings_focus_mode_dialog_title": {
        "nl": "Eigen focus mode",
        "en": "Custom focus mode",
    },
    "settings_focus_mode_dialog_builtin_title": {
        "nl": "Ingebouwde focus mode: {mode}",
        "en": "Built-in focus mode: {mode}",
    },
    "settings_focus_mode_dialog_intro": {
        "nl": "Maak of wijzig hier een eigen prompt-template. Deze wordt opgeslagen in prompt_templates en toegevoegd aan de focus mode lijst.",
        "en": "Create or edit your own prompt template here. It will be stored in prompt_templates and added to the focus mode list.",
    },
    "settings_focus_mode_dialog_builtin_intro": {
        "nl": "Dit is een ingebouwde template. Je kunt hem bekijken, maar niet direct wijzigen. Maak een eigen variant als je wilt afwijken.",
        "en": "This is a built-in template. You can inspect it, but not edit it directly. Create a custom variant if you want to change it.",
    },
    "settings_focus_mode_name": {
        "nl": "Naam",
        "en": "Name",
    },
    "settings_focus_mode_name_placeholder": {
        "nl": "Bijvoorbeeld: Sales of Support Coach",
        "en": "For example: Sales or Support Coach",
    },
    "settings_focus_mode_prompt": {
        "nl": "Prompt-template",
        "en": "Prompt template",
    },
    "settings_model_description_empty": {
        "nl": "Kies een model om de beschrijving te zien.",
        "en": "Choose a model to see its description.",
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
        "nl": "Dit opent tijdelijke remote support via een reverse SSH-tunnel. Schakel alleen in met expliciete toestemming. Doorgaan?",
        "en": "This opens temporary remote support through a reverse SSH tunnel. Enable only with explicit permission. Continue?",
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
    "settings_support_active_message": {
        "nl": "Actief op poort {port}. Sluit automatisch om {expires_at} ({remaining}).",
        "en": "Active on port {port}. Closes automatically at {expires_at} ({remaining}).",
    },
    "settings_support_inactive_message": {
        "nl": "Remote support staat uit.",
        "en": "Remote support is off.",
    },
    "settings_support_remaining_minutes": {
        "nl": "nog {minutes} min",
        "en": "{minutes} min remaining",
    },
    "settings_support_remaining_hours": {
        "nl": "nog {hours} uur",
        "en": "{hours} hour(s) remaining",
    },
    "settings_support_remaining_hours_minutes": {
        "nl": "nog {hours} uur {minutes} min",
        "en": "{hours} hour(s) {minutes} min remaining",
    },
    "settings_support_expiring_now": {
        "nl": "verloopt nu",
        "en": "expiring now",
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
    "devices_empty_title": {
        "nl": "Maak je eerste device aan",
        "en": "Create your first device",
    },
    "devices_empty_subtitle": {
        "nl": "Voeg een account toe dat via de API kan verbinden.",
        "en": "Add an account that can connect through the API.",
    },
    "devices_add_contact_title": {
        "nl": "Voeg een nieuw contact toe",
        "en": "Add a new contact",
    },
    "devices_add_contact_subtitle": {
        "nl": "Maak direct nog een contact aan.",
        "en": "Create another contact right away.",
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
    "devices_connected": {
        "nl": "Status: Verbonden",
        "en": "Status: Connected",
    },
    "devices_not_connected": {
        "nl": "Status: Niet verbonden",
        "en": "Status: Not connected",
    },
    "devices_client_url_title": {
        "nl": "Webclient URL",
        "en": "Web client URL",
    },
    "devices_client_url_subtitle": {
        "nl": "Externe apparaten kunnen op hetzelfde netwerk deze URL openen in een browser of webbrowser om in te loggen.",
        "en": "Devices on the same network can browse to this URL to sign in.",
    },
    "devices_client_url_show": {
        "nl": "Toon client URL",
        "en": "Show client URL",
    },
    "devices_client_url_copy": {
        "nl": "Kopieer URL",
        "en": "Copy URL",
    },
    "devices_client_url_copied": {
        "nl": "URL gekopieerd",
        "en": "URL copied",
    },
    "devices_client_url_qr_hint": {
        "nl": "Scan met je telefoon. Eerste keer? Installeer kort het apparaat­certificaat — daarna gaat alles via HTTPS.",
        "en": "Scan with your phone. First time? Install the device certificate once — after that everything runs over HTTPS.",
    },

    # ============================================
    # EMBEDDER PAGE
    # ============================================
    "embedder_intro": {
        "nl": "De Embedding Application draait op dit apparaat en is bereikbaar voor andere computers in hetzelfde netwerk. Scan de QR-code op een laptop of tablet om in te loggen en kennisbankdocumenten te beheren — zonder Git, zonder cloud.",
        "en": "The Embedding Application runs on this device and is reachable from other computers on the same network. Scan the QR code from a laptop or tablet to sign in and manage knowledge-base documents — no Git, no cloud.",
    },
    "embedder_qr_hint": {
        "nl": "Scan met de camera-app. Eerste keer? Installeer kort het apparaat­certificaat — daarna gaat de embedder via HTTPS.",
        "en": "Scan with your camera app. First time? Install the device certificate once — after that the embedder runs over HTTPS.",
    },
    "embedder_qr_missing": {
        "nl": "QR-module ontbreekt — herstart AITJE om dependencies bij te werken.",
        "en": "QR module missing — restart AITJE to refresh dependencies.",
    },
    "embedder_status_online": {
        "nl": "ONLINE",
        "en": "ONLINE",
    },
    "embedder_status_offline": {
        "nl": "OFFLINE",
        "en": "OFFLINE",
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
        "nl": "Aantal API-aanroepen vandaag.",
        "en": "Number of API requests today.",
    },
    "network_active_users": {
        "nl": "ACTIEVE GEBRUIKERS",
        "en": "ACTIVE USERS",
    },
    "network_customers_apps": {
        "nl": "Unieke gebruikers die vandaag actief waren.",
        "en": "Unique users active today.",
    },
    "network_avg_response_time": {
        "nl": "GEM. REACTIETIJD",
        "en": "AVG. RESPONSE TIME",
    },
    "network_avg_wait_time": {
        "nl": "Gemiddelde tijd tot AITJE volledig heeft geantwoord.",
        "en": "Average time until AITJE fully completed its response.",
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
    "network_details_title": {
        "nl": "Netwerkdetails",
        "en": "Network details",
    },
    "network_status_loading": {
        "nl": "Status laden...",
        "en": "Loading status...",
    },
    "network_info_wifi": {
        "nl": "WIFI-STATUS",
        "en": "WIFI STATUS",
    },
    "network_info_backend": {
        "nl": "BACKEND/API",
        "en": "BACKEND/API",
    },
    "network_info_activity": {
        "nl": "ACTIVITEIT",
        "en": "ACTIVITY",
    },
    "network_info_knowledge": {
        "nl": "KENNISBANK",
        "en": "KNOWLEDGE BASE",
    },
    "network_info_local": {
        "nl": "LOKALE TOEGANG",
        "en": "LOCAL ACCESS",
    },
    "network_info_performance": {
        "nl": "PRESTATIES",
        "en": "PERFORMANCE",
    },
    "network_status": {
        "nl": "Status",
        "en": "Status",
    },
    "network_status_online": {
        "nl": "Online",
        "en": "Online",
    },
    "network_status_offline": {
        "nl": "Offline",
        "en": "Offline",
    },
    "network_status_unknown": {
        "nl": "Onbekend",
        "en": "Unknown",
    },
    "network_status_unavailable": {
        "nl": "Niet beschikbaar",
        "en": "Unavailable",
    },
    "network_nmcli_missing": {
        "nl": "nmcli niet gevonden",
        "en": "nmcli not found",
    },
    "network_wifi_ssid": {
        "nl": "Netwerk",
        "en": "Network",
    },
    "network_wifi_signal": {
        "nl": "Signaal",
        "en": "Signal",
    },
    "network_wifi_interface": {
        "nl": "Interface",
        "en": "Interface",
    },
    "network_wifi_ipv4": {
        "nl": "IP-adres",
        "en": "IP address",
    },
    "network_wifi_gateway": {
        "nl": "Gateway",
        "en": "Gateway",
    },
    "network_wifi_security": {
        "nl": "Beveiliging",
        "en": "Security",
    },
    "network_backend_url": {
        "nl": "Backend",
        "en": "Backend",
    },
    "network_backend_check": {
        "nl": "Laatste check",
        "en": "Last check",
    },
    "network_requests_today": {
        "nl": "API-calls vandaag",
        "en": "API calls today",
    },
    "network_active_today": {
        "nl": "Actief vandaag",
        "en": "Active today",
    },
    "network_error_rate": {
        "nl": "Foutpercentage",
        "en": "Error rate",
    },
    "network_connections": {
        "nl": "Verbindingen",
        "en": "Connections",
    },
    "network_not_tracked": {
        "nl": "Nog niet gemeten",
        "en": "Not tracked yet",
    },
    "network_documents": {
        "nl": "Documenten",
        "en": "Documents",
    },
    "network_categories": {
        "nl": "Categorieen",
        "en": "Categories",
    },
    "network_last_sync": {
        "nl": "Laatste sync",
        "en": "Last sync",
    },
    "network_sync_never": {
        "nl": "Nog nooit",
        "en": "Never",
    },
    "network_hostname": {
        "nl": "Hostnaam",
        "en": "Hostname",
    },
    "network_local_ip": {
        "nl": "Lokaal IP",
        "en": "Local IP",
    },
    "network_local_url": {
        "nl": "Lokale URL",
        "en": "Local URL",
    },
    "network_mdns_url": {
        "nl": "mDNS",
        "en": "mDNS",
    },
    "network_uptime": {
        "nl": "Uptime",
        "en": "Uptime",
    },
    "network_avg_response_short": {
        "nl": "Gem. antwoord",
        "en": "Avg. response",
    },
    "network_tokens_per_second": {
        "nl": "Tokens/sec",
        "en": "Tokens/sec",
    },
    "network_no_ollama_metric": {
        "nl": "Na volgend antwoord",
        "en": "After next response",
    },
    "network_resources_title": {
        "nl": "Systeemverbruik",
        "en": "System usage",
    },
    "network_ram_now": {
        "nl": "RAM VERBRUIK",
        "en": "RAM USAGE",
    },
    "network_ram_caption": {
        "nl": "Actueel geheugenverbruik ({percent}% van het systeem).",
        "en": "Current memory usage ({percent}% of system memory).",
    },
    "network_cpu_now": {
        "nl": "CPU VERBRUIK",
        "en": "CPU USAGE",
    },
    "network_cpu_caption": {
        "nl": "Huidige systeembelasting.",
        "en": "Current system load.",
    },
    "network_power_now": {
        "nl": "STROOMVERBRUIK",
        "en": "POWER USAGE",
    },
    "network_power_caption": {
        "nl": "Live wattage van het apparaat.",
        "en": "Live device wattage.",
    },
    "network_power_live": {
        "nl": "Live gemeten via systeemsensor.",
        "en": "Live reading from system sensor.",
    },
    "network_power_unavailable": {
        "nl": "Geen live powersensor gevonden. Voor exact verbruik is Linux power telemetry of een slimme meter nodig.",
        "en": "No live power sensor found. Exact usage requires Linux power telemetry or a smart meter.",
    },
    "network_power_battery_line": {
        "nl": "Batterij: {value}",
        "en": "Battery: {value}",
    },
    "network_power_plugged_line": {
        "nl": "Aan lader: {value}",
        "en": "Charging: {value}",
    },
    "network_power_source_line": {
        "nl": "Stroombron: {value}",
        "en": "Power source: {value}",
    },
    "network_power_live_line": {
        "nl": "Live verbruik: {value}",
        "en": "Live usage: {value}",
    },
    "network_power_plugged_yes": {
        "nl": "Ja",
        "en": "Yes",
    },
    "network_power_plugged_no": {
        "nl": "Nee",
        "en": "No",
    },
    "network_power_source_ac": {
        "nl": "Netstroom",
        "en": "AC power",
    },
    "network_power_source_usb": {
        "nl": "USB-C / USB-voeding",
        "en": "USB-C / USB power",
    },
    "network_power_source_battery": {
        "nl": "Batterij",
        "en": "Battery",
    },
    "network_power_source_unknown": {
        "nl": "Onbekend",
        "en": "Unknown",
    },
    "network_power_no_battery": {
        "nl": "Geen batterij gedetecteerd",
        "en": "No battery detected",
    },
    "network_power_unknown_short": {
        "nl": "Onbekend",
        "en": "Unknown",
    },
    "network_performance_title": {
        "nl": "Hoe AITJE nu draait",
        "en": "How AITJE is running",
    },
    "network_performance_caption": {
        "nl": "Een snelle indruk van geheugen, rekenlast en stroomvraag van het kastje.",
        "en": "A quick view of memory, compute load, and device power demand.",
    },

    # ============================================
    # KNOWLEDGE PAGE
    # ============================================
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
    "kb_vector_progress_storage": {
        "nl": "Opslag",
        "en": "Storage",
    },
    "kb_vector_progress_embeddings": {
        "nl": "Embeddings",
        "en": "Embeddings",
    },
    "kb_optimal": {
        "nl": "Optimaal",
        "en": "Optimal",
    },
    "kb_documents": {
        "nl": "Kennisbank Documenten",
        "en": "Knowledge Bank Documents",
    },
    "kb_documents_subtitle": {
        "nl": "Bekijk documenten in de kennisbank.",
        "en": "Review documents in the knowledge base.",
    },
    "kb_documents_search_placeholder": {
        "nl": "Zoek in documenten...",
        "en": "Search documents...",
    },
    "kb_documents_refresh": {
        "nl": "Vernieuwen",
        "en": "Refresh",
    },
    "kb_documents_refresh_tooltip": {
        "nl": "Documenten en sync-status opnieuw ophalen",
        "en": "Reload documents and sync status",
    },
    "kb_preview_title": {
        "nl": "Document Preview",
        "en": "Document Preview",
    },
    "kb_preview_empty_title": {
        "nl": "Selecteer een document",
        "en": "Select a document",
    },
    "kb_preview_empty_body": {
        "nl": "Klik links op een document om hier de inhoud te bekijken.",
        "en": "Click a document on the left to view its contents here.",
    },
    "kb_preview_unavailable": {
        "nl": "Voor dit document is momenteel geen preview beschikbaar.",
        "en": "No preview is currently available for this document.",
    },
    "kb_preview_chunks": {
        "nl": "{count} chunks",
        "en": "{count} chunks",
    },
    "kb_tab_documents": {
        "nl": "Documenten",
        "en": "Documents",
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
    "kb_sync_last": {
        "nl": "Laatste push",
        "en": "Last push",
    },
    "kb_sync_never": {
        "nl": "Nog geen push ontvangen",
        "en": "No push received yet",
    },
    "kb_sync_error": {
        "nl": "Kon kennisbank niet laden",
        "en": "Could not load knowledge base",
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
    "chat_stop": {
        "nl": "STOP",
        "en": "STOP",
    },
    "chat_stop_feedback": {
        "nl": "Vertel AITJE wat het beter moet doen",
        "en": "Tell AITJE what it should do better",
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
    "chat_focus_mode_label": {
        "nl": "Focus mode:",
        "en": "Focus mode:",
    },
    "chat_current_mode_label": {
        "nl": "Current mode: {mode}",
        "en": "Current mode: {mode}",
    },
    "chat_current_model_label": {
        "nl": "Huidig model : {model}",
        "en": "Current Model : {model}",
    },
    "chat_change_focus_mode": {
        "nl": "Wijzig focus mode",
        "en": "Change focus mode",
    },
    "chat_change_model": {
        "nl": "Wijzig model",
        "en": "Change model",
    },
    "chat_error_prefix": {
        "nl": "[fout]",
        "en": "[error]",
    },
    "chat_error_401": {
        "nl": "401 Unauthorized: backend verwacht een Bearer token. Vraag een token op via /api/v1/signon en zet AITJE_BEARER_TOKEN in de omgeving.",
        "en": "401 Unauthorized: backend expects a Bearer token. Request a token via /api/v1/signon and set AITJE_BEARER_TOKEN in the environment.",
    },
    "chat_error_tokens": {
        "nl": "geschatte tokens: {estimated} / limiet: {max}",
        "en": "estimated tokens: {estimated} / limit: {max}",
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
    "chat_sources_title": {
        "nl": "GEBRUIKTE BRONNEN",
        "en": "SOURCES USED",
    },
    "chat_sources_page": {
        "nl": "p. {page}",
        "en": "p. {page}",
    },
    "chat_sources_pages": {
        "nl": "p. {start}-{end}",
        "en": "p. {start}-{end}",
    },
    "chat_thinking_block": {
        "nl": "Nadenken",
        "en": "Thinking",
    },
    "chat_thinking_enabled": {
        "nl": "Nadenken aan",
        "en": "Thinking on",
    },
    "chat_thinking_disabled": {
        "nl": "Nadenken uit",
        "en": "Thinking off",
    },
    "chat_response_block": {
        "nl": "Antwoord",
        "en": "Response",
    },
    "chat_response_pending": {
        "nl": "Antwoord wordt opgebouwd...",
        "en": "Response is being generated...",
    },
    "chat_websearch_enabled": {
        "nl": "Web search aan",
        "en": "Web search on",
    },
    "chat_websearch_disabled": {
        "nl": "Web search uit",
        "en": "Web search off",
    },
    "chat_websearch_block": {
        "nl": "Web search",
        "en": "Web search",
    },
    "chat_websearch_status_searching": {
        "nl": "Web aan het doorzoeken…",
        "en": "Searching the web…",
    },
    "chat_websearch_status_results": {
        "nl": "Web search · {count} bronnen gevonden",
        "en": "Web search · {count} sources found",
    },
    "chat_websearch_status_error": {
        "nl": "Web search niet beschikbaar",
        "en": "Web search unavailable",
    },
    "chat_websearch_query_label": {
        "nl": "Zoekopdracht: {query}",
        "en": "Query: {query}",
    },
    "chat_websearch_error_unknown": {
        "nl": "Onbekende fout bij webzoekopdracht.",
        "en": "Unknown error during web search.",
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
        "nl": "Taal model",
        "en": "Language model",
    },
    "settings_focus_mode": {
        "nl": "Focus mode",
        "en": "Focus mode",
    },
    "settings_model": {
        "nl": "Model",
        "en": "Model",
    },
    "settings_remote_support": {
        "nl": "Remote support van AITJE",
        "en": "Remote support from AITJE",
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
