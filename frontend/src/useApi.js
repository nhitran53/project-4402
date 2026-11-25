import { useCallback, useEffect, useState } from 'react'
import { api, apiUrl } from './api'

export function useApi(path, params, body) {
  const url = path ? apiUrl(path, params) : null
  const payload = body === undefined ? undefined : JSON.stringify(body)
  const [result, setResult] = useState(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!url) return
    const controller = new AbortController()
    const options = { signal: controller.signal }
    if (payload !== undefined) {
      options.method = 'POST'
      options.body = JSON.parse(payload)
    }

    function finish(data, error) {
      if (!controller.signal.aborted) setResult({ url, payload, attempt, data, error })
    }

    api(url, options).then((data) => finish(data, null), (error) => finish(null, error))
    return () => controller.abort()
  }, [url, payload, attempt])

  const reload = useCallback(() => setAttempt((value) => value + 1), [])
  const current = url && result?.url === url && result.payload === payload && result.attempt === attempt
  return {
    data: current ? result.data : null,
    error: current ? result.error : null,
    loading: Boolean(url && !current),
    reload,
  }
}

export function useCategories() {
  const { data, ...request } = useApi('/categories')
  return { ...request, categories: data || [] }
}
