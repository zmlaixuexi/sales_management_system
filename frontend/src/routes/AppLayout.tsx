import { useState, useEffect } from 'react'
import { Layout, Menu, Space, Typography } from 'antd'
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
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { authApi, type CurrentUser } from '@/api/auth'

const { Text } = Typography

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '首页看板' },
  { key: '/products', icon: <ShopOutlined />, label: '商品管理' },
  { key: '/inventory', icon: <InboxOutlined />, label: '库存流水' },
  { key: '/customers', icon: <TeamOutlined />, label: '客户管理' },
  { key: '/orders', icon: <ShoppingCartOutlined />, label: '销售订单' },
  { key: '/payments', icon: <WalletOutlined />, label: '收款记录' },
  { key: '/reports', icon: <BarChartOutlined />, label: '报表中心' },
  { key: '/audit-logs', icon: <FileTextOutlined />, label: '操作日志' },
  { key: '/users', icon: <UserSwitchOutlined />, label: '用户管理' },
  { key: '/roles', icon: <SafetyOutlined />, label: '角色权限' },
]

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState<CurrentUser | null>(null)

  useEffect(() => {
    authApi.getMe().then((res) => {
      if (res.data?.success) setUser(res.data.data)
    }).catch(() => {})
  }, [])

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
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

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="light" width={200}>
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
          {user && (
            <Space>
              <UserOutlined />
              <Text strong>{displayName}</Text>
              {roleLabel && <Text type="secondary" style={{ fontSize: 12 }}>{roleLabel}</Text>}
            </Space>
          )}
          <LogoutOutlined style={{ fontSize: 18, cursor: 'pointer' }} onClick={handleLogout} title="退出登录" />
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
