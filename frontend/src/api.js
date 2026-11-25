const TOKEN_KEY = 'pcparts.token'
let sessionToken

export function getToken() {
  if (sessionToken !== undefined) return sessionToken
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  sessionToken = token
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Keep the session in memory if storage is unavailable.
  }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export function apiUrl(path, params) {
  let url = path
  if (params) {
    const search = new URLSearchParams()
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === '') continue
      search.set(key, Array.isArray(value) ? value.join(',') : value)
    }
    const query = search.toString()
    if (query) url += `?${query}`
  }

  return url
}

export async function api(path, { method = 'GET', body, params, signal } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response
  try {
    response = await fetch(`/api${apiUrl(path, params)}`, { method, headers, signal, body: body === undefined ? undefined : JSON.stringify(body) })
  } catch {
    throw new ApiError('Could not connect. Check that the local server is running.', 0)
  }

  let data = null
  try {
    data = await response.json()
  } catch {
    throw new ApiError(`The server returned an invalid response (HTTP ${response.status}).`, response.status)
  }
  if (!response.ok) {
    throw new ApiError(data?.error || `Request failed (HTTP ${response.status}).`, response.status)
  }
  return data
}
