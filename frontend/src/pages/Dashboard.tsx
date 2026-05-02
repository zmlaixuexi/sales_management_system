import { useState, useEffect, useCallback } from 'react'
import { Card, Row, Col, Statistic, Table, Select, Tag, Spin, Empty, message } from 'antd'
import {
  DollarOutlined, ShoppingCartOutlined, RiseOutlined,
  AlertOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  fetchSalesSummary, fetchSalesTrend, fetchProductRanking, fetchInventoryWarning,
} from '@/api/reports'
import type { ProductRankingItem, InventoryWarningItem, SalesTrendItem } from '@/api/reports'
import { formatAmount } from '@/utils'
import { useAuthStore } from '@/stores/auth'

const periodOptions = [
  { label: '今日', value: 'today' },
  { label: '近 7 天', value: '7d' },
  { label: '近 30 天', value: '30d' },
  { label: '本月', value: 'this_month' },
  { label: '上月', value: 'last_month' },
]

export default function Dashboard() {
  const canViewProfit = useAuthStore(s => s.hasPermission('report:profit'))
  const [period, setPeriod] = useState('30d')
  const [summary, setSummary] = useState<{
    total_amount: string; total_cost: string; gross_profit: string
    gross_margin: string; order_count: number
  } | null>(null)
  const [trend, setTrend] = useState<SalesTrendItem[]>([])
  const [ranking, setRanking] = useState<ProductRankingItem[]>([])
  const [warnings, setWarnings] = useState<InventoryWarningItem[]>([])
  const [warningThreshold, setWarningThreshold] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [summaryRes, trendRes, rankRes, warnRes] = await Promise.all([
        fetchSalesSummary(period),
        fetchSalesTrend(period),
        fetchProductRanking({ period, limit: 10 }),
        fetchInventoryWarning(),
      ])
      if (summaryRes.success) setSummary(summaryRes.data)
      if (trendRes.success) setTrend(trendRes.data.items)
      if (rankRes.success) setRanking(rankRes.data.items)
      if (warnRes.success) {
        setWarnings(warnRes.data.items)
        setWarningThreshold(warnRes.data.threshold)
      }
    } catch (e: unknown) {
      if (!(e as Record<string, boolean>)?._toastDisplayed) message.error('加载看板数据失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }, [period])

  useEffect(() => { loadData() }, [loadData])

  // 计算趋势汇总
  const trendTotal = trend.reduce((s, t) => s + parseFloat(t.amount), 0)
  const maxDay = trend.length > 0
    ? trend.reduce((max, t) => parseFloat(t.amount) > parseFloat(max.amount) ? t : max, trend[0])
    : null

  const rankingColumns: ColumnsType<ProductRankingItem> = [
    { title: '排名', dataIndex: 'rank', width: 60 },
    { title: 'SKU', dataIndex: 'sku', width: 130 },
    { title: '商品名称', dataIndex: 'product_name', ellipsis: true },
    { title: '销量', dataIndex: 'total_quantity', width: 80 },
    { title: '销售额', dataIndex: 'total_sales', width: 120, render: (v: string) => `¥${formatAmount(v)}` },
    { title: '毛利', dataIndex: 'total_cost', width: 100, render: (v: string, record) => {
      const profit = parseFloat(record.total_sales) - parseFloat(v)
      return <span style={{ color: profit >= 0 ? '#52c41a' : '#ff4d4f' }}>¥{formatAmount(profit)}</span>
    }},
  ]

  const warningColumns: ColumnsType<InventoryWarningItem> = [
    { title: 'SKU', dataIndex: 'sku', width: 130 },
    { title: '商品名称', dataIndex: 'name', ellipsis: true },
    {
      title: '当前库存',
      dataIndex: 'stock_quantity',
      width: 100,
      render: (v: number) => (
        <Tag color={v === 0 ? 'red' : 'orange'}>{v}</Tag>
      ),
    },
    { title: '销售价', dataIndex: 'sale_price', width: 100, render: (v: string) => `¥${formatAmount(v)}` },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>首页看板</h2>
        <Select
          value={period}
          onChange={setPeriod}
          options={periodOptions}
          style={{ width: 120 }}
        />
      </div>

      <Spin spinning={loading}>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="销售总额"
                prefix={<DollarOutlined />}
                value={summary ? parseFloat(summary.total_amount) : 0}
                precision={2}
                suffix="元"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="订单数"
                prefix={<ShoppingCartOutlined />}
                value={summary?.order_count || 0}
                suffix="单"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="毛利"
                prefix={<RiseOutlined />}
                value={summary ? parseFloat(summary.gross_profit) : 0}
                precision={2}
                suffix="元"
                valueStyle={{ color: summary && parseFloat(summary.gross_profit) >= 0 ? '#3f8600' : '#cf1322' }}
              />
            </Card>
          </Col>
          {canViewProfit && (
            <Col span={6}>
              <Card>
                <Statistic
                  title="毛利率"
                  value={summary ? parseFloat(summary.gross_margin) : 0}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: summary && parseFloat(summary.gross_margin) >= 0 ? '#3f8600' : '#cf1322' }}
                />
              </Card>
            </Col>
          )}
        </Row>

        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={12}>
            <Card title="销售趋势" size="small">
              {trend.length === 0 ? (
                <Empty description="暂无数据" />
              ) : (
                <div>
                  <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>
                    期间总额：<b>¥{formatAmount(trendTotal)}</b>
                    {maxDay && parseFloat(maxDay.amount) > 0 && (
                      <span style={{ marginLeft: 16 }}>
                        峰值日：<b>{maxDay.date}</b>（¥{formatAmount(maxDay.amount)}）
                      </span>
                    )}
                  </div>
                  {/* 简易条形图：用 div 模拟，不引入图表库 */}
                  <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 120, overflow: 'hidden' }}>
                    {(() => {
                      const maxAmount = Math.max(...trend.map((t) => parseFloat(t.amount)), 1)
                      // 最多显示 30 根柱子
                      const displayTrend = trend.length > 30
                        ? trend.filter((_, i) => i % Math.ceil(trend.length / 30) === 0 || i === trend.length - 1)
                        : trend
                      return displayTrend.map((t) => {
                        const h = Math.max((parseFloat(t.amount) / maxAmount) * 110, 2)
                        return (
                          <div
                            key={t.date}
                            title={`${t.date}: ¥${formatAmount(t.amount)}（${t.order_count} 单）`}
                            style={{
                              flex: 1,
                              minWidth: 4,
                              height: h,
                              background: parseFloat(t.amount) > 0
                                ? 'linear-gradient(to top, #1890ff, #69c0ff)'
                                : '#f0f0f0',
                              borderRadius: 2,
                              cursor: 'pointer',
                            }}
                          />
                        )
                      })
                    })()}
                  </div>
                  {trend.length > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#999', marginTop: 4 }}>
                      <span>{trend[0]?.date}</span>
                      <span>{trend[trend.length - 1]?.date}</span>
                    </div>
                  )}
                </div>
              )}
            </Card>
          </Col>
          <Col span={12}>
            <Card
              title={<span><AlertOutlined style={{ marginRight: 8, color: '#fa8c16' }} />库存预警（≤{warningThreshold ?? '—'}）</span>}
              size="small"
            >
              {warnings.length === 0 ? (
                <Empty description="暂无预警商品" />
              ) : (
                <Table
                  columns={warningColumns}
                  dataSource={warnings}
                  rowKey="id"
                  size="small"
                  pagination={false}
                />
              )}
            </Card>
          </Col>
        </Row>

        <Card title="商品销售排行" size="small">
          {ranking.length === 0 ? (
            <Empty description="暂无排行数据" />
          ) : (
            <Table
              columns={rankingColumns}
              dataSource={ranking}
              rowKey="product_id"
              size="small"
              pagination={false}
            />
          )}
        </Card>
      </Spin>
    </div>
  )
}
