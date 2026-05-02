import { useState, useEffect, useCallback, useRef } from 'react'
import { message } from 'antd'

interface PaginatedResult<T> {
  items: T[]
  total: number
}

export function usePaginatedList<T>(
  fetchFn: (_params: Record<string, unknown>) => Promise<PaginatedResult<T>>,
  filters: Record<string, unknown> = {},
  errorMessage = '加载数据失败',
) {
  const [data, setData] = useState<T[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')

  const fetchFnRef = useRef(fetchFn)
  useEffect(() => { fetchFnRef.current = fetchFn })

  const filtersKey = JSON.stringify(filters)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const result = await fetchFnRef.current({
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
        ...filters,
      })
      setData(result.items ?? [])
      setTotal(result.total ?? 0)
    } catch (e: unknown) {
      setError(true)
      // 拦截器已展示过 toast 时跳过，避免重复提示
      if ((e as Record<string, boolean>)?._toastDisplayed) {
        // nothing
      } else {
        message.error(errorMessage)
      }
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, keyword, filtersKey, errorMessage])

  useEffect(() => { loadData() }, [loadData])

  return {
    data, total, loading, error,
    page, pageSize, keyword,
    setPage,
    setKeyword: (value: string) => { setKeyword(value); setPage(1) },
    onPageChange: (p: number, ps: number) => { setPage(p); setPageSize(ps) },
    refresh: loadData,
  }
}
