import { defineStore } from 'pinia'

type Locale = 'nl' | 'en'

const locales: Locale[] = ['nl', 'en']

const nl = {
  'common.tagline': 'Lokale AI console',
  'common.language.nl': 'Nederlands',
  'common.language.en': 'Engels',
  'common.language.switch': 'Schakel naar {{language}}',
  'common.language.current': 'Huidige taal: {{language}}',
  'app.metaDescription': 'Verbind met je lokale AITJE AI assistent',
  'header.logout': 'Uitloggen',
  'header.switchDevice': 'Apparaat',
  'header.statusPrefix': 'Verbonden:',
  'header.newChat': 'Nieuwe chat',
  'header.welcome': 'Welkom bij AITJE...',
  'header.languageLabel': 'Taal',
  'chat.placeholder': 'Stel een vraag aan Aitje.',
  'chat.newChatTitle': 'Nieuwe chat starten',
  'chat.newChatMessage': 'Weet je zeker dat je een nieuwe chat wilt starten? De huidige chat wordt gewist.',
  'chat.error.general': 'Er is een fout opgetreden',
  'chat.error.imageReadFailed': 'Afbeelding kon niet worden geladen',
  'chat.error.unsupportedImageType': 'Bestandstype niet ondersteund. Gebruik PNG, JPG of JPEG.',
  'chat.error.documentReadFailed': 'Document kon niet worden geladen',
  'chat.error.unsupportedDocumentType': 'Bestandstype niet ondersteund. Gebruik PDF, DOC, DOCX, XLS, XLSX of TXT.',
  'chat.emptyState': 'Welkom bij AITJE...',
  'chat.attach': 'Bijlage',
  'chat.attachImage': 'Foto',
  'chat.attachDocument': 'Document',
  'chat.openCamera': 'Camera',
  'chat.removeImage': 'Verwijder afbeelding',
  'chat.removeDocument': 'Verwijder document',
  'chat.reasoning': 'Redeneren',
  'chat.attachmentsOnly': '[Bijlage toegevoegd]',
  'chat.send': 'Stuur',
  'chat.webSearch.toggleLabel': 'Web zoeken',
  'chat.webSearch.searching': 'Web zoeken naar {{query}}…',
  'chat.webSearch.fetching': 'Bron {{index}}/{{total}} lezen…',
  'chat.webSearch.summarizing': 'Resultaten samenvatten…',
  'chat.webSearch.sourcesHeading': 'Bronnen',
  'chat.stop': 'Stop',
  'chat.stopFeedbackPlaceholder': 'Vertel AITJE wat het beter of anders moet doen.',
  'chat.stoppedTitle': 'Generatie gestopt',
  'chat.stoppedMessage': 'Vertel AITJE wat het beter of anders moet doen.',
  'chat.disclaimer': 'Aitje is AI en kan ook fouten maken, controleer belangrijke informatie.',
  'modal.cancel': 'Annuleren',
  'modal.confirm': 'Bevestigen',
  'message.copy': 'Kopieer',
  'message.copied': 'Gekopieerd!',
  'message.print': 'Print',
  'message.printTitle': 'AITJE - Bericht',
  'login.title': 'Inloggen',
  'login.connectedWith': 'Verbonden met: aitje-{{device}}',
  'login.connectTo': 'Verbind met: {{url}}',
  'login.username': 'Gebruikersnaam',
  'login.password': 'Wachtwoord',
  'login.submit': 'Inloggen',
  'login.loading': 'Bezig met inloggen...',
  'login.errorTitle': 'Fout bij inloggen:',
  'login.changeDevice': 'Ander device kiezen',
  'login.footerPrefix': 'Vragen of hulp nodig? ',
  'login.footerLink': 'Neem contact op met Aitje',
  'login.footerSuffix': '.',
  'setup.title': 'Wat is het device nummer van jouw AITJE?',
  'setup.label': 'Device nummer',
  'setup.helper': 'Voer het nummer in dat op jouw fysieke AITJE staat',
  'setup.submit': 'Doorgaan',
  'status.connectedLabel': 'Verbonden:',
  'status.connectedValue': 'aitje-{{device}}',
  'status.connectedUnknown': 'Onbekend apparaat',
  'errors.deviceNotConfigured': 'Device nummer niet geconfigureerd',
  'errors.notLoggedIn': 'Niet ingelogd',
  'errors.network': 'Kan niet verbinden met {{target}}.\n\nControleer:\n• AITJE is online\n• Je zit op hetzelfde WiFi netwerk\n• Het device nummer is correct',
  'errors.networkDefaultTarget': 'de server',
  'errors.unknown': 'Er is een onbekende fout opgetreden',
  'errors.sessionExpired': 'Sessie verlopen. Log opnieuw in.',
  'errors.askFailed': 'Vraag versturen mislukt: {{status}} - {{message}}',
  'errors.loginFailed': 'Inloggen mislukt ({{status}}): {{message}}',
  'errors.noToken': 'Geen token ontvangen van de server',
  'errors.loginGeneric': 'Er is een fout opgetreden bij het inloggen',
  'sidebar.chat': 'Chat',
  'sidebar.api': 'API Management',
  'sidebar.knowledge': 'Kennisbank',
  'sidebar.maps': 'Maps',
  'sidebar.contacts': 'Contacten',
  'sidebar.network': 'Network Status',
  'sidebar.connectedDevices': 'Connected Devices',
  'sidebar.settings': 'Instellingen',
  'sidebar.faq': 'FAQ',
} as const

type TranslationKey = keyof typeof nl

const en: Record<TranslationKey, string> = {
  'common.tagline': 'Local AI console',
  'common.language.nl': 'Dutch',
  'common.language.en': 'English',
  'common.language.switch': 'Switch to {{language}}',
  'common.language.current': 'Current language: {{language}}',
  'app.metaDescription': 'Connect with your local AITJE AI assistant',
  'header.logout': 'Log out',
  'header.switchDevice': 'Device',
  'header.statusPrefix': 'Connected:',
  'header.newChat': 'New chat',
  'header.welcome': 'Welcome to AITJE...',
  'header.languageLabel': 'Language',
  'chat.placeholder': 'Ask AITJE a question.',
  'chat.newChatTitle': 'Start a new chat',
  'chat.newChatMessage': 'Are you sure you want to start a new chat? The current conversation will be cleared.',
  'chat.error.general': 'Something went wrong',
  'chat.error.imageReadFailed': 'Could not load image',
  'chat.error.unsupportedImageType': 'Unsupported file type. Use PNG, JPG, or JPEG.',
  'chat.error.documentReadFailed': 'Could not load document',
  'chat.error.unsupportedDocumentType': 'Unsupported file type. Use PDF, DOC, DOCX, XLS, XLSX, or TXT.',
  'chat.emptyState': 'Welcome to AITJE...',
  'chat.attach': 'Attach',
  'chat.attachImage': 'Photo',
  'chat.attachDocument': 'Document',
  'chat.openCamera': 'Camera',
  'chat.removeImage': 'Remove image',
  'chat.removeDocument': 'Remove document',
  'chat.reasoning': 'Reasoning',
  'chat.attachmentsOnly': '[Attachment added]',
  'chat.send': 'Send',
  'chat.webSearch.toggleLabel': 'Web search',
  'chat.webSearch.searching': 'Searching the web for {{query}}…',
  'chat.webSearch.fetching': 'Reading source {{index}}/{{total}}…',
  'chat.webSearch.summarizing': 'Summarizing results…',
  'chat.webSearch.sourcesHeading': 'Sources',
  'chat.stop': 'Stop',
  'chat.stopFeedbackPlaceholder': 'Tell AITJE what it should do better or differently.',
  'chat.stoppedTitle': 'Generation stopped',
  'chat.stoppedMessage': 'Tell AITJE what it should do better or differently.',
  'chat.disclaimer': 'Aitje is AI and can also make mistakes, verify important information.',
  'modal.cancel': 'Cancel',
  'modal.confirm': 'Confirm',
  'message.copy': 'Copy',
  'message.copied': 'Copied!',
  'message.print': 'Print',
  'message.printTitle': 'AITJE - Message',
  'login.title': 'Sign in',
  'login.connectedWith': 'Connected with: aitje-{{device}}',
  'login.connectTo': 'Connect to: {{url}}',
  'login.username': 'Username',
  'login.password': 'Password',
  'login.submit': 'Sign in',
  'login.loading': 'Signing in...',
  'login.errorTitle': 'Login error:',
  'login.changeDevice': 'Choose another device',
  'login.footerPrefix': 'Questions or need help? ',
  'login.footerLink': 'Contact Aitje',
  'login.footerSuffix': '.',
  'setup.title': 'What is the device number of your AITJE?',
  'setup.label': 'Device number',
  'setup.helper': 'Enter the number shown on your physical AITJE',
  'setup.submit': 'Continue',
  'status.connectedLabel': 'Connected:',
  'status.connectedValue': 'aitje-{{device}}',
  'status.connectedUnknown': 'Unknown device',
  'errors.deviceNotConfigured': 'Device number not configured',
  'errors.notLoggedIn': 'Not signed in',
  'errors.network': 'Unable to connect to {{target}}.\n\nCheck:\n• AITJE is online\n• You are on the same Wi-Fi network\n• The device number is correct',
  'errors.networkDefaultTarget': 'the server',
  'errors.unknown': 'An unknown error occurred',
  'errors.sessionExpired': 'Session expired. Please sign in again.',
  'errors.askFailed': 'Failed to send question: {{status}} - {{message}}',
  'errors.loginFailed': 'Login failed ({{status}}): {{message}}',
  'errors.noToken': 'No token received from the server',
  'errors.loginGeneric': 'An error occurred during sign in',
  'sidebar.chat': 'Chat',
  'sidebar.api': 'API Management',
  'sidebar.knowledge': 'Knowledge base',
  'sidebar.maps': 'Maps',
  'sidebar.contacts': 'Contacts',
  'sidebar.network': 'Network status',
  'sidebar.connectedDevices': 'Connected devices',
  'sidebar.settings': 'Settings',
  'sidebar.faq': 'FAQ',
}

const translations: Record<Locale, Record<TranslationKey, string>> = {
  nl,
  en,
}

interface I18nState {
  locale: Locale
}

const DEFAULT_LOCALE: Locale = 'nl'

const interpolate = (template: string, vars: Record<string, string | number> = {}) => {
  return template.replace(/{{(.*?)}}/g, (_, rawKey) => {
    const key = rawKey.trim()
    const value = vars[key]
    return typeof value === 'undefined' ? '' : String(value)
  })
}

export const useI18nStore = defineStore('i18n', {
  state: (): I18nState => ({
    locale: DEFAULT_LOCALE,
  }),
  getters: {
    availableLocales: () => locales,
  },
  actions: {
    setLocale(nextLocale: Locale) {
      if (!translations[nextLocale]) return
      this.locale = nextLocale
      if (typeof window !== 'undefined') {
        localStorage.setItem('aitje_locale', nextLocale)
      }
      if (typeof document !== 'undefined') {
        document.documentElement.lang = nextLocale
      }
    },
    initLocale() {
      if (typeof window === 'undefined') return
      const saved = localStorage.getItem('aitje_locale') as Locale | null
      if (saved && translations[saved]) {
        this.locale = saved
      } else {
        this.locale = DEFAULT_LOCALE
      }
      if (typeof document !== 'undefined') {
        document.documentElement.lang = this.locale
      }
    },
    translate(key: TranslationKey, vars: Record<string, string | number> = {}) {
      const template = translations[this.locale]?.[key]
      if (!template) {
        return key
      }
      return interpolate(template, vars)
    },
  },
})

export type { Locale, TranslationKey }
