import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBoundary from '@/components/ErrorBoundary'

// 模拟 antd 组件以避免 jsdom 中复杂的样式计算
vi.mock('antd', () => ({
  Button: ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
    <button onClick={onClick}>{children}</button>
  ),
  Result: ({ title, subTitle }: { title: string; subTitle: string }) => (
    <div data-testid="error-result">
      <h1>{title}</h1>
      <p>{subTitle}</p>
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
      <ErrorBoundary>
        <div>正常内容</div>
      </ErrorBoundary>,
    )
    expect(screen.getByText('正常内容')).toBeInTheDocument()
  })

  it('捕获错误后显示错误页面', () => {
    render(
      <ErrorBoundary>
        <ThrowError error={new Error('测试错误')} />
      </ErrorBoundary>,
    )
    expect(screen.getByTestId('error-result')).toBeInTheDocument()
    expect(screen.getByText('页面出错了')).toBeInTheDocument()
    expect(screen.getByText('测试错误')).toBeInTheDocument()
  })
})
