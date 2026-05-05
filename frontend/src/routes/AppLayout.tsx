import { useState, useEffect } from 'react'
import { Layout, Menu, Space, Typography, Grid, Button } from 'antd'
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

  // 根据权限过滤菜单
  const menuItems = allMenuItems.filter((item) => {
    if (!item.permission) return true
    if (item.permission === '__superuser__') return user?.is_superuser === true
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
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
