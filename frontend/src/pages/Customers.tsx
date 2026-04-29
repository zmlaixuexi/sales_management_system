import { useState, useEffect, useCallback, useRef } from 'react'
import { Table, Button, Input, Space, Tag, Popconfirm, message, Select } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchCustomers, deleteCustomer } from '@/api/customers'
import type { Customer } from '@/api/customers'
import { downloadCsv } from '@/utils'
import apiClient from '@/api/client'

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

export default function CustomersPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<Customer[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [keyword, setKeyword] = useState('')
  const [sourceFilter, setSourceFilter] = useState<string | undefined>(undefined)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data: res } = await apiClient.post('/customers/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      if (res.success) {
        message.success(res.message)
        loadData()
      }
    } catch { /* 统一错误提示 */ }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchCustomers({
        page,
        page_size: pageSize,
        keyword: keyword || undefined,
        source: sourceFilter,
      })
      if (res.success) {
        setData(res.data.items)
        setTotal(res.data.total)
      }
    } catch {
      message.error('加载客户列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, keyword, sourceFilter])

  useEffect(() => { loadData() }, [loadData])

  const handleDelete = async (id: string) => {
    try {
      await deleteCustomer(id)
      message.success('删除成功')
      loadData()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { error?: { message?: string } } } }
      message.error(err.response?.data?.error?.message || '删除失败')
    }
  }

  const columns: ColumnsType<Customer> = [
    { title: '客户名称', dataIndex: 'name', ellipsis: true },
    { title: '联系人', dataIndex: 'contact_name', width: 100, render: (v: string | null) => v || '--' },
    { title: '电话', dataIndex: 'phone', width: 130, render: (v: string | null) => v || '--' },
    {
      title: '来源',
      dataIndex: 'source',
      width: 90,
      render: (v: string | null) => (v ? sourceMap[v] || v : '--'),
    },
    {
      title: '等级',
      dataIndex: 'level',
      width: 80,
      render: (v: string | null) => {
        if (!v) return '--'
        const info = levelMap[v] || { color: 'default', label: v }
        return <Tag color={info.color}>{info.label}</Tag>
      },
    },
    { title: '归属销售', dataIndex: 'owner_name', width: 100, render: (v: string | null) => v || '--' },
    {
      title: '跟进状态',
      dataIndex: 'follow_status',
      width: 100,
      render: (v: string | null) => v || '--',
    },
    {
      title: '操作',
      width: 140,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => navigate(`/customers/${record.id}/edit`)}>编辑</Button>
          <Popconfirm title="确定删除该客户？" onConfirm={() => handleDelete(record.id)}>
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
            placeholder="搜索客户名称/电话"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => { setKeyword(e.target.value); setPage(1) }}
            style={{ width: 240 }}
            allowClear
          />
          <Select
            placeholder="来源筛选"
            value={sourceFilter}
            onChange={(v) => { setSourceFilter(v); setPage(1) }}
            style={{ width: 120 }}
            allowClear
            options={Object.entries(sourceMap).map(([value, label]) => ({ value, label }))}
          />
        </Space>
        <Space>
          <Button icon={<UploadOutlined />} onClick={() => fileInputRef.current?.click()}>
            导入
          </Button>
          <input ref={fileInputRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={handleImport} />
          <Button icon={<DownloadOutlined />} onClick={() => downloadCsv('/exports/customers', { keyword: keyword || undefined, source: sourceFilter })}>
            导出
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/customers/new')}>
            新增客户
          </Button>
        </Space>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        locale={{ emptyText: loading ? '加载中...' : keyword || sourceFilter ? '没有匹配的客户' : '暂无客户，点击"新增客户"添加' }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50, 100],
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />
    </div>
  )
}
