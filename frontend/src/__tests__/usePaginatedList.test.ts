import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'

vi.mock('antd', () => ({
  message: { error: vi.fn() },
}))

import { message } from 'antd'
import { usePaginatedList } from '../hooks/usePaginatedList'

const mockFetch = vi.fn()

const mockData = {
  items: [{ id: '1', name: '测试' }, { id: '2', name: '测试2' }],
  total: 10,
}

describe('usePaginatedList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({ ...mockData })
  })

  it('初始加载获取第一页数据', async () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockFetch).toHaveBeenCalledWith({
      page: 1, page_size: 20, keyword: undefined,
    })
    expect(result.current.data).toEqual(mockData.items)
    expect(result.current.total).toBe(10)
  })

  it('加载失败时显示错误消息', async () => {
    mockFetch.mockRejectedValueOnce(new Error('网络错误'))

    const { result } = renderHook(() =>
      usePaginatedList(mockFetch, {}, '加载失败'),
    )

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(message.error).toHaveBeenCalledWith('加载失败')
    expect(result.current.data).toEqual([])
  })

  it('传递额外筛选参数', async () => {
    const { result } = renderHook(() =>
      usePaginatedList(mockFetch, { status: 'active' }),
    )

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(mockFetch).toHaveBeenCalledWith({
      page: 1, page_size: 20, keyword: undefined, status: 'active',
    })
  })

  it('setKeyword 同时重置页码为 1', async () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => { result.current.onPageChange(3, 20) })
    await waitFor(() => expect(result.current.page).toBe(3))

    act(() => { result.current.setKeyword('搜索词') })

    expect(result.current.page).toBe(1)
    expect(result.current.keyword).toBe('搜索词')
  })

  it('onPageChange 更新分页参数', async () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))
    vi.clearAllMocks()

    act(() => { result.current.onPageChange(2, 50) })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2, page_size: 50 }),
      )
    })
  })

  it('refresh 手动重新加载', async () => {
    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))
    vi.clearAllMocks()

    await act(async () => { await result.current.refresh() })

    expect(mockFetch).toHaveBeenCalledTimes(1)
  })

  it('筛选参数变化时自动重新加载', async () => {
    const { result } = renderHook(
      ({ status }) => usePaginatedList(mockFetch, { status }),
      { initialProps: { status: undefined } },
    )

    await waitFor(() => expect(result.current.loading).toBe(false))
    vi.clearAllMocks()

    renderHook(
      ({ status }) => usePaginatedList(mockFetch, { status }),
      { initialProps: { status: 'active' } },
    )

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'active' }),
      )
    })
  })

  it('结果为空时安全处理', async () => {
    mockFetch.mockResolvedValueOnce({})

    const { result } = renderHook(() => usePaginatedList(mockFetch))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toEqual([])
    expect(result.current.total).toBe(0)
  })

  it('拦截器已展示 toast 时不重复提示', async () => {
    const error = Object.assign(new Error('已提示'), { _toastDisplayed: true })
    mockFetch.mockRejectedValueOnce(error)

    const { result } = renderHook(() =>
      usePaginatedList(mockFetch, {}, '兜底错误'),
    )

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(message.error).not.toHaveBeenCalled()
    expect(result.current.data).toEqual([])
  })
})
