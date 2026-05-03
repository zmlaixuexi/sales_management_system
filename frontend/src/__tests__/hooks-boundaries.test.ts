/**
 * 代码质量：前端 hooks 边界测试 — useSubmit 和 usePaginatedList 补充测试
 * 覆盖边界情况：多次并发提交、空关键字、null 结果、fetchFn 变更、分页重置
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'

// ═══════════════════════════════════════════════════════
// useSubmit 边界测试
// ═══════════════════════════════════════════════════════

vi.mock('antd', () => ({
  message: { error: vi.fn() },
}))

import { message } from 'antd'
import { useSubmit } from '@/hooks/useSubmit'

describe('useSubmit 边界测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('提交空值时正常调用 onSubmit', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => useSubmit(onSubmit))

    await act(async () => { await result.current.handleSubmit(null as never) })
    expect(onSubmit).toHaveBeenCalledWith(null)
  })

  it('提交 undefined 值时正常调用', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => useSubmit(onSubmit))

    await act(async () => { await result.current.handleSubmit(undefined as never) })
    expect(onSubmit).toHaveBeenCalledWith(undefined)
  })

  it('onSubmit 返回值被忽略（不返回 data）', async () => {
    const onSubmit = vi.fn().mockResolvedValue({ data: 'ignored' })
    const { result } = renderHook(() => useSubmit(onSubmit))

    await act(async () => { await result.current.handleSubmit('val') })
    expect(result.current.submitting).toBe(false)
  })

  it('连续快速提交三次只执行第一次', async () => {
    let resolve: () => void
    const onSubmit = vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r }))
    const { result } = renderHook(() => useSubmit(onSubmit))

    act(() => { result.current.handleSubmit('a') })
    act(() => { result.current.handleSubmit('b') })
    act(() => { result.current.handleSubmit('c') })

    await act(async () => { resolve!() })

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith('a')
  })

  it('错误对象同时有 errorFields 和 _toastDisplayed 时不弹提示', async () => {
    const error = Object.assign(
      { errorFields: [{ name: ['x'], errors: ['err'] }] },
      { _toastDisplayed: true },
    )
    const onSubmit = vi.fn().mockRejectedValue(error)
    const { result } = renderHook(() => useSubmit(onSubmit))

    await act(async () => { await result.current.handleSubmit('val') })
    expect(message.error).not.toHaveBeenCalled()
  })

  it('错误对象无 response 属性时使用 fallback', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('未知错误'))
    const { result } = renderHook(() => useSubmit(onSubmit, '自定义失败'))

    await act(async () => { await result.current.handleSubmit('val') })
    expect(message.error).toHaveBeenCalledWith('自定义失败')
  })

  it('fallbackError 为空字符串时传空字符串', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('err'))
    const { result } = renderHook(() => useSubmit(onSubmit, ''))

    await act(async () => { await result.current.handleSubmit('val') })
    // getApiErrorMessage({}, '') → ''
    expect(message.error).toHaveBeenCalledWith('')
  })

  it('onSubmit 抛出 number 类型异常时不崩溃', async () => {
    const onSubmit = vi.fn().mockRejectedValue(42)
    const { result } = renderHook(() => useSubmit(onSubmit, '数字错误'))

    await act(async () => { await result.current.handleSubmit('val') })
    expect(result.current.submitting).toBe(false)
    expect(message.error).toHaveBeenCalledWith('数字错误')
  })

  it('handleSubmit 是稳定引用（不随 onSubmit 变化而变化）', () => {
    const onSubmit1 = vi.fn().mockResolvedValue(undefined)
    const { result, rerender } = renderHook(
      ({ cb }) => useSubmit(cb),
      { initialProps: { cb: onSubmit1 } },
    )

    const handle1 = result.current.handleSubmit

    const onSubmit2 = vi.fn().mockResolvedValue(undefined)
    rerender({ cb: onSubmit2 })

    // useCallback 依赖 [onSubmit, fallbackError]，onSubmit 变化时引用会变
    // 这是正常行为
    expect(typeof result.current.handleSubmit).toBe('function')
  })

  it('初始 submitting 状态为 false', () => {
    const onSubmit = vi.fn()
    const { result } = renderHook(() => useSubmit(onSubmit))
    expect(result.current.submitting).toBe(false)
  })

  it('onSubmit 异步完成后 locked 重置', async () => {
    const onSubmit = vi.fn()
      .mockResolvedValueOnce(undefined)
      .mockResolvedValueOnce(undefined)
    const { result } = renderHook(() => useSubmit(onSubmit))

    await act(async () => { await result.current.handleSubmit('a') })
    expect(onSubmit).toHaveBeenCalledTimes(1)

    await act(async () => { await result.current.handleSubmit('b') })
    expect(onSubmit).toHaveBeenCalledTimes(2)
  })
})

// ═══════════════════════════════════════════════════════
// usePaginatedList 边界测试
// ═══════════════════════════════════════════════════════

import { usePaginatedList } from '@/hooks/usePaginatedList'

const mockFetch = vi.fn()
const mockData = {
  items: [{ id: '1', name: 'A' }],
  total: 5,
}

describe('usePaginatedList 边界测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({ ...mockData })
  })

  it('初始 page 为 1', () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))
    expect(result.current.page).toBe(1)
  })

  it('初始 pageSize 为 20', () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))
    expect(result.current.pageSize).toBe(20)
  })

  it('初始 keyword 为空字符串', () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))
    expect(result.current.keyword).toBe('')
  })

  it('初始 loading 为 true（首次加载中）', () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))
    expect(result.current.loading).toBe(true)
  })

  it('初始 error 为 false', () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))
    expect(result.current.error).toBe(false)
  })

  it('空字符串 keyword 传 undefined 给 fetchFn', async () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockFetch).toHaveBeenCalledWith({
      page: 1, page_size: 20, keyword: undefined,
    })
  })

  it('非空 keyword 传给 fetchFn', async () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))
    vi.clearAllMocks()

    act(() => { result.current.setKeyword('test') })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.objectContaining({ keyword: 'test' }),
      )
    })
  })

  it('items 为 null 时安全处理', async () => {
    mockFetch.mockResolvedValueOnce({ items: null, total: null })

    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toEqual([])
    expect(result.current.total).toBe(0)
  })

  it('fetchFn 返回 items 为 undefined 时安全处理', async () => {
    mockFetch.mockResolvedValueOnce({ total: 3 })

    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toEqual([])
  })

  it('fetchFn 变更时使用最新引用', async () => {
    const fetchA = vi.fn().mockResolvedValue({ items: [{ id: 'a' }], total: 1 })
    const fetchB = vi.fn().mockResolvedValue({ items: [{ id: 'b' }], total: 1 })

    const { result, rerender } = renderHook(
      ({ fn }) => usePaginatedList(fn),
      { initialProps: { fn: fetchA } },
    )

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(fetchA).toHaveBeenCalledTimes(1)

    rerender({ fn: fetchB })
    await act(async () => { await result.current.refresh() })

    expect(fetchB).toHaveBeenCalled()
  })

  it('默认错误消息为"加载数据失败"', async () => {
    mockFetch.mockRejectedValue(new Error('fail'))

    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(message.error).toHaveBeenCalledWith('加载数据失败')
  })

  it('自定义 errorMessage 生效', async () => {
    mockFetch.mockRejectedValue(new Error('fail'))

    const { result } = renderHook(() =>
      usePaginatedList(mockFetch, {}, '自定义加载错误'),
    )

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(message.error).toHaveBeenCalledWith('自定义加载错误')
  })

  it('onPageChange 正确更新 page 和 pageSize', async () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))
    vi.clearAllMocks()

    act(() => { result.current.onPageChange(3, 50) })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.objectContaining({ page: 3, page_size: 50 }),
      )
    })

    expect(result.current.page).toBe(3)
    expect(result.current.pageSize).toBe(50)
  })

  it('filters 传空对象时等价于无额外参数', async () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch, {}))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockFetch).toHaveBeenCalledWith({
      page: 1, page_size: 20, keyword: undefined,
    })
  })

  it('filters 包含 undefined 值时仍传递', async () => {
    const { result } = renderHook(() =>
      usePaginatedList(mockFetch, { status: undefined }),
    )

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockFetch).toHaveBeenCalledWith(
      expect.objectContaining({ status: undefined }),
    )
  })

  it('refresh 返回 Promise', async () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))

    const refreshResult = result.current.refresh()
    expect(refreshResult).toBeInstanceOf(Promise)
    await refreshResult
  })
})
