/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const { mockLogin, mockNavigate, antdMocks } = vi.hoisted(() => {
  const ml = { fn: vi.fn() }
  const mn = { fn: vi.fn() }
  const MockCard = ({ children }: any) => <div data-testid="card">{children}</div>
  const MockFormItem = ({ children }: any) => <div>{children}</div>
  const MockForm = Object.assign(
    ({ children, onFinish }: any) => (
      <form
        data-testid="login-form"
        onSubmit={(e) => {
          e.preventDefault()
          onFinish?.({ username: 'admin', password: 'pass123' })
        }}
      >
        {children}
      </form>
    ),
    { Item: MockFormItem },
  )
  const MockInput = Object.assign(
    (props: any) => <input data-testid="username-input" {...props} />,
    { Password: (props: any) => <input data-testid="password-input" type="password" {...props} /> },
  )
  const MockButton = ({ children, loading, htmlType }: any) => (
    <button data-testid="login-button" type={htmlType} disabled={loading}>
      {loading ? '加载中...' : children}
    </button>
  )
  const MockTitle = ({ children }: any) => <h1>{children}</h1>
  return {
    mockLogin: ml.fn,
    mockNavigate: mn.fn,
    antdMocks: { Card: MockCard, Form: MockForm, Input: MockInput, Button: MockButton, Title: MockTitle },
  }
})

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: any) =>
    selector({ login: mockLogin, token: null, user: null, loading: false }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('antd', () => ({
  Card: antdMocks.Card,
  Form: antdMocks.Form,
  Input: antdMocks.Input,
  Button: antdMocks.Button,
  message: { error: vi.fn(), success: vi.fn() },
  Typography: { Title: antdMocks.Title },
}))

vi.mock('@ant-design/icons', () => ({
  UserOutlined: () => null,
  LockOutlined: () => null,
}))

vi.mock('@/utils', () => ({
  getApiErrorMessage: (e: unknown, fallback: string) => {
    const err = e as { message?: string }
    return err.message || fallback
  },
}))

import Login from '@/pages/Login'

function renderLogin(initialPath = '/login') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<div data-testid="dashboard">Dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Login 页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('渲染登录表单', () => {
    renderLogin()
    expect(screen.getByTestId('login-form')).toBeInTheDocument()
    expect(screen.getByText('销售管理系统')).toBeInTheDocument()
  })

  it('登录成功后跳转首页', async () => {
    mockLogin.mockResolvedValue(undefined)
    renderLogin()

    screen.getByTestId('login-form').requestSubmit()

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('admin', 'pass123')
    })
  })

  it('登录失败显示错误消息', async () => {
    mockLogin.mockRejectedValue(new Error('用户名或密码错误'))
    renderLogin()

    screen.getByTestId('login-form').requestSubmit()

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalled()
    })
  })

  it('带 redirect 参数时登录成功跳转到指定页面', async () => {
    mockLogin.mockResolvedValue(undefined)
    renderLogin('/login?redirect=/dashboard')

    screen.getByTestId('login-form').requestSubmit()

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })
  })

  it('无 redirect 参数时跳转到 /', async () => {
    mockLogin.mockResolvedValue(undefined)
    renderLogin()

    screen.getByTestId('login-form').requestSubmit()

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
    })
  })
})
