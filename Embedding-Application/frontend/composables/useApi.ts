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
  };
}
