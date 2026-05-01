import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'

vi.mock('antd', () => ({
  message: { error: vi.fn() },
}))

import { message } from 'antd'
import { useSubmit } from '../hooks/useSubmit'

describe('useSubmit', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('成功时调用 onSubmit', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => useSubmit(onSubmit))

    await act(async () => { await result.current.handleSubmit('values') })

    expect(onSubmit).toHaveBeenCalledWith('values')
    expect(result.current.submitting).toBe(false)
  })

  it('提交期间 submitting 为 true', async () => {
    let resolve: () => void
    const onSubmit = vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r }))
    const { result } = renderHook(() => useSubmit(onSubmit))

    act(() => { result.current.handleSubmit('values') })

    await waitFor(() => expect(result.current.submitting).toBe(true))

    await act(async () => { resolve!() })

    expect(result.current.submitting).toBe(false)
  })

  it('失败时显示错误消息', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('fail'))
    const { result } = renderHook(() => useSubmit(onSubmit, '自定义错误'))

    await act(async () => { await result.current.handleSubmit('values') })

    expect(message.error).toHaveBeenCalledWith('自定义错误')
    expect(result.current.submitting).toBe(false)
  })

  it('Ant Design 表单校验错误不弹提示', async () => {
    const formError = { errorFields: [{ name: ['name'], errors: ['必填'] }] }
    const onSubmit = vi.fn().mockRejectedValue(formError)
    const { result } = renderHook(() => useSubmit(onSubmit))

    await act(async () => { await result.current.handleSubmit('values') })

    expect(message.error).not.toHaveBeenCalled()
  })

  it('防重复提交：并发调用只执行一次', async () => {
    let resolve: () => void
    const onSubmit = vi.fn().mockReturnValue(new Promise<void>((r) => { resolve = r }))
    const { result } = renderHook(() => useSubmit(onSubmit))

    act(() => { result.current.handleSubmit('values') })
    act(() => { result.current.handleSubmit('values') })

    await act(async () => { resolve!() })

    expect(onSubmit).toHaveBeenCalledTimes(1)
  })

  it('拦截器已展示 toast 时不重复提示', async () => {
    const error = Object.assign(new Error('已提示'), { _toastDisplayed: true })
    const onSubmit = vi.fn().mockRejectedValue(error)
    const { result } = renderHook(() => useSubmit(onSubmit, '兜底'))

    await act(async () => { await result.current.handleSubmit('values') })

    expect(message.error).not.toHaveBeenCalled()
  })
})
