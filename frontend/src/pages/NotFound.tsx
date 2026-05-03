import { Button, Result } from 'antd'
import { useNavigate } from 'react-router-dom'
import useDocumentTitle from '@/hooks/useDocumentTitle'

function NotFound() {
  useDocumentTitle('页面不存在')
  const navigate = useNavigate()
  return (
    <Result
      status="404"
      title="404"
      subTitle="页面不存在"
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          返回首页
        </Button>
      }
    />
  )
}

export default NotFound
