import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
  ShopOutlined,
  FileTextOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '首页看板' },
  { key: '/products', icon: <ShopOutlined />, label: '商品管理' },
  { key: '/customers', icon: <TeamOutlined />, label: '客户管理' },
  { key: '/orders', icon: <ShoppingCartOutlined />, label: '销售订单' },
  { key: '/audit-logs', icon: <FileTextOutlined />, label: '操作日志' },
]

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()

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
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          <LogoutOutlined style={{ fontSize: 18, cursor: 'pointer' }} onClick={handleLogout} />
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
