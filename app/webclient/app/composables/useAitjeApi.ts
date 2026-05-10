import { useAuthStore } from '~/stores/auth'
import { useChatLogger } from '~/composables/useChatLogger'
import { useI18nStore, type TranslationKey } from '~/stores/i18n'
import type { ApiHistoryMessage } from '~/stores/chat'

interface SignonResponse {
  token: string
  expires_at: string
}

export interface WebSource {
  title: string
  url: string
  snippet?: string
}

export type WebSearchStatus =
  | { type: 'searching', query: string }
  | { type: 'fetching', index: number, total: number, url: string }
  | { type: 'summarizing' }

interface AskStreamResponse {
  message: string
  thinking: string
  webSources?: WebSource[]
}

interface PromptDocumentPayload {
  filename: string
  data: string
  content_type?: string | null
}

interface AskRequest {
  prompt: string
  mode?: string | null
  thinking?: boolean
  webSearch?: boolean
  maxNewTokens?: number
  history?: ApiHistoryMessage[]
  images?: string[]
  documents?: PromptDocumentPayload[]
  newChat?: boolean
  signal?: AbortSignal
  onToken?: (content: string, delta: string) => void
  onThinking?: (thinking: string, delta: string) => void
  onQueue?: (position: number) => void
  onSearchStatus?: (status: WebSearchStatus) => void
  onWebSources?: (sources: WebSource[]) => void
}

interface BackendWebSearchEnvelope {
  status?: string
  query?: string
  results?: Array<{ title?: string, url?: string, snippet?: string, engine?: string }>
  error?: string
}

interface StreamEventPayload {
  status?: string
  position?: number
  token?: string
  thinking?: string
  message?: string
  done?: boolean
  web_search?: BackendWebSearchEnvelope
  web_results?: Array<{ title?: string, url?: string, snippet?: string, engine?: string }>
  web_search_error?: string
}

type AitjeError = Error & { code?: string }

const createError = (message: string, code?: string): AitjeError => {
  const err = new Error(message) as AitjeError
  if (code) {
    err.code = code
  }
  return err
}

export const useAitjeApi = () => {
  const authStore = useAuthStore()
  const i18nStore = useI18nStore()

  const translate = (key: TranslationKey, vars?: Record<string, string | number>) => {
    return i18nStore.translate(key, vars)
  }

  const handleApiError = (error: any, context: string, url?: string): never => {
    console.error(`${context} error:`, error)
    console.error('Full error object:', JSON.stringify(error, null, 2))
    console.error('Error name:', error.name)
    console.error('Error message:', error.message)
    if (url) console.error('URL:', url)

    const errorMessage = String(error?.message || '').toLowerCase()
    const isAbortError =
      error?.name === 'AbortError'
      || error?.code === 'REQUEST_ABORTED'
      || errorMessage.includes('aborted')
      || errorMessage.includes('abort')

    if (isAbortError) {
      throw createError('Request aborted', 'REQUEST_ABORTED')
    }

    if ((error as AitjeError)?.code) {
      throw error
    }

    if (error instanceof TypeError && error.message?.includes('fetch')) {
      const target = url || translate('errors.networkDefaultTarget')
      throw createError(translate('errors.network', { target }), 'NETWORK_ERROR')
    }

    throw createError(error.message || translate('errors.unknown'), 'UNKNOWN_ERROR')
  }

  const signon = async (username: string, password: string): Promise<SignonResponse> => {
    if (!authStore.baseUrl) {
      throw createError(translate('errors.deviceNotConfigured'), 'DEVICE_NOT_CONFIGURED')
    }

    const url = `${authStore.baseUrl}/api/v1/signon`
    console.log('Sign-on URL:', url)

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_name: username,
          password: password,
        }),
      })

      console.log('Sign-on response status:', response.status)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('Sign-on error response:', errorText)
        throw createError(
          translate('errors.loginFailed', {
            status: response.status,
            message: errorText || response.statusText,
          }),
          'LOGIN_FAILED',
        )
      }

      const data = await response.json()
      console.log('Sign-on response data:', data)

      if (!data.token) {
        throw createError(translate('errors.noToken'), 'LOGIN_NO_TOKEN')
      }

      return data
    } catch (error: any) {
      handleApiError(error, 'Sign-on', url)
    }
  }

  const ask = async (request: AskRequest): Promise<AskStreamResponse> => {
    if (!authStore.baseUrl) {
      throw createError(translate('errors.deviceNotConfigured'), 'DEVICE_NOT_CONFIGURED')
    }

    if (!authStore.bearerToken) {
      throw createError(translate('errors.notLoggedIn'), 'NOT_AUTHENTICATED')
    }

    const { logApiPost, logApiGet } = useChatLogger()
    const url = `${authStore.baseUrl}/api/v1/ask/stream`
    const {
      prompt,
      mode = null,
      thinking = true,
      webSearch = false,
      maxNewTokens = 128,
      history = [],
      images = [],
      documents = [],
      newChat = false,
      signal,
      onToken,
      onThinking,
      onQueue,
      onSearchStatus,
      onWebSources,
    } = request

    const requestBody: Record<string, unknown> = {
      prompt,
      mode,
      thinking,
      max_new_tokens: maxNewTokens,
      history,
      images,
      documents,
      new_chat: newChat,
    }

    if (webSearch) {
      requestBody.web_search = true
    }

    logApiPost({
      url,
      prompt,
      mode,
      thinking,
      webSearch,
      maxNewTokens,
      historyLength: history.length,
      imagesCount: images.length,
      documentsCount: documents.length,
      newChat,
    })

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'Authorization': `Bearer ${authStore.bearerToken}`,
        },
        body: JSON.stringify(requestBody),
        signal,
      })

      if (!response.ok) {
        if (response.status === 401) {
          authStore.clearAuth()
          throw createError(translate('errors.sessionExpired'), 'SESSION_EXPIRED')
        }

        const errorText = await response.text()
        throw createError(
          translate('errors.askFailed', {
            status: response.status,
            message: errorText || response.statusText,
          }),
          'ASK_FAILED',
        )
      }

      if (!response.body) {
        throw createError('Streaming response body is missing', 'ASK_STREAM_UNAVAILABLE')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let message = ''
      let finalThinking = ''
      let webSources: WebSource[] | undefined

      const normalizeWebSources = (
        items?: Array<{ title?: string, url?: string, snippet?: string }>,
      ): WebSource[] => {
        if (!Array.isArray(items)) return []
        return items
          .filter(item => item && typeof item.url === 'string' && item.url.length > 0)
          .map(item => ({
            title: typeof item.title === 'string' && item.title ? item.title : (item.url as string),
            url: item.url as string,
            snippet: typeof item.snippet === 'string' ? item.snippet : undefined,
          }))
      }

      const processEventPayload = (payload: StreamEventPayload) => {
        if (payload.status === 'queued' && typeof payload.position === 'number') {
          onQueue?.(payload.position)
          return
        }

        // Backend emits web search progress under a `web_search` envelope.
        if (payload.web_search && typeof payload.web_search === 'object') {
          const envelope = payload.web_search
          if (envelope.status === 'started' && typeof envelope.query === 'string') {
            onSearchStatus?.({ type: 'searching', query: envelope.query })
          } else if (envelope.status === 'results') {
            const sources = normalizeWebSources(envelope.results)
            if (sources.length > 0) {
              webSources = sources
              onWebSources?.(sources)
            }
            onSearchStatus?.({ type: 'summarizing' })
          }
          // 'unavailable' / 'error' statuses fall through silently — generation continues.
          return
        }

        if (payload.done === true) {
          if (typeof payload.message === 'string') {
            message = payload.message
            onToken?.(message, '')
          }

          if (typeof payload.thinking === 'string') {
            finalThinking = payload.thinking
            onThinking?.(finalThinking, '')
          }

          if (Array.isArray(payload.web_results) && payload.web_results.length > 0) {
            const sources = normalizeWebSources(payload.web_results)
            if (sources.length > 0) {
              webSources = sources
              onWebSources?.(sources)
            }
          }

          return
        }

        if (typeof payload.thinking === 'string') {
          finalThinking += payload.thinking
          onThinking?.(finalThinking, payload.thinking)
        }

        if (typeof payload.token === 'string') {
          message += payload.token
          onToken?.(message, payload.token)
        }
      }

      const processFrame = (frame: string) => {
        const lines = frame.split(/\r?\n/)

        for (const line of lines) {
          if (!line.startsWith('data:')) continue

          const rawData = line.slice(5).trim()
          if (!rawData) continue

          try {
            const payload = JSON.parse(rawData) as StreamEventPayload
            processEventPayload(payload)
          } catch (parseError) {
            console.error('Failed to parse ask stream payload:', rawData, parseError)
            throw createError('Failed to parse streaming response', 'ASK_STREAM_PARSE_ERROR')
          }
        }
      }

      while (true) {
        const { value, done } = await reader.read()
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

        const frames = buffer.split(/\r?\n\r?\n/)
        buffer = frames.pop() || ''

        for (const frame of frames) {
          processFrame(frame)
        }

        if (done) {
          break
        }
      }

      if (buffer.trim()) {
        processFrame(buffer)
      }

      const data: AskStreamResponse = {
        message,
        thinking: finalThinking,
        webSources,
      }

      logApiGet({
        url,
        status: response.status,
        data,
      })

      return data
    } catch (error: any) {
      handleApiError(error, 'Ask', url)
    }
  }

  return {
    signon,
    ask,
  }
}
