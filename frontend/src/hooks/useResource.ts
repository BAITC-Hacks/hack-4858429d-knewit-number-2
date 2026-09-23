import { useCallback, useEffect, useState } from 'react'

// Pass a stable loader (an imported function or useCallback) to avoid extra requests.
export function useResource<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<unknown>(null)
  const [revision, setRevision] = useState(0)
  const reload = useCallback(() => setRevision((value) => value + 1), [])

  useEffect(() => {
    let active = true
    setData(null)
    setError(null)
    setLoading(true)
    load()
      .then((value) => { if (active) setData(value) })
      .catch((reason: unknown) => { if (active) setError(reason) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [load, revision])

  return { data, setData, loading, error, reload }
}
