import { useState, useEffect } from 'react'
import {
  Form, Button, Card, Space, InputNumber, Input, Select, Table, message, Image,
} from 'antd'
import { ArrowLeftOutlined, PlusOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchOrder, createOrder, updateOrder } from '@/api/orders'
import type { OrderDetail } from '@/api/orders'
import { fetchCustomers } from '@/api/customers'
import type { Customer } from '@/api/customers'
import { fetchProducts } from '@/api/products'
import type { Product } from '@/api/products'
import { formatAmount } from '@/utils'

interface OrderLine {
  key: string
  product_id: string
  product_name: string
  product_image_url: string | null
  sku: string
  sale_price: string
  quantity: number
  unit_price: number
  subtotal: number
}

export default function OrderForm() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id)
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [customerSearch, setCustomerSearch] = useState('')
  const [lines, setLines] = useState<OrderLine[]>([])

  // 商品选择弹窗状态
  const [productPickerOpen, setProductPickerOpen] = useState(false)
  const [products, setProducts] = useState<Product[]>([])
  const [productSearch, setProductSearch] = useState('')
  const [productLoading, setProductLoading] = useState(false)

  // 加载客户列表
  useEffect(() => {
    fetchCustomers({ page: 1, page_size: 50, keyword: customerSearch || undefined })
      .then((res) => { if (res.success) setCustomers(res.data.items) })
  }, [customerSearch])

  // 加载商品列表
  const loadProducts = async () => {
    setProductLoading(true)
    try {
      const res = await fetchProducts({ page: 1, page_size: 50, keyword: productSearch || undefined, status: 'active' })
      if (res.success) setProducts(res.data.items)
    } finally {
      setProductLoading(false)
    }
  }

  useEffect(() => {
    if (productPickerOpen) loadProducts()
  }, [productPickerOpen, productSearch])

  // 编辑模式加载订单数据
  useEffect(() => {
    if (id) {
      setLoading(true)
      fetchOrder(id)
        .then((res) => {
          if (!res.success) return
          const order: OrderDetail = res.data
          form.setFieldsValue({
            customer_id: order.customer_id,
            remark: order.remark,
          })
          setLines(order.items.map((item, idx) => ({
            key: `existing-${idx}`,
            product_id: item.product_id,
            product_name: item.product_name_snapshot,
            product_image_url: item.product_image_url_snapshot,
            sku: item.product_sku_snapshot,
            sale_price: item.unit_price,
            quantity: item.quantity,
            unit_price: parseFloat(item.unit_price),
            subtotal: parseFloat(item.subtotal_amount),
          })))
        })
        .finally(() => setLoading(false))
    }
  }, [id, form])

  const addProduct = (product: Product) => {
    const existing = lines.find((l) => l.product_id === product.id)
    if (existing) {
      message.warning('该商品已在订单中')
      return
    }
    const price = parseFloat(product.sale_price)
    setLines((prev) => [
      ...prev,
      {
        key: `new-${product.id}`,
        product_id: product.id,
        product_name: product.name,
        product_image_url: product.main_image_url,
        sku: product.sku,
        sale_price: product.sale_price,
        quantity: 1,
        unit_price: price,
        subtotal: price,
      },
    ])
    setProductPickerOpen(false)
  }

  const removeLine = (key: string) => {
    setLines((prev) => prev.filter((l) => l.key !== key))
  }

  const updateLine = (key: string, field: 'quantity' | 'unit_price', value: number) => {
    setLines((prev) =>
      prev.map((l) => {
        if (l.key !== key) return l
        const updated = { ...l, [field]: value }
        updated.subtotal = updated.quantity * updated.unit_price
        return updated
      }),
    )
  }

  const totalAmount = lines.reduce((sum, l) => sum + l.subtotal, 0)

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (lines.length === 0) {
        message.error('请添加至少一个商品')
        return
      }
      setLoading(true)
      const payload = {
        customer_id: values.customer_id,
        items: lines.map((l) => ({
          product_id: l.product_id,
          quantity: l.quantity,
          unit_price: String(l.unit_price),
        })),
        remark: values.remark,
      }
      if (isEdit && id) {
        const res = await updateOrder(id, payload)
        if (res.success) {
          message.success('更新成功')
          navigate(`/orders/${id}`)
        }
      } else {
        const res = await createOrder(payload)
        if (res.success) {
          message.success('创建成功')
          navigate(`/orders/${res.data.id}`)
        }
      }
    } catch (e: unknown) {
      if (e && typeof e === 'object' && 'errorFields' in e) return
      const err = e as { response?: { data?: { error?: { message?: string } } } }
      message.error(err.response?.data?.error?.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  const lineColumns: ColumnsType<OrderLine> = [
    {
      title: '图片',
      dataIndex: 'product_image_url',
      width: 60,
      render: (url: string | null) =>
        url ? <Image src={url} width={40} height={40} style={{ objectFit: 'cover', borderRadius: 4 }} /> : '--',
    },
    { title: 'SKU', dataIndex: 'sku', width: 140 },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true },
    {
      title: '数量',
      dataIndex: 'quantity',
      width: 100,
      render: (v: number, record) => (
        <InputNumber
          min={1}
          value={v}
          onChange={(val) => val && updateLine(record.key, 'quantity', val)}
          size="small"
          style={{ width: 80 }}
        />
      ),
    },
    {
      title: '成交单价',
      dataIndex: 'unit_price',
      width: 120,
      render: (v: number, record) => (
        <InputNumber
          min={0}
          precision={2}
          value={v}
          onChange={(val) => val !== null && updateLine(record.key, 'unit_price', val)}
          size="small"
          style={{ width: 100 }}
          prefix="¥"
        />
      ),
    },
    {
      title: '小计',
      dataIndex: 'subtotal',
      width: 110,
      render: (v: number) => `¥${formatAmount(v)}`,
    },
    {
      title: '',
      width: 50,
      render: (_, record) => (
        <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeLine(record.key)} size="small" />
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/orders')}>返回列表</Button>
      </div>

      <Card title={isEdit ? '编辑订单' : '新建订单'} loading={loading}>
        <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
          <Form.Item label="客户" name="customer_id" rules={[{ required: true, message: '请选择客户' }]}>
            <Select
              showSearch
              placeholder="搜索并选择客户"
              filterOption={false}
              onSearch={setCustomerSearch}
              notFoundContent="未找到客户"
            >
              {customers.map((c) => (
                <Select.Option key={c.id} value={c.id}>
                  {c.name}{c.phone ? ` (${c.phone})` : ''}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>

        <div style={{ marginBottom: 16 }}>
          <Space style={{ marginBottom: 12 }}>
            <Button icon={<PlusOutlined />} onClick={() => setProductPickerOpen(true)}>添加商品</Button>
            <span style={{ color: '#999' }}>共 {lines.length} 项</span>
          </Space>
          <Table
            columns={lineColumns}
            dataSource={lines}
            rowKey="key"
            size="small"
            pagination={false}
            footer={() => (
              <div style={{ textAlign: 'right', fontWeight: 600 }}>
                合计：¥{formatAmount(totalAmount)}
              </div>
            )}
          />
        </div>

        <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={3} maxLength={500} />
          </Form.Item>
        </Form>

        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSubmit} loading={loading}>
              {isEdit ? '保存修改' : '创建订单'}
            </Button>
            <Button onClick={() => navigate('/orders')}>取消</Button>
          </Space>
        </Form.Item>
      </Card>

      {/* 商品选择弹窗 */}
      {productPickerOpen && (
        <Card
          title="选择商品"
          size="small"
          style={{ marginTop: 16 }}
          extra={<Button size="small" onClick={() => setProductPickerOpen(false)}>关闭</Button>}
        >
          <Input
            placeholder="搜索商品名称"
            prefix={<SearchOutlined />}
            value={productSearch}
            onChange={(e) => setProductSearch(e.target.value)}
            style={{ width: 240, marginBottom: 12 }}
            allowClear
          />
          <Table
            columns={[
              {
                title: '图片', dataIndex: 'main_image_url', width: 50,
                render: (url: string | null) =>
                  url ? <Image src={url} width={36} height={36} style={{ objectFit: 'cover', borderRadius: 4 }} /> : '--',
              },
              { title: 'SKU', dataIndex: 'sku', width: 130 },
              { title: '名称', dataIndex: 'name', ellipsis: true },
              { title: '售价', dataIndex: 'sale_price', width: 90, render: (v: string) => `¥${formatAmount(v)}` },
              { title: '库存', dataIndex: 'stock_quantity', width: 70 },
              {
                title: '', width: 80,
                render: (_, record) => (
                  <Button
                    type="link"
                    size="small"
                    disabled={lines.some((l) => l.product_id === record.id)}
                    onClick={() => addProduct(record)}
                  >
                    选择
                  </Button>
                ),
              },
            ]}
            dataSource={products}
            rowKey="id"
            size="small"
            loading={productLoading}
            pagination={false}
          />
        </Card>
      )}
    </div>
  )
}
