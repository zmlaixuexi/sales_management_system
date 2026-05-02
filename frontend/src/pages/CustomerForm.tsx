import { useState, useEffect } from 'react'
import { Form, Input, Button, Card, Space, Select, message } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchCustomer, createCustomer, updateCustomer } from '@/api/customers'
import { useSubmit } from '@/hooks/useSubmit'
import { getApiErrorMessage } from '@/utils'

export default function CustomerForm() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id)
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      fetchCustomer(id)
        .then((res) => {
          if (res.success) {
            form.setFieldsValue({
              name: res.data.name,
              contact_name: res.data.contact_name,
              phone: res.data.phone,
              email: res.data.email,
              source: res.data.source,
              level: res.data.level,
              follow_status: res.data.follow_status,
              remark: res.data.remark,
            })
          }
        })
        .catch((e: unknown) => {
          if (!(e as any)?._toastDisplayed) message.error(getApiErrorMessage(e, '加载客户信息失败'))
          navigate('/customers', { replace: true })
        })
        .finally(() => setLoading(false))
    }
  }, [id, form])

  const { submitting, handleSubmit } = useSubmit(async (values: Record<string, unknown>) => {
    if (isEdit && id) {
      const res = await updateCustomer(id, values)
      if (res.success) {
        message.success('更新成功')
        navigate('/customers')
      }
    } else {
      const res = await createCustomer(values as unknown as Parameters<typeof createCustomer>[0])
      if (res.success) {
        message.success('创建成功')
        navigate('/customers')
      }
    }
  })

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/customers')}>返回列表</Button>
      </div>
      <Card title={isEdit ? '编辑客户' : '新增客户'} loading={loading || submitting}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ level: 'normal', follow_status: 'new', source: 'other' }}
          style={{ maxWidth: 600 }}
        >
          <Form.Item label="客户名称" name="name" rules={[{ required: true, message: '请输入客户名称' }]}>
            <Input placeholder="请输入客户名称" maxLength={100} />
          </Form.Item>

          <Space size="large">
            <Form.Item label="联系人" name="contact_name">
              <Input placeholder="联系人姓名" maxLength={100} style={{ width: 250 }} />
            </Form.Item>
            <Form.Item label="电话" name="phone">
              <Input placeholder="联系电话" maxLength={30} style={{ width: 250 }} />
            </Form.Item>
          </Space>

          <Form.Item label="邮箱" name="email">
            <Input placeholder="邮箱地址" maxLength={100} />
          </Form.Item>

          <Space size="large">
            <Form.Item label="来源" name="source">
              <Select
                style={{ width: 200 }}
                options={[
                  { label: '转介绍', value: 'referral' },
                  { label: '线上', value: 'online' },
                  { label: '线下', value: 'offline' },
                  { label: '广告', value: 'ad' },
                  { label: '其他', value: 'other' },
                ]}
              />
            </Form.Item>
            <Form.Item label="等级" name="level">
              <Select
                style={{ width: 200 }}
                options={[
                  { label: 'VIP', value: 'vip' },
                  { label: '重要', value: 'important' },
                  { label: '普通', value: 'normal' },
                  { label: '潜在', value: 'potential' },
                ]}
              />
            </Form.Item>
          </Space>

          <Form.Item label="跟进状态" name="follow_status">
            <Select
              style={{ width: 200 }}
              options={[
                { label: '新客户', value: 'new' },
                { label: '跟进中', value: 'following' },
                { label: '已成交', value: 'closed' },
                { label: '已流失', value: 'lost' },
              ]}
            />
          </Form.Item>

          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={3} maxLength={500} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading || submitting}>
                {isEdit ? '保存修改' : '创建客户'}
              </Button>
              <Button onClick={() => navigate('/customers')}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
