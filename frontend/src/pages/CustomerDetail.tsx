import { useState, useEffect, useCallback } from 'react'
import {
  Card, Descriptions, Table, Button, Space, Tag, Popconfirm, message,
} from 'antd'
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchCustomer, deleteCustomer } from '@/api/customers'
import type { Customer } from '@/api/customers'
import { fetchOrders } from '@/api/orders'
import type { Order } from '@/api/orders'
import { formatAmount, getApiErrorMessage } from '@/utils'

const sourceMap: Record<string, string> = {
  referral: '转介绍',
  online: '线上',
  offline: '线下',
  ad: '广告',
  other: '其他',
}

const levelMap: Record<string, { color: string; label: string }> = {
  vip: { color: 'gold', label: 'VIP' },
  important: { color: 'blue', label: '重要' },
  normal: { color: 'default', label: '普通' },
  potential: { color: 'green', label: '潜在' },
}

const orderStatusMap: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  confirmed: { color: 'blue', label: '已确认' },
  cancelled: { color: 'red', label: '已取消' },
  partially_paid: { color: 'orange', label: '部分收款' },
  completed: { color: 'green', label: '已完成' },
}

export default function CustomerDetail() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [ordersTotal, setOrdersTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const loadCustomer = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const res = await fetchCustomer(id)
      if (res.success) setCustomer(res.data)
    } catch {
      message.error('加载客户详情失败')
    } finally {
      setLoading(false)
    }
  }, [id])

  const loadOrders = useCallback(async () => {
    if (!id) return
    try {
      const res = await fetchOrders({ customer_id: id, page: 1, page_size: 10 })
      if (res.success) {
        setOrders(res.data.items)
        setOrdersTotal(res.data.total)
      }
    } catch { /* 订单加载失败不阻塞页面 */ }
  }, [id])

  useEffect(() => { loadCustomer() }, [loadCustomer])
  useEffect(() => { loadOrders() }, [loadOrders])

  const handleDelete = async () => {
    if (!id || deleting) return
    setDeleting(true)
    try {
      await deleteCustomer(id)
      message.success('客户已删除')
      navigate('/customers')
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, '删除失败'))
    } finally {
      setDeleting(false)
    }
  }

  if (!customer) {
    return <Card loading={loading}>加载中...</Card>
  }

  const levelInfo = customer.level ? (levelMap[customer.level] || { color: 'default', label: customer.level }) : null

  const orderColumns: ColumnsType<Order> = [
    {
      title: '订单号',
      dataIndex: 'order_no',
      width: 180,
      render: (v: string, record) => (
        <a onClick={() => navigate(`/orders/${record.id}`)}>{v}</a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const info = orderStatusMap[v] || { color: 'default', label: v }
        return <Tag color={info.color}>{info.label}</Tag>
      },
    },
    {
      title: '订单金额',
      dataIndex: 'total_amount',
      width: 120,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (v: string | null) => v ? new Date(v).toLocaleString('zh-CN') : '--',
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/customers')}>返回列表</Button>
        <Space>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/customers/${id}/edit`)}>编辑</Button>
          <Popconfirm title="确定删除该客户？删除后不可恢复。" onConfirm={handleDelete}>
            <Button danger icon={<DeleteOutlined />} loading={deleting}>删除</Button>
          </Popconfirm>
        </Space>
      </div>

      <Card title={customer.name} loading={loading}>
        <Descriptions column={3} size="small" bordered>
          <Descriptions.Item label="联系人">{customer.contact_name || '--'}</Descriptions.Item>
          <Descriptions.Item label="电话">{customer.phone || '--'}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{customer.email || '--'}</Descriptions.Item>
          <Descriptions.Item label="来源">
            {customer.source ? (sourceMap[customer.source] || customer.source) : '--'}
          </Descriptions.Item>
          <Descriptions.Item label="等级">
            {levelInfo ? <Tag color={levelInfo.color}>{levelInfo.label}</Tag> : '--'}
          </Descriptions.Item>
          <Descriptions.Item label="归属销售">{customer.owner_name || '--'}</Descriptions.Item>
          <Descriptions.Item label="跟进状态">{customer.follow_status || '--'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {customer.created_at ? new Date(customer.created_at).toLocaleString('zh-CN') : '--'}
          </Descriptions.Item>
          <Descriptions.Item label="更新时间">
            {customer.updated_at ? new Date(customer.updated_at).toLocaleString('zh-CN') : '--'}
          </Descriptions.Item>
          {customer.remark && (
            <Descriptions.Item label="备注" span={3}>{customer.remark}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title={`关联订单（${ordersTotal}）`} style={{ marginTop: 16 }} size="small">
        <Table
          columns={orderColumns}
          dataSource={orders}
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: '暂无关联订单' }}
        />
      </Card>
    </div>
  )
}
