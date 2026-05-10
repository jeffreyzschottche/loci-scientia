import { defineStore } from 'pinia'

export interface WebSource {
  title: string
  url: string
  snippet?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  images?: string[]
  documents?: AttachedDocument[]
  webSources?: WebSource[]
  timestamp: Date
}

export interface AttachedDocument {
  filename: string
  contentType?: string | null
}

export interface PromptHistoryItem {
  question: string
  answer: string
}

export interface ApiHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatState {
  messages: ChatMessage[]
  isLoading: boolean
  promptHistory: PromptHistoryItem[]
  isNewChat: boolean  // Flag to signal server to clear its history
}

export const useChatStore = defineStore('chat', {
  state: (): ChatState => ({
    messages: [],
    isLoading: false,
    promptHistory: [],
    isNewChat: false,
  }),

  getters: {
    getPromptHistoryString: (state) => {
      if (state.promptHistory.length === 0) return ''

      return state.promptHistory
        .map(item => `Q: ${item.question}\nA: ${item.answer}`)
        .join('\n\n')
    },
    getRequestHistory: (state): ApiHistoryMessage[] => {
      if (state.promptHistory.length === 0) return []

      return state.promptHistory.flatMap((item) => ([
        { role: 'user', content: item.question },
        { role: 'assistant', content: item.answer },
      ]))
    },
  },

  actions: {
    addMessage(
      role: 'user' | 'assistant',
      content: string,
      thinking?: string,
      images?: string[],
      documents?: AttachedDocument[],
    ) {
      const message: ChatMessage = {
        id: `${Date.now()}-${Math.random()}`,
        role,
        content,
        thinking,
        images,
        documents,
        timestamp: new Date(),
      }
      this.messages.push(message)
      return message.id
    },

    addUserMessage(content: string, images?: string[], documents?: AttachedDocument[]) {
      return this.addMessage('user', content, undefined, images, documents)
    },

    addAssistantMessage(content: string, thinking?: string) {
      return this.addMessage('assistant', content, thinking)
    },

    updateMessage(messageId: string, updates: Partial<Pick<ChatMessage, 'content' | 'thinking' | 'webSources'>>) {
      const message = this.messages.find(item => item.id === messageId)
      if (!message) return

      if (typeof updates.content === 'string') {
        message.content = updates.content
      }

      if (typeof updates.thinking === 'string') {
        message.thinking = updates.thinking
      }

      if (Array.isArray(updates.webSources)) {
        message.webSources = updates.webSources
      }
    },

    removeMessage(messageId: string) {
      this.messages = this.messages.filter(message => message.id !== messageId)
    },

    addToPromptHistory(question: string, answer: string) {
      this.promptHistory.push({ question, answer })
    },

    setLoading(loading: boolean) {
      this.isLoading = loading
    },

    clearMessages() {
      this.messages = []
      this.promptHistory = []
      this.isNewChat = true  // Signal server to clear history on next request
    },

    consumeNewChatFlag(): boolean {
      // Returns true if this is a new chat, then resets the flag
      const wasNewChat = this.isNewChat
      this.isNewChat = false
      return wasNewChat
    },
  },
})
