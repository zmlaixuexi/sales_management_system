import { useState } from 'react'
import { Card, Form, Input, Button, message, Typography } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { getApiErrorMessage } from '@/utils'
import useDocumentTitle from '@/hooks/useDocumentTitle'

const { Title } = Typography

export default function Login() {
  useDocumentTitle('登录')
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const login = useAuthStore((s) => s.login)
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      await login(values.username, values.password)
      const redirect = searchParams.get('redirect') || '/'
      navigate(redirect, { replace: true })
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, '用户名或密码错误'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <Card style={{
        width: '90%',
        maxWidth: 420,
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
        borderRadius: 12,
      }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 24, color: '#1677ff' }}>
          销售管理系统
        </Title>
        <Form onFinish={onFinish} autoComplete="off" size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
