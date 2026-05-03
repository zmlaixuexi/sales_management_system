import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import useDocumentTitle from '@/hooks/useDocumentTitle'

describe('useDocumentTitle', () => {
  const originalTitle = document.title

  beforeEach(() => {
    document.title = originalTitle
  })

  it('设置页面标题为 "标题 - 销售管理系统"', () => {
    renderHook(() => useDocumentTitle('商品列表'))
    expect(document.title).toBe('商品列表 - 销售管理系统')
  })

  it('不传标题时使用默认标题', () => {
    renderHook(() => useDocumentTitle())
    expect(document.title).toBe('销售管理系统')
  })

  it('组件卸载时恢复原标题', () => {
    document.title = '原标题'
    const { unmount } = renderHook(() => useDocumentTitle('测试页'))
    expect(document.title).toBe('测试页 - 销售管理系统')
    unmount()
    expect(document.title).toBe('原标题')
  })

  it('标题变化时更新 document.title', () => {
    const { rerender } = renderHook(
      ({ title }: { title: string }) => useDocumentTitle(title),
      { initialProps: { title: '页面A' } },
    )
    expect(document.title).toBe('页面A - 销售管理系统')
    rerender({ title: '页面B' })
    expect(document.title).toBe('页面B - 销售管理系统')
  })
})
