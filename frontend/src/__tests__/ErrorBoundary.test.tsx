import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
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

describe('ErrorBoundary', () => {
  // 抑制 React 错误边界的 console.error 输出
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
})
