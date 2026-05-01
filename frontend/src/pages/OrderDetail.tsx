import { useState, useEffect, useCallback } from 'react'
import {
  Card, Descriptions, Table, Button, Space, Tag, Popconfirm, InputNumber, Select,
  Input, message, Image, Modal,
} from 'antd'
import { ArrowLeftOutlined, EditOutlined, DollarOutlined } from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchOrder, confirmOrder, cancelOrder } from '@/api/orders'
import type { OrderDetail, OrderItem, OrderPayment } from '@/api/orders'
import { createPayment, reversePayment } from '@/api/payments'
import { formatAmount, formatPercent, getApiErrorMessage } from '@/utils'

const statusMap: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  confirmed: { color: 'blue', label: '已确认' },
  cancelled: { color: 'red', label: '已取消' },
  partially_paid: { color: 'orange', label: '部分收款' },
  completed: { color: 'green', label: '已完成' },
}

const paymentMethodLabels: Record<string, string> = {
  cash: '现金',
  bank_transfer: '银行转账',
  wechat: '微信',
  alipay: '支付宝',
  other: '其他',
}

export default function OrderDetail() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // 收款弹窗状态
  const [payModalOpen, setPayModalOpen] = useState(false)
  const [payAmount, setPayAmount] = useState<number>(0)
  const [payMethod, setPayMethod] = useState('cash')
  const [payRemark, setPayRemark] = useState('')

  const loadOrder = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const res = await fetchOrder(id)
      if (res.success) setOrder(res.data)
    } catch {
      message.error('加载订单详情失败')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { loadOrder() }, [loadOrder])

  const handleConfirm = async () => {
    if (!id || actionLoading) return
    setActionLoading('confirm')
    try {
      const res = await confirmOrder(id)
      if (res.success) {
        message.success('订单已确认，库存已扣减')
        loadOrder()
      }
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, '确认失败'))
    } finally {
      setActionLoading(null)
    }
  }

  const handleCancel = async () => {
    if (!id || actionLoading) return
    setActionLoading('cancel')
    try {
      const res = await cancelOrder(id)
      if (res.success) {
        message.success('订单已取消')
        loadOrder()
      }
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, '取消失败'))
    } finally {
      setActionLoading(null)
    }
  }

  const handleRegisterPayment = async () => {
    if (!id || actionLoading || payAmount <= 0) {
      message.error('请输入正确的收款金额')
      return
    }
    setActionLoading('payment')
    try {
      const res = await createPayment(id, {
        amount: String(payAmount),
        payment_method: payMethod,
        remark: payRemark || undefined,
      })
      if (res.success) {
        message.success('收款登记成功')
        setPayModalOpen(false)
        setPayAmount(0)
        setPayRemark('')
        loadOrder()
      }
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, '收款登记失败'))
    } finally {
      setActionLoading(null)
    }
  }

  const handleReversePayment = async (paymentId: string) => {
    if (actionLoading) return
    setActionLoading('reverse')
    try {
      const res = await reversePayment(paymentId)
      if (res.success) {
        message.success('冲正成功')
        loadOrder()
      }
    } catch (e: unknown) {
      message.error(getApiErrorMessage(e, '冲正失败'))
    } finally {
      setActionLoading(null)
    }
  }

  if (!order) {
    return <Card loading={loading}>加载中...</Card>
  }

  const remaining = parseFloat(order.total_amount) - parseFloat(order.paid_amount)
  const statusInfo = statusMap[order.status] || { color: 'default', label: order.status }
  const canEdit = order.status === 'draft'
  const canConfirm = order.status === 'draft'
  const canCancel = ['draft', 'confirmed', 'partially_paid'].includes(order.status)
  const canPay = ['confirmed', 'partially_paid'].includes(order.status)

  const itemColumns: ColumnsType<OrderItem> = [
    {
      title: '图片',
      dataIndex: 'product_image_url_snapshot',
      width: 60,
      render: (url: string | null) =>
        url ? <Image src={url} width={40} height={40} style={{ objectFit: 'cover', borderRadius: 4 }} /> : '--',
    },
    { title: 'SKU', dataIndex: 'product_sku_snapshot', width: 140 },
    { title: '商品名称', dataIndex: 'product_name_snapshot', ellipsis: true },
    { title: '数量', dataIndex: 'quantity', width: 70 },
    {
      title: '成交单价',
      dataIndex: 'unit_price',
      width: 100,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
    {
      title: '折扣',
      dataIndex: 'discount_amount',
      width: 80,
      render: (v: string) => {
        const val = parseFloat(v)
        return val > 0 ? `-¥${formatAmount(v)}` : '--'
      },
    },
    {
      title: '小计',
      dataIndex: 'subtotal_amount',
      width: 110,
      render: (v: string) => `¥${formatAmount(v)}`,
    },
  ]

  const paymentColumns: ColumnsType<OrderPayment> = [
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
      render: (v: string) => paymentMethodLabels[v] || v,
    },
    {
      title: '收款时间',
      dataIndex: 'paid_at',
      width: 170,
      render: (v: string | null) => v ? new Date(v).toLocaleString('zh-CN') : '--',
    },
    { title: '备注', dataIndex: 'remark', ellipsis: true },
    {
      title: '操作',
      width: 80,
      render: (_, record) => (
        <Popconfirm title="确定冲正该笔收款？" onConfirm={() => handleReversePayment(record.id)}>
          <Button type="link" size="small" danger loading={actionLoading === 'reverse'} disabled={!!actionLoading}>冲正</Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/orders')}>返回列表</Button>
        <Space>
          {canEdit && (
            <Button icon={<EditOutlined />} onClick={() => navigate(`/orders/${id}/edit`)}>编辑</Button>
          )}
          {canConfirm && (
            <Popconfirm title="确认订单将扣减库存，确定？" onConfirm={handleConfirm}>
              <Button type="primary" loading={actionLoading === 'confirm'} disabled={!!actionLoading}>确认订单</Button>
            </Popconfirm>
          )}
          {canPay && (
            <Button icon={<DollarOutlined />} onClick={() => setPayModalOpen(true)} disabled={!!actionLoading}>登记收款</Button>
          )}
          {canCancel && (
            <Popconfirm title="确定取消该订单？" onConfirm={handleCancel}>
              <Button danger loading={actionLoading === 'cancel'} disabled={!!actionLoading}>取消订单</Button>
            </Popconfirm>
          )}
        </Space>
      </div>

      <Card title={`订单 ${order.order_no}`} loading={loading}>
        <Descriptions column={3} size="small" bordered>
          <Descriptions.Item label="订单号">{order.order_no}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {order.created_at ? new Date(order.created_at).toLocaleString('zh-CN') : '--'}
          </Descriptions.Item>
          <Descriptions.Item label="订单金额">¥{formatAmount(order.total_amount)}</Descriptions.Item>
          <Descriptions.Item label="已收金额">¥{formatAmount(order.paid_amount)}</Descriptions.Item>
          <Descriptions.Item label="剩余应收">¥{formatAmount(remaining)}</Descriptions.Item>
          <Descriptions.Item label="总成本">¥{formatAmount(order.total_cost)}</Descriptions.Item>
          <Descriptions.Item label="毛利">¥{formatAmount(order.gross_profit)}</Descriptions.Item>
          <Descriptions.Item label="毛利率">{formatPercent(order.gross_margin)}</Descriptions.Item>
          {order.remark && (
            <Descriptions.Item label="备注" span={3}>{order.remark}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title="订单明细" style={{ marginTop: 16 }} size="small">
        <Table
          columns={itemColumns}
          dataSource={order.items}
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: '暂无订单明细' }}
          footer={() => (
            <div style={{ textAlign: 'right', fontWeight: 600 }}>
              共 {order.items.length} 项，合计：¥{formatAmount(order.total_amount)}
            </div>
          )}
        />
      </Card>

      {order.payments.length > 0 && (
        <Card title="收款记录" style={{ marginTop: 16 }} size="small">
          <Table
            columns={paymentColumns}
            dataSource={order.payments}
            rowKey="id"
            size="small"
            pagination={false}
          />
        </Card>
      )}

      {/* 收款弹窗 */}
      <Modal
        title="登记收款"
        open={payModalOpen}
        onOk={handleRegisterPayment}
        onCancel={() => setPayModalOpen(false)}
        confirmLoading={actionLoading === 'payment'}
        okText="确认收款"
      >
        <div style={{ marginBottom: 12 }}>
          <span>剩余应收：<b>¥{formatAmount(remaining)}</b></span>
        </div>
        <div style={{ marginBottom: 12 }}>
          <span>收款金额：</span>
          <InputNumber
            min={0.01}
            max={remaining}
            precision={2}
            value={payAmount}
            onChange={(v) => setPayAmount(v || 0)}
            style={{ width: 200 }}
            prefix="¥"
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <span>收款方式：</span>
          <Select
            value={payMethod}
            onChange={setPayMethod}
            style={{ width: 200 }}
            options={Object.entries(paymentMethodLabels).map(([value, label]) => ({ label, value }))}
          />
        </div>
        <div>
          <span>备注：</span>
          <Input
            value={payRemark}
            onChange={(e) => setPayRemark(e.target.value)}
            placeholder="可选"
            style={{ width: 300 }}
          />
        </div>
      </Modal>
    </div>
  )
}
