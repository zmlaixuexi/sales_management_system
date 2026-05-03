/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _reportMocks = {
  fetchSalesSummary: vi.fn(),
  fetchSalesTrend: vi.fn(),
  fetchProductRanking: vi.fn(),
  fetchCustomerRanking: vi.fn(),
  fetchSalespersonRanking: vi.fn(),
  fetchInventoryWarning: vi.fn(),
}

vi.mock('@/api/reports', () => ({
  fetchSalesSummary: (...args: any[]) => _reportMocks.fetchSalesSummary(...args),
  fetchSalesTrend: (...args: any[]) => _reportMocks.fetchSalesTrend(...args),
  fetchProductRanking: (...args: any[]) => _reportMocks.fetchProductRanking(...args),
  fetchCustomerRanking: (...args: any[]) => _reportMocks.fetchCustomerRanking(...args),
  fetchSalespersonRanking: (...args: any[]) => _reportMocks.fetchSalespersonRanking(...args),
  fetchInventoryWarning: (...args: any[]) => _reportMocks.fetchInventoryWarning(...args),
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
}))

const _messageError = vi.fn()
vi.mock('antd', () => ({
  Card: ({ title, children }: any) => (
    <div data-testid="card" data-title={title}>{children}</div>
  ),
  Tabs: ({ items }: any) => (
    <div data-testid="tabs">
      {items?.map((item: any) => (
        <div key={item.key} data-testid={`tab-${item.key}`}>{item.label}{item.children}</div>
      ))}
    </div>
  ),
  Table: ({ dataSource, columns, rowKey, locale }: any) => (
    <div>
      <table data-testid="table">
        <tbody>
          {dataSource?.map((row: any) => (
            <tr key={row[rowKey]} data-testid={`row-${row[rowKey]}`}>
              {columns?.map((col: any) => (
                <td key={col.dataIndex} data-col={col.dataIndex}>
                  {col.render ? col.render(row[col.dataIndex], row) : row[col.dataIndex]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {(!dataSource || dataSource.length === 0) && locale?.emptyText && <span>{locale.emptyText}</span>}
    </div>
  ),
  Select: ({ value, onChange, options }: any) => (
    <select data-testid="select" value={value} onChange={(e: any) => onChange?.(e.target.value)}>
      {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  ),
  Statistic: ({ title, value, prefix }: any) => (
    <div data-testid="statistic" data-title={title}>{prefix}{value}</div>
  ),
  Row: ({ children }: any) => <div data-testid="row">{children}</div>,
  Col: ({ children }: any) => <div>{children}</div>,
  Space: ({ children }: any) => <span>{children}</span>,
  Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
  message: { error: (...args: any[]) => _messageError(...args), success: vi.fn() },
}))

import ReportsCenter from '@/pages/ReportsCenter'

function renderReportsCenter() {
  return render(
    <MemoryRouter initialEntries={['/reports']}>
      <Routes>
        <Route path="/reports" element={<ReportsCenter />} />
      </Routes>
    </MemoryRouter>,
  )
}

const mockSummary = {
  success: true,
  data: {
    total_amount: '10000.50',
    total_cost: '6000.00',
    gross_profit: '4000.50',
    gross_margin: '40.00',
    order_count: 25,
    period: '30d',
    start_date: '2026-04-02',
    end_date: '2026-05-02',
  },
}

const mockTrend = {
  success: true,
  data: {
    items: [
      { date: '2026-05-01', amount: '5000.00', order_count: 10 },
      { date: '2026-05-02', amount: '3000.00', order_count: 8 },
    ],
    period: '30d',
  },
}

const mockProducts = {
  success: true,
  data: {
    items: [
      { rank: 1, product_id: 'p-1', product_name: '商品A', sku: 'SKU-001', total_sales: '5000', total_cost: '3000', total_quantity: 50 },
    ],
    period: '30d',
  },
}

const mockCustomers = {
  success: true,
  data: {
    items: [
      { rank: 1, customer_id: 'c-1', customer_name: '客户X', total_sales: '8000', total_cost: '4800', gross_profit: '3200', order_count: 15 },
    ],
    period: '30d',
  },
}

const mockSalespersons = {
  success: true,
  data: {
    items: [
      { rank: 1, user_id: 'u-1', name: '销售员A', total_sales: '9000', total_cost: '5400', gross_profit: '3600', order_count: 20 },
    ],
    period: '30d',
  },
}

const mockInventory = {
  success: true,
  data: {
    items: [
      { id: 'inv-1', sku: 'SKU-002', name: '低库存商品', stock_quantity: 3, sale_price: '100.00' },
    ],
    threshold: 10,
    total: 1,
  },
}

describe('ReportsCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _reportMocks.fetchSalesSummary.mockResolvedValue(mockSummary)
    _reportMocks.fetchSalesTrend.mockResolvedValue(mockTrend)
    _reportMocks.fetchProductRanking.mockResolvedValue(mockProducts)
    _reportMocks.fetchCustomerRanking.mockResolvedValue(mockCustomers)
    _reportMocks.fetchSalespersonRanking.mockResolvedValue(mockSalespersons)
    _reportMocks.fetchInventoryWarning.mockResolvedValue(mockInventory)
  })

  it('渲染页面标题和周期选择器', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByText('报表中心')).toBeInTheDocument()
      expect(screen.getByTestId('select')).toBeInTheDocument()
    })
  })

  it('渲染五个标签页', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByTestId('tab-summary')).toHaveTextContent('销售概览')
      expect(screen.getByTestId('tab-products')).toHaveTextContent('商品排行')
      expect(screen.getByTestId('tab-customers')).toHaveTextContent('客户排行')
      expect(screen.getByTestId('tab-salespersons')).toHaveTextContent('销售排行')
      expect(screen.getByTestId('tab-inventory')).toHaveTextContent('库存预警')
    })
  })

  it('显示销售概览统计卡片', async () => {
    renderReportsCenter()
    await waitFor(() => {
      const stats = screen.getAllByTestId('statistic')
      const titles = stats.map((s) => s.getAttribute('data-title'))
      expect(titles).toContain('销售总额')
      expect(titles).toContain('订单数')
      expect(titles).toContain('总成本')
      expect(titles).toContain('毛利')
    })
  })

  it('渲染销售趋势表格', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByTestId('row-2026-05-01')).toBeInTheDocument()
      expect(screen.getByText('2026-05-01')).toBeInTheDocument()
    })
  })

  it('渲染商品排行表格', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByText('商品A')).toBeInTheDocument()
      expect(screen.getByText('SKU-001')).toBeInTheDocument()
    })
  })

  it('所有 API 使用默认周期 30d 调用', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(_reportMocks.fetchSalesSummary).toHaveBeenCalledWith('30d')
      expect(_reportMocks.fetchSalesTrend).toHaveBeenCalledWith('30d')
      expect(_reportMocks.fetchProductRanking).toHaveBeenCalledWith({ period: '30d', limit: 20 })
      expect(_reportMocks.fetchCustomerRanking).toHaveBeenCalledWith({ period: '30d', limit: 20 })
      expect(_reportMocks.fetchSalespersonRanking).toHaveBeenCalledWith({ period: '30d', limit: 20 })
      expect(_reportMocks.fetchInventoryWarning).toHaveBeenCalledWith()
    })
  })

  it('库存预警显示库存数量标签', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByTestId('row-inv-1')).toBeInTheDocument()
      const tags = screen.getAllByTestId('tag')
      const stockTag = tags.find((t) => t.textContent === '3')
      expect(stockTag).toBeTruthy()
    })
  })

  it('加载概览失败显示错误提示', async () => {
    _reportMocks.fetchSalesSummary.mockRejectedValue(new Error('network'))
    renderReportsCenter()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载销售概览失败')
    })
  })

  it('渲染客户排行表格数据', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByText('客户X')).toBeInTheDocument()
    })
  })

  it('渲染销售排行表格数据', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByText('销售员A')).toBeInTheDocument()
    })
  })

  it('切换周期选择器触发新的数据加载', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(_reportMocks.fetchSalesSummary).toHaveBeenCalledWith('30d')
    })
    const select = screen.getByTestId('select')
    fireEvent.change(select, { target: { value: '7d' } })
    await waitFor(() => {
      expect(_reportMocks.fetchSalesSummary).toHaveBeenCalledWith('7d')
    })
  })

  it('周期选择器包含正确标签', async () => {
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByTestId('select')).toBeInTheDocument()
    })
    const select = screen.getByTestId('select')
    const optionTexts = Array.from(select.querySelectorAll('option')).map((o) => o.textContent)
    expect(optionTexts).toContain('今日')
    expect(optionTexts).toContain('近7天')
    expect(optionTexts).toContain('近30天')
    expect(optionTexts).toContain('本月')
  })

  it('无排行数据时显示空状态', async () => {
    _reportMocks.fetchProductRanking.mockResolvedValue({
      success: true,
      data: { items: [], period: '30d' },
    })
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByText('暂无商品排行数据')).toBeInTheDocument()
    })
  })

  it('客户排行加载失败显示错误提示', async () => {
    _reportMocks.fetchCustomerRanking.mockRejectedValue(new Error('network'))
    renderReportsCenter()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载客户排行失败')
    })
  })

  it('销售排行加载失败显示错误提示', async () => {
    _reportMocks.fetchSalespersonRanking.mockRejectedValue(new Error('network'))
    renderReportsCenter()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载销售排行失败')
    })
  })

  it('趋势数据为空时显示空状态', async () => {
    _reportMocks.fetchSalesTrend.mockResolvedValue({
      success: true,
      data: { items: [], period: '30d' },
    })
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByText('暂无趋势数据')).toBeInTheDocument()
    })
  })

  it('库存预警无数据时显示空状态', async () => {
    _reportMocks.fetchInventoryWarning.mockResolvedValue({
      success: true,
      data: { items: [], threshold: 10, total: 0 },
    })
    renderReportsCenter()
    await waitFor(() => {
      expect(screen.getByText('暂无库存预警')).toBeInTheDocument()
    })
  })

  it('销售趋势加载失败显示错误提示', async () => {
    _reportMocks.fetchSalesTrend.mockRejectedValue(new Error('network'))
    renderReportsCenter()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载销售趋势失败')
    })
  })

  it('商品排行加载失败显示错误提示', async () => {
    _reportMocks.fetchProductRanking.mockRejectedValue(new Error('network'))
    renderReportsCenter()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载商品排行失败')
    })
  })

  it('库存预警加载失败显示错误提示', async () => {
    _reportMocks.fetchInventoryWarning.mockRejectedValue(new Error('network'))
    renderReportsCenter()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载库存预警失败')
    })
  })
})
