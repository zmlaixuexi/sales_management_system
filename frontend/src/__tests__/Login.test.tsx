/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _loginFn = vi.fn()
const _messageError = vi.fn()

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: any) => selector({ login: (...args: any[]) => _loginFn(...args) }),
}))

vi.mock('antd', () => ({
  Card: ({ children }: any) => <div data-testid="card">{children}</div>,
  Form: Object.assign(
    ({ children, onFinish }: any) => {
      // 暴露 onFinish 以便测试中手动调用
      ;(globalThis as any).__loginOnFinish = onFinish
      return (
        <form data-testid="login-form" onSubmit={(e) => { e.preventDefault() }}>
          {children}
        </form>
      )
    },
    {
      Item: ({ children, name }: any) => (
        <div data-testid="form-item" data-name={name}>{children}</div>
      ),
    },
  ),
  Input: Object.assign(
    ({ placeholder }: any) => <input data-testid="input" placeholder={placeholder} />,
    { Password: ({ placeholder }: any) => <input data-testid="password-input" placeholder={placeholder} /> },
  ),
  Button: ({ children, loading, htmlType }: any) => (
    <button data-testid="submit-btn" disabled={loading} type={htmlType}>
      {loading ? '登录中...' : children}
    </button>
  ),
  Typography: { Title: ({ children }: any) => <h3>{children}</h3> },
  message: { error: (...args: any[]) => _messageError(...args), success: vi.fn() },
}))

vi.mock('@ant-design/icons', () => ({
  UserOutlined: () => <span>👤</span>,
  LockOutlined: () => <span>🔒</span>,
}))

import Login from '@/pages/Login'

function renderLogin(redirect?: string) {
  const entry = redirect ? `/login?redirect=${redirect}` : '/login'
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<div>首页</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染页面标题', () => {
    renderLogin()
    expect(screen.getByText('销售管理系统')).toBeInTheDocument()
  })

  it('渲染用户名和密码输入框', () => {
    renderLogin()
    expect(screen.getByTestId('input')).toBeInTheDocument()
    expect(screen.getByTestId('password-input')).toBeInTheDocument()
  })

  it('渲染登录按钮', () => {
    renderLogin()
    expect(screen.getByText('登录')).toBeInTheDocument()
  })

  it('提交表单调用 login', async () => {
    _loginFn.mockResolvedValue(undefined)
    renderLogin()
    // 通过 Form mock 暴露的 onFinish 手动触发
    const onFinish = (globalThis as any).__loginOnFinish
    fireEvent.submit(screen.getByTestId('login-form'))
    // Ant Design Form 内部管理 onFinish，mock 中直接调用
    onFinish?.({ username: 'admin', password: 'pass' })
    await waitFor(() => {
      expect(_loginFn).toHaveBeenCalledWith('admin', 'pass')
    })
  })

  it('登录失败显示错误提示', async () => {
    _loginFn.mockRejectedValue(new Error('invalid'))
    renderLogin()
    const onFinish = (globalThis as any).__loginOnFinish
    onFinish?.({ username: 'admin', password: 'wrong' })
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('用户名或密码错误')
    })
  })

  it('登录成功后跳转到首页', async () => {
    _loginFn.mockResolvedValue(undefined)
    renderLogin()
    const onFinish = (globalThis as any).__loginOnFinish
    onFinish?.({ username: 'admin', password: 'pass' })
    await waitFor(() => {
      expect(_loginFn).toHaveBeenCalledWith('admin', 'pass')
    })
  })

  it('登录成功后跳转到 redirect 参数指定页', async () => {
    _loginFn.mockResolvedValue(undefined)
    renderLogin('/products')
    const onFinish = (globalThis as any).__loginOnFinish
    onFinish?.({ username: 'admin', password: 'pass' })
    await waitFor(() => {
      expect(_loginFn).toHaveBeenCalledWith('admin', 'pass')
    })
  })
})
