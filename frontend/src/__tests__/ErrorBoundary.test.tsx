import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, useNavigate, Routes, Route } from 'react-router-dom'
import ErrorBoundary from '@/components/ErrorBoundary'

// 模拟 antd 组件以避免 jsdom 中复杂的样式计算
vi.mock('antd', () => ({
  Button: ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
    <button role="button" onClick={onClick}>{children}</button>
  ),
  Result: ({ title, subTitle, extra }: { title: string; subTitle: string; extra?: React.ReactNode[] }) => (
    <div data-testid="error-result">
      <h1>{title}</h1>
      <p>{subTitle}</p>
      <div>{extra}</div>
    </div>
  ),
}))

function ThrowError({ error }: { error: Error }) {
  throw error
}

function NavButton({ to }: { to: string }) {
  const nav = useNavigate()
  return <button data-testid="nav-btn" onClick={() => nav(to)}>跳转</button>
}

describe('ErrorBoundary', () => {
  const originalError = console.error
  beforeEach(() => {
    console.error = vi.fn()
  })
  afterEach(() => {
    console.error = originalError
  })

  it('正常渲染子组件', () => {
    render(
      <MemoryRouter>
        <ErrorBoundary>
          <div>正常内容</div>
        </ErrorBoundary>
      </MemoryRouter>,
    )
    expect(screen.getByText('正常内容')).toBeInTheDocument()
  })

  it('捕获错误后显示错误页面', () => {
    render(
      <MemoryRouter>
        <ErrorBoundary>
          <ThrowError error={new Error('测试错误')} />
        </ErrorBoundary>
      </MemoryRouter>,
    )
    expect(screen.getByTestId('error-result')).toBeInTheDocument()
    expect(screen.getByText('页面出错了')).toBeInTheDocument()
    expect(screen.getByText('测试错误')).toBeInTheDocument()
  })

  it('重试按钮存在并恢复子组件渲染', () => {
    let shouldThrow = true
    function ConditionalThrow() {
      if (shouldThrow) throw new Error('条件错误')
      return <div>恢复内容</div>
    }

    render(
      <MemoryRouter>
        <ErrorBoundary>
          <ConditionalThrow />
        </ErrorBoundary>
      </MemoryRouter>,
    )

    expect(screen.getByTestId('error-result')).toBeInTheDocument()
    expect(screen.getByText('重试')).toBeInTheDocument()
    expect(screen.getByText('返回首页')).toBeInTheDocument()

    shouldThrow = false
    fireEvent.click(screen.getByText('重试'))

    expect(screen.getByText('恢复内容')).toBeInTheDocument()
    expect(screen.queryByTestId('error-result')).not.toBeInTheDocument()
  })

  it('路由变化时自动重置错误状态', () => {
    let shouldThrow = true
    function MaybeThrow() {
      if (shouldThrow) throw new Error('路由重置错误')
      return <div>路由恢复内容</div>
    }

    render(
      <MemoryRouter initialEntries={['/page-a']}>
        {/* 导航按钮放在 ErrorBoundary 外面 */}
        <NavButton to="/page-b" />
        <Routes>
          <Route path="*" element={
            <ErrorBoundary>
              <MaybeThrow />
            </ErrorBoundary>
          } />
        </Routes>
      </MemoryRouter>,
    )

    // 初始渲染触发错误
    expect(screen.getByTestId('error-result')).toBeInTheDocument()

    // 修复错误并导航到新路由
    shouldThrow = false
    fireEvent.click(screen.getByTestId('nav-btn'))

    // 路由变化 → resetKey 更新 → 错误重置 → 子组件重新渲染
    expect(screen.getByText('路由恢复内容')).toBeInTheDocument()
    expect(screen.queryByTestId('error-result')).not.toBeInTheDocument()
  })

  it('返回首页按钮跳转到根路径', () => {
    render(
      <MemoryRouter>
        <ErrorBoundary>
          <ThrowError error={new Error('首页跳转测试')} />
        </ErrorBoundary>
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByText('返回首页'))
    expect(window.location.href).toContain('/')
  })

  it('错误无 message 时显示默认提示', () => {
    // 创建一个没有 message 的错误对象
    const errorWithoutMessage = new Error()
    errorWithoutMessage.message = ''

    render(
      <MemoryRouter>
        <ErrorBoundary>
          <ThrowError error={errorWithoutMessage} />
        </ErrorBoundary>
      </MemoryRouter>,
    )

    expect(screen.getByTestId('error-result')).toBeInTheDocument()
    expect(screen.getByText('发生了未知错误')).toBeInTheDocument()
  })
})
