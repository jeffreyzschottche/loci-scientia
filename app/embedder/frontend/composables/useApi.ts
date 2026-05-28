import { apiFetch } from '~/services/apiFetch';

export function useApi() {
  const authStore = useAuthStore();

  async function request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (authStore.token) {
      headers.Authorization = `Bearer ${authStore.token}`;
    }

    return apiFetch<T>(endpoint, {
      ...options,
      headers,
    });
  }

  async function download(endpoint: string): Promise<{ blob: Blob; filename: string }> {
    const config = useRuntimeConfig();
    const baseUrl = config.public.apiBaseUrl as string;
    const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      Accept: 'application/zip',
    };

    if (authStore.token) {
      headers.Authorization = `Bearer ${authStore.token}`;
    }

    const response = await fetch(url, { method: 'GET', headers });
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.message || data?.detail?.message || 'Download mislukt');
    }

    const disposition = response.headers.get('Content-Disposition') || '';
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
    return {
      blob: await response.blob(),
      filename: filenameMatch?.[1] || 'aitje-kennisbank-backup.zip',
    };
  }

  return {
    get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),

    post: <T>(endpoint: string, data?: any) =>
      request<T>(endpoint, {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    patch: <T>(endpoint: string, data?: any) =>
      request<T>(endpoint, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    delete: <T>(endpoint: string) =>
      request<T>(endpoint, { method: 'DELETE' }),

    download,
  };
}
