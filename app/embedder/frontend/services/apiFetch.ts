import { Capacitor } from '@capacitor/core';
import { Http, type HttpResponse } from '@capacitor-community/http';
import { ApiError } from './ApiError';

function getApiBaseUrl(): string {
  const config = useRuntimeConfig();
  return config.public.apiBaseUrl as string;
}

function normalizeHeaders(headers?: HeadersInit): Record<string, string> {
  if (!headers) {
    return {};
  }

  if (headers instanceof Headers) {
    return Object.fromEntries(headers.entries());
  }

  if (Array.isArray(headers)) {
    return headers.reduce<Record<string, string>>((acc, [key, value]) => {
      acc[key] = value;
      return acc;
    }, {});
  }

  return { ...headers };
}

function parseBody(body?: BodyInit | null): any {
  if (!body) {
    return undefined;
  }

  if (typeof body === 'string') {
    try {
      return JSON.parse(body);
    } catch {
      return body;
    }
  }

  return body;
}

async function handleCapacitorRequest<T>(
  url: string,
  options: RequestInit,
  headers: Record<string, string>
): Promise<T> {
  const response: HttpResponse = await Http.request({
    url,
    method: (options.method || 'GET') as any,
    headers,
    data: parseBody(options.body),
  });

  const data = response.data;

  if (response.status < 200 || response.status >= 300) {
    throw new ApiError(
      (data as any)?.message || 'An error occurred',
      response.status,
      data
    );
  }

  return data as T;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = endpoint.startsWith('http') ? endpoint : `${baseUrl}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...normalizeHeaders(options.headers),
  };

  if (Capacitor.isNativePlatform()) {
    return handleCapacitorRequest<T>(url, options, headers);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      data?.message || 'An error occurred',
      response.status,
      data
    );
  }

  return data as T;
}
