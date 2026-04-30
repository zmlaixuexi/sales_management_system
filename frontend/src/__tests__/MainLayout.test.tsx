/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import MainLayout from '@/components/MainLayout'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(),
}))

// Mock 必须自包含（vi.mock 会提升到文件顶部）
vi.mock('antd', () => {
  function Layout({ children }: any) { return <div data-testid="layout">{children}</div> }
  function Sider({ children, collapsed, onCollapse }: any) {
    return (
      <div data-testid="sider" data-collapsed={String(collapsed)}>
        <button data-testid="collapse-btn" onClick={() => onCollapse(!collapsed)}>收起</button>
        {children}
      </div>
    )
  }
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
    Avatar: () => <div data-testid="avatar" />,
    Dropdown: ({ menu, children }: any) => (
      <div data-testid="dropdown">
        {children}
        {menu?.items?.map((item: any) => (
          <button key={item.key} data-testid={`dropdown-${item.key}`} onClick={item.onClick}>
            {item.label}
          </button>
        ))}
      </div>
    ),
    Typography: { Text: ({ children }: any) => <span>{children}</span> },
  }
})

vi.mock('@ant-design/icons', () => ({
  DashboardOutlined: () => null,
  ShoppingOutlined: () => null,
  TeamOutlined: () => null,
  FileTextOutlined: () => null,
  UserOutlined: () => null,
  LogoutOutlined: () => null,
  AuditOutlined: () => null,
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

describe('MainLayout', () => {
  const mockLogout = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    ;(useAuthStore as any).mockReturnValue({
      user: { display_name: '测试用户', username: 'tester' },
      logout: mockLogout,
    })
  })

  it('渲染侧边栏和菜单项', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <MainLayout />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('sider')).toBeInTheDocument()
    expect(screen.getByTestId('menu-/dashboard')).toHaveTextContent('首页看板')
    expect(screen.getByTestId('menu-/products')).toHaveTextContent('商品管理')
  })

  it('点击菜单项触发导航', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <MainLayout />
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByTestId('menu-/products'))
    expect(mockNavigate).toHaveBeenCalledWith('/products')
  })

  it('显示用户名并支持退出登录', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <MainLayout />
      </MemoryRouter>,
    )
    expect(screen.getByText('测试用户')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('dropdown-logout'))
    expect(mockLogout).toHaveBeenCalled()
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
  })

  it('折叠侧边栏', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <MainLayout />
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByTestId('collapse-btn'))
    expect(screen.getByTestId('sider').dataset.collapsed).toBe('true')
  })

  it('用户无 display_name 时显示 username', () => {
    ;(useAuthStore as any).mockReturnValue({
      user: { username: 'fallback' },
      logout: mockLogout,
    })
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <MainLayout />
      </MemoryRouter>,
    )
    expect(screen.getByText('fallback')).toBeInTheDocument()
  })

  it('用户信息均无时显示默认文字', () => {
    ;(useAuthStore as any).mockReturnValue({
      user: {},
      logout: mockLogout,
    })
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <MainLayout />
      </MemoryRouter>,
    )
    expect(screen.getByText('用户')).toBeInTheDocument()
  })
})
