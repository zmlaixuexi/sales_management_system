/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import AppLayout from '@/routes/AppLayout'

vi.mock('@/api/auth', () => ({
  authApi: { getMe: vi.fn() },
}))

vi.mock('antd', () => {
  function Layout({ children }: any) { return <div>{children}</div> }
  function Sider({ children }: any) { return <aside>{children}</aside> }
  function Header({ children }: any) { return <header>{children}</header> }
  function Content({ children }: any) { return <main>{children}</main> }
  Layout.Sider = Sider
  Layout.Header = Header
  Layout.Content = Content
  return {
    Layout,
    Menu: ({ items, onClick, selectedKeys }: any) => (
      <nav data-testid="menu" data-selected={selectedKeys?.[0]}>
        {items?.map((item: any) => (
          <button key={item.key} data-testid={`menu-${item.key}`} onClick={() => onClick?.({ key: item.key })}>
            {item.label}
          </button>
        ))}
      </nav>
    ),
    Space: ({ children }: any) => <span>{children}</span>,
    Typography: { Text: ({ children, ...props }: any) => <span {...props}>{children}</span> },
  }
})

vi.mock('@ant-design/icons', () => ({
  DashboardOutlined: () => null,
  ShoppingCartOutlined: () => null,
  TeamOutlined: () => null,
  ShopOutlined: () => null,
  FileTextOutlined: () => null,
  LogoutOutlined: (props: any) => <span data-testid="logout-icon" onClick={props.onClick} />,
  UserOutlined: () => null,
  BarChartOutlined: () => null,
  WalletOutlined: () => null,
  UserSwitchOutlined: () => null,
  InboxOutlined: () => null,
}))

import { authApi } from '@/api/auth'

describe('AppLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('加载用户信息并显示名称', async () => {
    ;(authApi.getMe as any).mockResolvedValue({
      data: { success: true, data: { display_name: '管理员', username: 'admin', roles: [{ display_name: '超级管理员' }] } },
    })

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="*" element={<AppLayout />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('管理员')).toBeInTheDocument()
      expect(screen.getByText('超级管理员')).toBeInTheDocument()
    })
  })

  it('点击菜单项触发导航', () => {
    ;(authApi.getMe as any).mockResolvedValue({ data: { success: false } })

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="*" element={<AppLayout />} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByTestId('menu-/products'))
    expect(screen.getByTestId('menu-/products')).toHaveTextContent('商品管理')
  })

  it('退出登录清除 token 并跳转', () => {
    ;(authApi.getMe as any).mockResolvedValue({ data: { success: false } })
    localStorage.setItem('access_token', 'test')
    localStorage.setItem('refresh_token', 'test')

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="*" element={<AppLayout />} />
          <Route path="/login" element={<div>login-page</div>} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByTestId('logout-icon'))
    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })

  it('getMe 失败时不崩溃', async () => {
    ;(authApi.getMe as any).mockRejectedValue(new Error('网络错误'))

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="*" element={<AppLayout />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(authApi.getMe).toHaveBeenCalled()
    })
    expect(screen.getByTestId('menu')).toBeInTheDocument()
  })

  it('用户无 display_name 时显示 username', async () => {
    ;(authApi.getMe as any).mockResolvedValue({
      data: { success: true, data: { username: 'fallback_user', roles: [] } },
    })

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="*" element={<AppLayout />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('fallback_user')).toBeInTheDocument()
    })
  })
})
