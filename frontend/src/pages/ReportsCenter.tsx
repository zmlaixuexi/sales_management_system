import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Tabs, Select, Statistic, Row, Col, Space, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  fetchSalesSummary,
  fetchSalesTrend,
  fetchProductRanking,
  fetchCustomerRanking,
  fetchSalespersonRanking,
  fetchInventoryWarning,
} from '@/api/reports'
import type {
  SalesSummary,
  SalesTrendItem,
  ProductRankingItem,
  CustomerRankingItem,
  SalespersonRankingItem,
  InventoryWarningItem,
} from '@/api/reports'
import { formatAmount } from '@/utils'
import useDocumentTitle from '@/hooks/useDocumentTitle'

const periodOptions = [
  { value: 'today', label: '今日' },
  { value: '7d', label: '近7天' },
  { value: '30d', label: '近30天' },
  { value: 'this_month', label: '本月' },
  { value: 'last_month', label: '上月' },
]

export default function ReportsCenter() {
  useDocumentTitle('报表中心')
  const [period, setPeriod] = useState('30d')
  const [summary, setSummary] = useState<SalesSummary | null>(null)
  const [trendItems, setTrendItems] = useState<SalesTrendItem[]>([])
  const [products, setProducts] = useState<ProductRankingItem[]>([])
  const [customers, setCustomers] = useState<CustomerRankingItem[]>([])
  const [salespersons, setSalespersons] = useState<SalespersonRankingItem[]>([])
  const [inventory, setInventory] = useState<InventoryWarningItem[]>([])
  const [inventoryTotal, setInventoryTotal] = useState(0)
  const [loading, setLoading] = useState<string | null>(null)

  const loadSummary = useCallback(async (p: string) => {
    setLoading('summary')
    try {
      const res = await fetchSalesSummary(p)
      if (res.success) setSummary(res.data)
    } catch (e: unknown) {
      if (!(e as Record<string, boolean>)?._toastDisplayed) message.error('加载销售概览失败')
    } finally {
      setLoading(null)
    }
  }, [])

  const loadTrend = useCallback(async (p: string) => {
    setLoading('trend')
    try {
      const res = await fetchSalesTrend(p)
      if (res.success) setTrendItems(res.data.items)
    } catch (e: unknown) {
      if (!(e as Record<string, boolean>)?._toastDisplayed) message.error('加载销售趋势失败')
    } finally {
      setLoading(null)
    }
  }, [])

  const loadProducts = useCallback(async (p: string) => {
    setLoading('products')
    try {
      const res = await fetchProductRanking({ period: p, limit: 20 })
      if (res.success) setProducts(res.data.items)
    } catch (e: unknown) {
      if (!(e as Record<string, boolean>)?._toastDisplayed) message.error('加载商品排行失败')
    } finally {
      setLoading(null)
    }
  }, [])

  const loadCustomers = useCallback(async (p: string) => {
    setLoading('customers')
    try {
      const res = await fetchCustomerRanking({ period: p, limit: 20 })
      if (res.success) setCustomers(res.data.items)
    } catch (e: unknown) {
      if (!(e as Record<string, boolean>)?._toastDisplayed) message.error('加载客户排行失败')
    } finally {
      setLoading(null)
    }
  }, [])

  const loadSalespersons = useCallback(async (p: string) => {
    setLoading('salespersons')
    try {
      const res = await fetchSalespersonRanking({ period: p, limit: 20 })
      if (res.success) setSalespersons(res.data.items)
    } catch (e: unknown) {
      if (!(e as Record<string, boolean>)?._toastDisplayed) message.error('加载销售排行失败')
    } finally {
      setLoading(null)
    }
  }, [])

  const loadInventory = useCallback(async () => {
    setLoading('inventory')
    try {
      const res = await fetchInventoryWarning()
      if (res.success) {
        setInventory(res.data.items)
        setInventoryTotal(res.data.total)
      }
    } catch (e: unknown) {
      if (!(e as Record<string, boolean>)?._toastDisplayed) message.error('加载库存预警失败')
    } finally {
      setLoading(null)
    }
  }, [])

  useEffect(() => {
    loadSummary(period)
    loadTrend(period)
    loadProducts(period)
    loadCustomers(period)
    loadSalespersons(period)
    loadInventory()
  }, [period, loadSummary, loadTrend, loadProducts, loadCustomers, loadSalespersons, loadInventory])

  const handlePeriodChange = (val: string) => {
    setPeriod(val)
  }

  const trendColumns: ColumnsType<SalesTrendItem> = [
    { title: '日期', dataIndex: 'date', width: 120 },
    { title: '销售额', dataIndex: 'amount', width: 120, render: (v: string) => `¥${formatAmount(v)}` },
    { title: '订单数', dataIndex: 'order_count', width: 80 },
  ]

  const productColumns: ColumnsType<ProductRankingItem> = [
    { title: '排名', dataIndex: 'rank', width: 60 },
    { title: 'SKU', dataIndex: 'sku', width: 120, render: (v: string | null) => v || '--' },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true },
    { title: '销量', dataIndex: 'total_quantity', width: 80 },
    { title: '销售额', dataIndex: 'total_sales', width: 120, render: (v: string) => `¥${formatAmount(v)}` },
    ...(summary?.total_cost !== undefined ? [{
      title: '成本' as const,
      dataIndex: 'total_cost' as const,
      width: 120,
      render: (v: string) => `¥${formatAmount(v)}`,
    }] : []),
  ]

  const customerColumns: ColumnsType<CustomerRankingItem> = [
    { title: '排名', dataIndex: 'rank', width: 60 },
    { title: '客户名称', dataIndex: 'customer_name', ellipsis: true },
    { title: '订单数', dataIndex: 'order_count', width: 80 },
    { title: '销售额', dataIndex: 'total_sales', width: 120, render: (v: string) => `¥${formatAmount(v)}` },
    ...(summary?.total_cost !== undefined ? [
      { title: '成本' as const, dataIndex: 'total_cost' as const, width: 120, render: (v?: string) => v ? `¥${formatAmount(v)}` : '--' },
      { title: '毛利' as const, dataIndex: 'gross_profit' as const, width: 120, render: (v?: string) => v ? `¥${formatAmount(v)}` : '--' },
    ] : []),
  ]

  const salespersonColumns: ColumnsType<SalespersonRankingItem> = [
    { title: '排名', dataIndex: 'rank', width: 60 },
    { title: '销售员', dataIndex: 'name', ellipsis: true },
    { title: '订单数', dataIndex: 'order_count', width: 80 },
    { title: '销售额', dataIndex: 'total_sales', width: 120, render: (v: string) => `¥${formatAmount(v)}` },
    ...(summary?.total_cost !== undefined ? [
      { title: '成本' as const, dataIndex: 'total_cost' as const, width: 120, render: (v?: string) => v ? `¥${formatAmount(v)}` : '--' },
      { title: '毛利' as const, dataIndex: 'gross_profit' as const, width: 120, render: (v?: string) => v ? `¥${formatAmount(v)}` : '--' },
    ] : []),
  ]

  const inventoryColumns: ColumnsType<InventoryWarningItem> = [
    { title: 'SKU', dataIndex: 'sku', width: 120 },
    { title: '商品名称', dataIndex: 'name', ellipsis: true },
    {
      title: '当前库存',
      dataIndex: 'stock_quantity',
      width: 100,
      render: (v: number) => <Tag color={v === 0 ? 'red' : 'orange'}>{v}</Tag>,
    },
    { title: '销售价', dataIndex: 'sale_price', width: 120, render: (v: string) => `¥${formatAmount(v)}` },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>报表中心</h2>
        <Space>
          <span>统计周期：</span>
          <Select value={period} onChange={handlePeriodChange} options={periodOptions} style={{ width: 120 }} />
        </Space>
      </div>

      <Tabs
        defaultActiveKey="summary"
        items={[
          {
            key: 'summary',
            label: '销售概览',
            children: (
              <div>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={6}>
                    <Card><Statistic title="销售总额" value={summary?.total_amount ? parseFloat(summary.total_amount) : 0} precision={2} prefix="¥" loading={loading === 'summary'} /></Card>
                  </Col>
                  <Col span={6}>
                    <Card><Statistic title="订单数" value={summary?.order_count ?? 0} loading={loading === 'summary'} /></Card>
                  </Col>
                  {summary?.total_cost !== undefined && (
                    <>
                      <Col span={6}>
                        <Card><Statistic title="总成本" value={parseFloat(summary.total_cost)} precision={2} prefix="¥" loading={loading === 'summary'} /></Card>
                      </Col>
                      <Col span={6}>
                        <Card><Statistic title="毛利" value={parseFloat(summary.gross_profit)} precision={2} prefix="¥" loading={loading === 'summary'} /></Card>
                      </Col>
                    </>
                  )}
                </Row>
                <Card title="销售趋势" size="small">
                  <Table
                    columns={trendColumns}
                    dataSource={trendItems}
                    rowKey="date"
                    size="small"
                    loading={loading === 'trend'}
                    pagination={{ pageSize: 10 }}
                    locale={{ emptyText: '暂无趋势数据' }}
                  />
                </Card>
              </div>
            ),
          },
          {
            key: 'products',
            label: '商品排行',
            children: (
              <Card size="small">
                <Table
                  columns={productColumns}
                  dataSource={products}
                  rowKey="rank"
                  size="small"
                  loading={loading === 'products'}
                  pagination={{ pageSize: 10 }}
                  locale={{ emptyText: '暂无商品排行数据' }}
                />
              </Card>
            ),
          },
          {
            key: 'customers',
            label: '客户排行',
            children: (
              <Card size="small">
                <Table
                  columns={customerColumns}
                  dataSource={customers}
                  rowKey="rank"
                  size="small"
                  loading={loading === 'customers'}
                  pagination={{ pageSize: 10 }}
                  locale={{ emptyText: '暂无客户排行数据' }}
                />
              </Card>
            ),
          },
          {
            key: 'salespersons',
            label: '销售排行',
            children: (
              <Card size="small">
                <Table
                  columns={salespersonColumns}
                  dataSource={salespersons}
                  rowKey="rank"
                  size="small"
                  loading={loading === 'salespersons'}
                  pagination={{ pageSize: 10 }}
                  locale={{ emptyText: '暂无销售排行数据' }}
                />
              </Card>
            ),
          },
          {
            key: 'inventory',
            label: `库存预警（${inventoryTotal}）`,
            children: (
              <Card size="small">
                <Table
                  columns={inventoryColumns}
                  dataSource={inventory}
                  rowKey="id"
                  size="small"
                  loading={loading === 'inventory'}
                  pagination={false}
                  locale={{ emptyText: '暂无库存预警' }}
                />
              </Card>
            ),
          },
        ]}
      />
    </div>
  )
}
