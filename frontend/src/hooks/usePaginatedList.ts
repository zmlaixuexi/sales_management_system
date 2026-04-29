import { useState, useEffect, useCallback, useRef } from 'react'
import { message } from 'antd'

interface PaginatedResult<T> {
  items: T[]
  total: number
}

export function usePaginatedList<T>(
  fetchFn: (params: Record<string, unknown>) => Promise<PaginatedResult<T>>,
  filters: Record<string, unknown> = {},
  errorMessage = '加载数据失败',
) {
  const [data, setData] = useState<T[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')

  const fetchFnRef = useRef(fetchFn)
  useEffect(() => { fetchFnRef.current = fetchFn })

  const filtersKey = JSON.stringify(filters)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await fetchFnRef.current({
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
        ...filters,
      })
      setData(result.items ?? [])
      setTotal(result.total ?? 0)
    } catch {
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, keyword, filtersKey, errorMessage])

  useEffect(() => { loadData() }, [loadData])

  return {
    data, total, loading,
    page, pageSize, keyword,
    setPage,
    setKeyword: (value: string) => { setKeyword(value); setPage(1) },
    onPageChange: (p: number, ps: number) => { setPage(p); setPageSize(ps) },
    refresh: loadData,
  }
}
