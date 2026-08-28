export class ApiError extends Error {
  constructor(message, status = 0, code = 'API_ERROR') {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

const rawApiUrl = import.meta.env.VITE_API_URL
export const API_URL = (rawApiUrl || '').trim().replace(/\/+$/, '')
export const API_BASE_URL = API_URL
const productionApiConfigurationError = import.meta.env.PROD && (!API_URL || !/^https:\/\//i.test(API_URL) || /localhost|127\.0\.0\.1/i.test(API_URL))
const DEFAULT_TIMEOUT_MS = 5000

export async function fetchJson(path, options = {}) {
  if (productionApiConfigurationError) {
    throw new ApiError('Production API URL is not configured. Set VITE_API_URL to the deployed HTTPS backend.', 503, 'API_CONFIGURATION_ERROR')
  }
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), options.timeout ?? DEFAULT_TIMEOUT_MS)
  const requestOptions = { ...options, signal: controller.signal }
  delete requestOptions.timeout

  try {
    const response = await fetch(path, { credentials: 'include', ...requestOptions })
    const contentType = response.headers.get('content-type') || ''
    const text = await response.text()
    let body = null

    if (text.trim()) {
      if (!contentType.includes('application/json')) {
        throw new ApiError(`API returned ${contentType || 'non-JSON'} instead of JSON.`, response.status, 'INVALID_RESPONSE_FORMAT')
      }
      try {
        body = JSON.parse(text)
      } catch {
        throw new ApiError('API returned invalid JSON.', response.status, 'INVALID_JSON')
      }
    }

    if (!response.ok) {
      const error = body?.error
      const message = typeof error === 'object' ? error.message : error || body?.message
      throw new ApiError(message || `Request failed with HTTP ${response.status}.`, response.status, typeof error === 'object' ? error.code : 'HTTP_ERROR')
    }
    if (body === null) throw new ApiError('API returned an empty response.', response.status, 'EMPTY_RESPONSE')
    return body
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error.name === 'AbortError') throw new ApiError('The backend is waking up or responding slowly. Please try again in a moment.', 408, 'TIMEOUT')
    throw new ApiError('Unable to connect to the production API. Check the backend deployment and VITE_API_URL configuration.', 0, 'NETWORK_ERROR')
  } finally {
    clearTimeout(timeout)
  }
}

export function parseEventJson(event) {
  try {
    return JSON.parse(event.data)
  } catch {
    return null
  }
}
