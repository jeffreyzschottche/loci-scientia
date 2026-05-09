interface LogEntry {
  type: 'apiPOST' | 'apiGET'
  timestamp: string
  data: any
}

export const useChatLogger = () => {
  const logFilePath = 'chatlog.json'
  let logs: LogEntry[] = []

  const loadLogs = () => {
    if (typeof window === 'undefined') return

    try {
      const stored = localStorage.getItem('aitje_chatlog')
      if (stored) {
        logs = JSON.parse(stored)
      }
    } catch (e) {
      console.error('Failed to load chat logs:', e)
      logs = []
    }
  }

  const saveLogs = () => {
    if (typeof window === 'undefined') return

    try {
      localStorage.setItem('aitje_chatlog', JSON.stringify(logs))
    } catch (e) {
      console.error('Failed to save chat logs:', e)
    }
  }

  const logApiPost = (data: any) => {
    loadLogs()

    const entry: LogEntry = {
      type: 'apiPOST',
      timestamp: new Date().toISOString(),
      data,
    }

    logs.push(entry)
    saveLogs()
  }

  const logApiGet = (data: any) => {
    loadLogs()

    const entry: LogEntry = {
      type: 'apiGET',
      timestamp: new Date().toISOString(),
      data,
    }

    logs.push(entry)
    saveLogs()
  }

  const clearLogs = () => {
    logs = []
    if (typeof window !== 'undefined') {
      localStorage.removeItem('aitje_chatlog')
    }
  }

  const downloadLogs = () => {
    loadLogs()

    const dataStr = JSON.stringify(logs, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = logFilePath
    link.click()
    URL.revokeObjectURL(url)
  }

  return {
    logApiPost,
    logApiGet,
    clearLogs,
    downloadLogs,
  }
}
