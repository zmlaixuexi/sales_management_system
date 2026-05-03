import { useState } from 'react'
import { Table, Button, Input, Select, Space, Tag } from 'antd'
import { PlusOutlined, SearchOutlined, EyeOutlined, DownloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchOrders } from '@/api/orders'
import type { Order } from '@/api/orders'
import { formatAmount, formatPercent } from '@/utils'
import { downloadCsv } from '@/api/request'
import { usePaginatedList } from '@/hooks/usePaginatedList'
import { orderStatusMap as statusMap } from '@/constants/statusMaps'
import { useAuthStore } from '@/stores/auth'
import useDocumentTitle from '@/hooks/useDocumentTitle'

export default function OrdersPage() {
  useDocumentTitle('订单管理')
  const navigate = useNavigate()
  const canViewCost = useAuthStore(s => s.hasPermission('product:view_cost'))
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)

  const { data, total, loading, error, page, pageSize, keyword, setPage, setKeyword, onPageChange, refresh } = usePaginatedList<Order>(
    async (params) => { const r = await fetchOrders(params); return r.data },
    { status: statusFilter },
    '加载订单列表失败',
  )

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
    ...(canViewCost ? [
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
    ] : []),
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
            onChange={(e) => setKeyword(e.target.value)}
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
        <Space>
          <Button icon={<DownloadOutlined />} onClick={() => downloadCsv('/exports/orders', { keyword: keyword || undefined, status: statusFilter })}>
            导出
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/orders/new')}>
            新建订单
          </Button>
        </Space>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        locale={{ emptyText: error && !loading ? <span>加载失败，<a onClick={refresh}>重试</a></span> : loading ? '加载中...' : keyword || statusFilter ? '没有匹配的订单' : '暂无订单，点击"新建订单"添加' }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50, 100],
          showTotal: (t) => `共 ${t} 条`,
          onChange: onPageChange,
        }}
      />
    </div>
  )
}
