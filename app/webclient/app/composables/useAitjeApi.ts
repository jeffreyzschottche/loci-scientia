import { useAuthStore } from '~/stores/auth'
import { useChatLogger } from '~/composables/useChatLogger'
import { useI18nStore, type TranslationKey } from '~/stores/i18n'
import type { ApiHistoryMessage } from '~/stores/chat'

interface SignonResponse {
  token: string
  expires_at: string
}

interface AskStreamResponse {
  message: string
  thinking: string
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
  maxNewTokens?: number
  history?: ApiHistoryMessage[]
  images?: string[]
  documents?: PromptDocumentPayload[]
  newChat?: boolean
  signal?: AbortSignal
  onToken?: (content: string, delta: string) => void
  onThinking?: (thinking: string, delta: string) => void
  onQueue?: (position: number) => void
}

interface StreamEventPayload {
  status?: string
  position?: number
  token?: string
  thinking?: string
  message?: string
  done?: boolean
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
      maxNewTokens = 128,
      history = [],
      images = [],
      documents = [],
      newChat = false,
      signal,
      onToken,
      onThinking,
      onQueue,
    } = request

    const requestBody = {
      prompt,
      mode,
      thinking,
      max_new_tokens: maxNewTokens,
      history,
      images,
      documents,
      new_chat: newChat,
    }

    logApiPost({
      url,
      prompt,
      mode,
      thinking,
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

      const processEventPayload = (payload: StreamEventPayload) => {
        if (payload.status === 'queued' && typeof payload.position === 'number') {
          onQueue?.(payload.position)
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
