import { Table, Button, Tag, Space } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchPayments } from '@/api/payments'
import type { Payment } from '@/api/payments'
import { formatAmount } from '@/utils'
import { usePaginatedList } from '@/hooks/usePaginatedList'
import { downloadCsv } from '@/api/request'
import { paymentStatusMap as statusMap, paymentMethodMap } from '@/constants/statusMaps'
import useDocumentTitle from '@/hooks/useDocumentTitle'

export default function PaymentsPage() {
  useDocumentTitle('收款管理')
  const navigate = useNavigate()

  const { data, total, loading, error, page, pageSize, onPageChange, refresh } = usePaginatedList<Payment>(
    async (params) => { const r = await fetchPayments(params); return r.data },
    {},
    '加载收款列表失败',
  )

  const columns: ColumnsType<Payment> = [
    {
      title: '收款ID',
      dataIndex: 'id',
      width: 100,
      render: (v: string) => v.slice(0, 8),
    },
    {
      title: '订单ID',
      dataIndex: 'order_id',
      width: 100,
      render: (v: string) => (
        <Button type="link" size="small" onClick={() => navigate(`/orders/${v}`)}>{v.slice(0, 8)}</Button>
      ),
    },
    {
      title: '金额',
      dataIndex: 'amount',
      width: 120,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
    {
      title: '收款方式',
      dataIndex: 'payment_method',
      width: 100,
      render: (v: string) => paymentMethodMap[v] || v,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (v: string) => {
        const info = statusMap[v] || { color: 'default', label: v }
        return <Tag color={info.color}>{info.label}</Tag>
      },
    },
    {
      title: '收款时间',
      dataIndex: 'paid_at',
      width: 170,
      render: (v: string | null) => v ? new Date(v).toLocaleString('zh-CN') : '--',
    },
    {
      title: '备注',
      dataIndex: 'remark',
      ellipsis: true,
      render: (v: string | null) => v || '--',
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
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>收款记录</h2>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={() => downloadCsv('/exports/payments')}>导出</Button>
          <span style={{ color: '#888' }}>共 {total} 条记录</span>
        </Space>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        locale={{ emptyText: error && !loading ? <span>加载失败，<a onClick={refresh}>重试</a></span> : loading ? '加载中...' : '暂无收款记录' }}
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
