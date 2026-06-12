/* Load-more pagination shared by the feed and profile post lists.
   Contract: fetchPage is stable for the component's lifetime (lists remount
   on context change — see the key in UserScreen). */

import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/shared/api'
import type { Paginated } from '@/entities/post'

export interface PaginatedListState<T> {
  items: T[]
  loading: boolean
  error: string | null
  hasNext: boolean
  total: number
  loadMore: () => void
}

export function usePaginatedList<T>(
  fetchPage: (page: number) => Promise<Paginated<T>>,
): PaginatedListState<T> {
  const [items, setItems] = useState<T[]>([])
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  /* Responses of superseded requests are ignored */
  const requestId = useRef(0)

  /* setState happens only in promise callbacks, so calling from useEffect
     causes no synchronous cascading renders */
  const run = useCallback(
    (pageToLoad: number, append: boolean) => {
      const id = ++requestId.current
      fetchPage(pageToLoad)
        .then((result) => {
          if (id !== requestId.current) return
          setItems((prev) => (append ? [...prev, ...result.items] : result.items))
          setPage(result.page)
          setHasNext(result.has_next)
          setTotal(result.total)
          setError(null)
        })
        .catch((err) => {
          if (id !== requestId.current) return
          setError(err instanceof ApiError ? err.message : 'Не удалось загрузить данные')
        })
        .finally(() => {
          if (id === requestId.current) setLoading(false)
        })
    },
    [fetchPage],
  )

  useEffect(() => {
    run(1, false)
  }, [run])

  const loadMore = useCallback(() => {
    setLoading(true)
    run(page + 1, true)
  }, [run, page])

  return { items, loading, error, hasNext, total, loadMore }
}
