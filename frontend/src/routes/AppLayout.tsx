import { useState, useEffect } from 'react'
import { Layout, Menu, Space, Typography, Grid, Button, Result } from 'antd'
import {
  DashboardOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
  ShopOutlined,
  FileTextOutlined,
  LogoutOutlined,
  UserOutlined,
  BarChartOutlined,
  WalletOutlined,
  UserSwitchOutlined,
  InboxOutlined,
  SafetyOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { authApi, type CurrentUser } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const { Text } = Typography
const { useBreakpoint } = Grid

const { Header, Sider, Content } = Layout

// 路径 -> 所需权限映射（null 表示所有用户可访问）
const PATH_PERMISSIONS: Record<string, string | null> = {
  '/': null,
  '/products': 'product:list',
  '/products/new': 'product:create',
  '/inventory': 'inventory:list',
  '/customers': 'customer:list',
  '/customers/new': 'customer:create',
  '/orders': 'order:list',
  '/orders/new': 'order:create',
  '/payments': 'payment:list',
  '/audit-logs': 'audit:view',
  '/reports': 'report:sales',
  '/users': '__superuser__',
  '/roles': '__superuser__',
}

// 匹配动态路径
function getPathPermission(pathname: string): string | null {
  if (PATH_PERMISSIONS[pathname] !== undefined) return PATH_PERMISSIONS[pathname]
  const segments = pathname.split('/').filter(Boolean)
  for (const [pattern, perm] of Object.entries(PATH_PERMISSIONS)) {
    const pSegs = pattern.split('/').filter(Boolean)
    if (pSegs.length !== segments.length) continue
    if (pSegs.every((seg, i) => seg.startsWith(':') || seg === segments[i])) return perm
  }
  return null
}

// 菜单项定义，permission 为 null 表示所有登录用户可见
const allMenuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '首页看板', permission: null as string | null },
  { key: '/products', icon: <ShopOutlined />, label: '商品管理', permission: 'product:list' },
  { key: '/inventory', icon: <InboxOutlined />, label: '库存流水', permission: 'inventory:list' },
  { key: '/customers', icon: <TeamOutlined />, label: '客户管理', permission: 'customer:list' },
  { key: '/orders', icon: <ShoppingCartOutlined />, label: '销售订单', permission: 'order:list' },
  { key: '/payments', icon: <WalletOutlined />, label: '收款记录', permission: 'payment:list' },
  { key: '/reports', icon: <BarChartOutlined />, label: '报表中心', permission: 'report:sales' },
  { key: '/audit-logs', icon: <FileTextOutlined />, label: '操作日志', permission: 'audit:view' },
  { key: '/users', icon: <UserSwitchOutlined />, label: '用户管理', permission: '__superuser__' },
  { key: '/roles', icon: <SafetyOutlined />, label: '角色权限', permission: '__superuser__' },
]

function PermissionGuard({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const hasPermission = useAuthStore(s => s.hasPermission)
  const user = useAuthStore(s => s.user)
  const perm = getPathPermission(location.pathname)
  if (perm === null) return <>{children}</>
  if (perm === '__superuser__' && user?.is_superuser !== true) {
    return <Result status="403" title="无访问权限" subTitle="您没有权限访问此页面" extra={<Button type="primary" onClick={() => navigate('/')}>返回首页</Button>} />
  }
  if (perm !== '__superuser__' && !hasPermission(perm)) {
    return <Result status="403" title="无访问权限" subTitle="您没有权限访问此页面" extra={<Button type="primary" onClick={() => navigate('/')}>返回首页</Button>} />
  }
  return <>{children}</>
}

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const screens = useBreakpoint()
  const isMobile = screens.md === false // 明确为 false 才算移动端（undefined 不算）
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [collapsed, setCollapsed] = useState(isMobile)

  // 小屏幕自动折叠侧边栏
  useEffect(() => {
    if (isMobile) setCollapsed(true)
  }, [isMobile])

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
    if (isMobile) setCollapsed(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/login')
  }

  // 匹配子路径高亮：/orders/123 → /orders
  const selectedKey = '/' + location.pathname.split('/').filter(Boolean)[0]

  const displayName = user?.display_name || user?.username || ''
  const roleLabel = user?.roles?.[0]?.display_name || ''
  const hasPermission = useAuthStore(s => s.hasPermission)

  // 根据权限过滤菜单（hasPermission 已处理 superuser 逻辑）
  const menuItems = allMenuItems.filter((item) => {
    if (!item.permission) return true
    return hasPermission(item.permission)
  })

  useEffect(() => {
    authApi.getMe().then((res) => {
      if (res.data?.success) setUser(res.data.data)
    }).catch(() => {})
  }, [])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        theme="light"
        width={200}
        collapsedWidth={isMobile ? 0 : 80}
        collapsed={collapsed}
        trigger={null}
        style={isMobile ? { position: 'fixed', zIndex: 100, height: '100vh' } : undefined}
      >
        <div style={{ height: 48, margin: 16, textAlign: 'center', fontSize: 18, fontWeight: 600 }}>
          销售管理系统
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 16 }}>
          {isMobile && (
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ fontSize: 16, marginRight: 'auto' }}
            />
          )}
          <div style={{ flex: 1 }} />
          {user && (
            <Space>
              <UserOutlined />
              <Text strong>{displayName}</Text>
              {roleLabel && <Text type="secondary" style={{ fontSize: 12 }}>{roleLabel}</Text>}
            </Space>
          )}
          <LogoutOutlined style={{ fontSize: 18, cursor: 'pointer' }} onClick={handleLogout} title="退出登录" />
        </Header>
        <Content style={{ margin: isMobile ? 16 : 24, padding: isMobile ? 16 : 24, background: '#fff', borderRadius: 8 }}>
          <PermissionGuard>
            <Outlet />
          </PermissionGuard>
        </Content>
      </Layout>
    </Layout>
  )
}
