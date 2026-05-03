import { Table, Space } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchInventoryMovements } from '@/api/inventory'
import type { InventoryMovement } from '@/api/inventory'
import { usePaginatedList } from '@/hooks/usePaginatedList'

const movementTypeMap: Record<string, { label: string; color: string }> = {
  manual_adjust: { label: '手动调整', color: 'blue' },
  order_deduct: { label: '订单扣减', color: 'orange' },
  order_cancel_return: { label: '取消退货', color: 'green' },
}

const relatedTypeMap: Record<string, string> = {
  sales_order: '销售订单',
}

export default function InventoryPage() {
  const { data, total, loading, error, page, pageSize, onPageChange, refresh } = usePaginatedList<InventoryMovement>(
    async (params) => { const r = await fetchInventoryMovements(params); return r.data },
    {},
    '加载库存流水失败',
  )

  const columns: ColumnsType<InventoryMovement> = [
    {
      title: '变动类型',
      dataIndex: 'movement_type',
      width: 120,
      render: (v: string) => {
        const info = movementTypeMap[v] || { label: v, color: 'default' }
        return <Space><span style={{ width: 8, height: 8, borderRadius: '50%', background: info.color === 'blue' ? '#1677ff' : info.color === 'orange' ? '#fa8c16' : info.color === 'green' ? '#52c41a' : '#999', display: 'inline-block' }} />{info.label}</Space>
      },
    },
    {
      title: '变动前',
      dataIndex: 'quantity_before',
      width: 90,
    },
    {
      title: '变动量',
      dataIndex: 'quantity_change',
      width: 90,
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#52c41a' : v < 0 ? '#ff4d4f' : undefined }}>
          {v > 0 ? `+${v}` : v}
        </span>
      ),
    },
    {
      title: '变动后',
      dataIndex: 'quantity_after',
      width: 90,
    },
    {
      title: '关联类型',
      dataIndex: 'related_type',
      width: 100,
      render: (v: string | null) => v ? (relatedTypeMap[v] || v) : '--',
    },
    {
      title: '备注',
      dataIndex: 'remark',
      ellipsis: true,
      render: (v: string | null) => v || '--',
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      width: 170,
      render: (v: string | null) => v ? new Date(v).toLocaleString('zh-CN') : '--',
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>库存流水</h2>
        <Space>
          <span style={{ color: '#888' }}>共 {total} 条记录</span>
        </Space>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        locale={{ emptyText: error && !loading ? <span>加载失败，<a onClick={refresh}>重试</a></span> : loading ? '加载中...' : '暂无库存变动记录' }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50],
          showTotal: (t) => `共 ${t} 条`,
          onChange: onPageChange,
        }}
      />
    </div>
  )
}
