import { env } from "../config/env";

export function apiUrl(path: string): string {
  return `${env.apiUrl}${path}`;
}

export function assetUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  if (path.startsWith("/api/")) {
    return `${apiOrigin()}${path}`;
  }
  return apiUrl(path);
}

function apiOrigin(): string {
  return new URL(env.apiUrl).origin;
}

export async function parseJsonResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `HTTP ${response.status}`);
  }
  return payload as T;
}
