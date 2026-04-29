import { useState, useEffect, useCallback } from 'react'
import {
  Table, Button, Input, Select, Space, Tag, Popconfirm, message, Image,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, StopOutlined, SearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchProducts, deleteProduct, disableProduct } from '@/api/products'
import type { Product } from '@/api/products'
import { formatAmount, formatPercent } from '@/utils'

const statusMap: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '上架' },
  inactive: { color: 'orange', label: '下架' },
  disabled: { color: 'red', label: '停用' },
}

export default function ProductsPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<Product[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchProducts({ page, page_size: pageSize, keyword: keyword || undefined, status: statusFilter })
      if (res.success) {
        setData(res.data.items)
        setTotal(res.data.total)
      }
    } catch {
      message.error('加载商品列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, keyword, statusFilter])

  useEffect(() => { loadData() }, [loadData])

  const handleDelete = async (id: string) => {
    try {
      await deleteProduct(id)
      message.success('删除成功')
      loadData()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: { message?: string } } } }
      message.error(err.response?.data?.error?.message || '删除失败')
    }
  }

  const handleDisable = async (id: string) => {
    try {
      await disableProduct(id)
      message.success('停用成功')
      loadData()
    } catch {
      message.error('停用失败')
    }
  }

  const columns: ColumnsType<Product> = [
    {
      title: '图片',
      dataIndex: 'main_image_url',
      width: 80,
      render: (url: string | null) =>
        url ? <Image src={url} width={50} height={50} style={{ objectFit: 'cover', borderRadius: 4 }} /> : '--',
    },
    { title: 'SKU', dataIndex: 'sku', width: 160 },
    { title: '商品名称', dataIndex: 'name', ellipsis: true },
    { title: '分类', dataIndex: 'category_name', width: 100, render: (v: string | null) => v || '--' },
    {
      title: '销售价',
      dataIndex: 'sale_price',
      width: 100,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
    {
      title: '成本价',
      dataIndex: 'cost_price',
      width: 100,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
    {
      title: '利润',
      dataIndex: 'unit_profit',
      width: 100,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
    {
      title: '毛利率',
      dataIndex: 'gross_margin',
      width: 90,
      render: (v: string) => formatPercent(v),
    },
    { title: '库存', dataIndex: 'stock_quantity', width: 80 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (s: string) => {
        const info = statusMap[s] || { color: 'default', label: s }
        return <Tag color={info.color}>{info.label}</Tag>
      },
    },
    {
      title: '操作',
      width: 160,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => navigate(`/products/${record.id}/edit`)}>编辑</Button>
          {record.status === 'active' && (
            <Button type="link" size="small" icon={<StopOutlined />} onClick={() => handleDisable(record.id)}>停用</Button>
          )}
          <Popconfirm title="确定删除该商品？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Space>
          <Input
            placeholder="搜索商品名称"
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
            options={[
              { label: '上架', value: 'active' },
              { label: '下架', value: 'inactive' },
              { label: '停用', value: 'disabled' },
            ]}
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/products/new')}>
          新增商品
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
