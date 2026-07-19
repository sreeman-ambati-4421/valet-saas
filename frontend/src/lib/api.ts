const API_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function apiFetch<T>(
  path: string,
  accessToken: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      /* ignore non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
