import { useState, useRef } from 'react'
import {
  Table, Button, Input, Select, Space, Tag, Popconfirm, message, Image,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, StopOutlined, SearchOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchProducts, deleteProduct, disableProduct } from '@/api/products'
import { getApiErrorMessage, isToastDisplayed } from '@/utils'
import type { Product, ProductListParams } from '@/api/products'
import { formatAmount, formatPercent } from '@/utils'
import { downloadCsv } from '@/api/request'
import apiClient from '@/api/client'
import { usePaginatedList } from '@/hooks/usePaginatedList'
import { productStatusMap as statusMap } from '@/constants/statusMaps'
import { useAuthStore } from '@/stores/auth'
import useDocumentTitle from '@/hooks/useDocumentTitle'

export default function ProductsPage() {
  useDocumentTitle('商品管理')
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data, total, loading, error, page, pageSize, keyword, setPage, setKeyword, onPageChange, refresh: loadData } = usePaginatedList<Product>(
    async (params) => {
      const query: ProductListParams = {
        page: typeof params.page === 'number' ? params.page : undefined,
        page_size: typeof params.page_size === 'number' ? params.page_size : undefined,
        keyword: typeof params.keyword === 'string' ? params.keyword : undefined,
        status: typeof params.status === 'string' ? params.status : undefined,
      }
      const r = await fetchProducts(query)
      return r.data
    },
    { status: statusFilter },
    '加载商品列表失败',
  )

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data: res } = await apiClient.post('/products/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      if (res.success) {
        message.success(res.message)
        loadData()
      }
    } catch { /* 统一错误提示 */ }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteProduct(id)
      message.success('删除成功')
      loadData()
    } catch (e: unknown) {
      if (!isToastDisplayed(e)) message.error(getApiErrorMessage(e, '删除失败'))
    }
  }

  const handleDisable = async (id: string) => {
    try {
      await disableProduct(id)
      message.success('停用成功')
      loadData()
    } catch (e: unknown) {
      if (!isToastDisplayed(e)) message.error(getApiErrorMessage(e, '停用失败'))
    }
  }

  const canViewCost = useAuthStore(s => s.hasPermission('product:view_cost'))

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
    ...(canViewCost ? [
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
    ] : []),
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
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Space wrap>
          <Input
            placeholder="搜索商品名称"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            style={{ width: 240, maxWidth: '100%' }}
            allowClear
          />
          <Select
            placeholder="状态筛选"
            value={statusFilter}
            onChange={(v) => { setStatusFilter(v); setPage(1) }}
            style={{ width: 120, minWidth: 100 }}
            allowClear
            options={[
              { label: '上架', value: 'active' },
              { label: '下架', value: 'inactive' },
              { label: '停用', value: 'disabled' },
            ]}
          />
        </Space>
        <Space wrap>
          <Button icon={<UploadOutlined />} onClick={() => fileInputRef.current?.click()}>
            导入
          </Button>
          <input ref={fileInputRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleImport} />
          <Button icon={<DownloadOutlined />} onClick={() => downloadCsv('/exports/products', { keyword: keyword || undefined, status: statusFilter })}>
            导出
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/products/new')}>
            新增商品
          </Button>
        </Space>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: error && !loading ? <span>加载失败，<a onClick={loadData}>重试</a></span> : loading ? '加载中...' : keyword || statusFilter ? '没有匹配的商品' : '暂无商品，点击"新增商品"添加' }}
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
