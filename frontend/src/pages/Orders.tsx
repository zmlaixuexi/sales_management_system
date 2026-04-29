import { useState, useEffect, useCallback } from 'react'
import { Table, Button, Input, Select, Space, Tag, message } from 'antd'
import { PlusOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchOrders } from '@/api/orders'
import type { Order } from '@/api/orders'
import { formatAmount, formatPercent } from '@/utils'

const statusMap: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  confirmed: { color: 'blue', label: '已确认' },
  cancelled: { color: 'red', label: '已取消' },
  partially_paid: { color: 'orange', label: '部分收款' },
  completed: { color: 'green', label: '已完成' },
}

export default function OrdersPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<Order[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchOrders({
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
        status: statusFilter,
      })
      if (res.success) {
        setData(res.data.items)
        setTotal(res.data.total)
      }
    } catch {
      message.error('加载订单列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, keyword, statusFilter])

  useEffect(() => { loadData() }, [loadData])

  const columns: ColumnsType<Order> = [
    {
      title: '订单号',
      dataIndex: 'order_no',
      width: 200,
      render: (v: string, record) => (
        <Button type="link" size="small" onClick={() => navigate(`/orders/${record.id}`)}>{v}</Button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (s: string) => {
        const info = statusMap[s] || { color: 'default', label: s }
        return <Tag color={info.color}>{info.label}</Tag>
      },
    },
    { title: '明细数', dataIndex: 'item_count', width: 80 },
    {
      title: '订单金额',
      dataIndex: 'total_amount',
      width: 120,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
    {
      title: '已收金额',
      dataIndex: 'paid_amount',
      width: 120,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
    {
      title: '毛利',
      dataIndex: 'gross_profit',
      width: 100,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
    {
      title: '毛利率',
      dataIndex: 'gross_margin',
      width: 90,
      render: (v: string) => formatPercent(v),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 170,
      render: (v: string | null) => v ? new Date(v).toLocaleString('zh-CN') : '--',
    },
    {
      title: '操作',
      width: 100,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/orders/${record.id}`)}
        >
          详情
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Space>
          <Input
            placeholder="搜索订单号"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => { setKeyword(e.target.value); setPage(1) }}
            style={{ width: 240 }}
            allowClear
          />
          <Select
            placeholder="状态筛选"
            value={statusFilter}
            onChange={(v) => { setStatusFilter(v); setPage(1) }}
            style={{ width: 120 }}
            allowClear
            options={Object.entries(statusMap).map(([value, { label }]) => ({ label, value }))}
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/orders/new')}>
          新建订单
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />
    </div>
  )
}
