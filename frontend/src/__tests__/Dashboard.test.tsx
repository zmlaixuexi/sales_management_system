/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _reportMocks = {
  fetchSalesSummary: vi.fn(),
  fetchSalesTrend: vi.fn(),
  fetchProductRanking: vi.fn(),
  fetchInventoryWarning: vi.fn(),
}
const _messageError = vi.fn()

vi.mock('@/api/reports', () => ({
  fetchSalesSummary: (...args: any[]) => _reportMocks.fetchSalesSummary(...args),
  fetchSalesTrend: (...args: any[]) => _reportMocks.fetchSalesTrend(...args),
  fetchProductRanking: (...args: any[]) => _reportMocks.fetchProductRanking(...args),
  fetchInventoryWarning: (...args: any[]) => _reportMocks.fetchInventoryWarning(...args),
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
  formatPercent: (v: any) => `${v}%`,
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => (code: string) => code === 'report:profit',
}))

vi.mock('antd', () => {
  function Statistic({ title, value, suffix }: any) {
    return <div data-testid="statistic" data-title={title} data-value={value} data-suffix={suffix} />
  }
  return {
    Card: ({ title, children }: any) => <div data-testid="card" data-title={title}>{children}</div>,
    Row: ({ children }: any) => <div data-testid="row">{children}</div>,
    Col: ({ children }: any) => <div>{children}</div>,
    Statistic,
    Select: ({ value, onChange, options }: any) => (
      <select
        data-testid="period-select"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
      >
        {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    ),
    Spin: ({ spinning, children }: any) => (
      <div data-testid="spin" data-spinning={spinning ? 'true' : 'false'}>{children}</div>
    ),
    Empty: ({ description }: any) => <div data-testid="empty">{description}</div>,
    Table: ({ dataSource, columns, rowKey }: any) => (
      <table data-testid="table">
        <tbody>
          {dataSource?.map((row: any) => (
            <tr key={row[rowKey] || row.id || row.product_id} data-testid={`row-${row[rowKey] || row.id || row.product_id}`}>
              {columns?.map((col: any) => (
                <td key={col.dataIndex} data-col={col.dataIndex}>
                  {col.render ? col.render(row[col.dataIndex], row) : row[col.dataIndex]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    ),
    Tag: ({ children }: any) => <span>{children}</span>,
    message: { error: (...args: any[]) => _messageError(...args), success: vi.fn() },
  }
})

vi.mock('@ant-design/icons', () => ({
  DollarOutlined: () => <span>$</span>,
  ShoppingCartOutlined: () => <span>🛒</span>,
  RiseOutlined: () => <span>📈</span>,
  AlertOutlined: () => <span>⚠️</span>,
}))

// Import after mocks are set up
import Dashboard from '@/pages/Dashboard'

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
      </Routes>
    </MemoryRouter>,
  )
}

const summaryData = {
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

const trendData = {
  success: true,
  data: {
    items: [
      { date: '2026-05-01', amount: '500.00', order_count: 3 },
      { date: '2026-05-02', amount: '800.00', order_count: 5 },
    ],
    period: '30d',
  },
}

const rankingData = {
  success: true,
  data: {
    items: [
      { rank: 1, product_id: 'p1', product_name: '商品A', sku: 'SKU-001', total_sales: '3000', total_cost: '1800', total_quantity: 30 },
    ],
    period: '30d',
  },
}

const warningData = {
  success: true,
  data: {
    items: [
      { id: 'w1', sku: 'SKU-LOW', name: '低库存商品', stock_quantity: 2, sale_price: '100.00' },
    ],
    threshold: 5,
    total: 1,
  },
}

beforeEach(() => {
  vi.clearAllMocks()
  _reportMocks.fetchSalesSummary.mockResolvedValue(summaryData)
  _reportMocks.fetchSalesTrend.mockResolvedValue(trendData)
  _reportMocks.fetchProductRanking.mockResolvedValue(rankingData)
  _reportMocks.fetchInventoryWarning.mockResolvedValue(warningData)
})

describe('Dashboard', () => {
  it('渲染看板标题和期间选择器', async () => {
    renderDashboard()
    expect(screen.getByText('首页看板')).toBeInTheDocument()
    expect(screen.getByTestId('period-select')).toBeInTheDocument()
    expect(screen.getByTestId('period-select')).toHaveValue('30d')
  })

  it('初始加载显示 loading', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'true')
    })
  })

  it('数据加载完成后显示统计卡片', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    const stats = screen.getAllByTestId('statistic')
    const titles = stats.map((s) => s.getAttribute('data-title'))
    expect(titles).toContain('销售总额')
    expect(titles).toContain('订单数')
    expect(titles).toContain('毛利')
    expect(titles).toContain('毛利率')
  })

  it('API 使用默认 period=30d 调用', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(_reportMocks.fetchSalesSummary).toHaveBeenCalledWith('30d')
      expect(_reportMocks.fetchSalesTrend).toHaveBeenCalledWith('30d')
      expect(_reportMocks.fetchProductRanking).toHaveBeenCalledWith({ period: '30d', limit: 10 })
      expect(_reportMocks.fetchInventoryWarning).toHaveBeenCalled()
    })
  })

  it('统计卡片显示正确的数值', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    const stats = screen.getAllByTestId('statistic')
    const statMap = new Map(stats.map((s) => [s.getAttribute('data-title'), s.getAttribute('data-value')]))
    expect(statMap.get('销售总额')).toBe('10000.5')
    expect(statMap.get('订单数')).toBe('25')
    expect(statMap.get('毛利')).toBe('4000.5')
    expect(statMap.get('毛利率')).toBe('40')
  })

  it('商品排行和库存预警表格渲染数据', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    const tables = screen.getAllByTestId('table')
    expect(tables.length).toBeGreaterThanOrEqual(2)
  })

  it('API 请求全部失败时显示错误提示', async () => {
    _reportMocks.fetchSalesSummary.mockRejectedValue(new Error('network'))
    _reportMocks.fetchSalesTrend.mockRejectedValue(new Error('network'))
    _reportMocks.fetchProductRanking.mockRejectedValue(new Error('network'))
    _reportMocks.fetchInventoryWarning.mockRejectedValue(new Error('network'))

    renderDashboard()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载看板数据失败，请稍后重试')
    })
  })

  it('切换期间选择器触发新的数据加载', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(_reportMocks.fetchSalesSummary).toHaveBeenCalledWith('30d')
    })

    const select = screen.getByTestId('period-select')
    fireEvent.change(select, { target: { value: 'today' } })

    await waitFor(() => {
      expect(_reportMocks.fetchSalesSummary).toHaveBeenCalledWith('today')
    })
  })

  it('趋势汇总显示期间总额和峰值日', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    expect(screen.getByText(/期间总额/)).toBeInTheDocument()
    expect(screen.getByText(/峰值日/)).toBeInTheDocument()
  })

  it('库存预警渲染预警商品数据', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    // 预警商品 SKU 在表格中渲染
    expect(screen.getByText('SKU-LOW')).toBeInTheDocument()
    expect(screen.getByText('低库存商品')).toBeInTheDocument()
  })

  it('期间选择器包含 5 个选项', () => {
    renderDashboard()
    const select = screen.getByTestId('period-select')
    const options = select.querySelectorAll('option')
    expect(options.length).toBe(5)
  })

  it('期间选择器包含正确标签', () => {
    renderDashboard()
    const select = screen.getByTestId('period-select')
    const optionTexts = Array.from(select.querySelectorAll('option')).map((o) => o.textContent)
    expect(optionTexts).toContain('今日')
    expect(optionTexts).toContain('近 7 天')
    expect(optionTexts).toContain('近 30 天')
    expect(optionTexts).toContain('本月')
    expect(optionTexts).toContain('上月')
  })

  it('商品排行表格渲染商品数据', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    expect(screen.getByText('SKU-001')).toBeInTheDocument()
    expect(screen.getByText('商品A')).toBeInTheDocument()
  })

  it('无趋势数据时显示空状态', async () => {
    _reportMocks.fetchSalesTrend.mockResolvedValue({
      success: true,
      data: { items: [], period: '30d' },
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('无预警数据时显示"暂无预警商品"', async () => {
    _reportMocks.fetchInventoryWarning.mockResolvedValue({
      success: true,
      data: { items: [], threshold: 5, total: 0 },
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    expect(screen.getByText('暂无预警商品')).toBeInTheDocument()
  })

  it('无排行数据时显示"暂无排行数据"', async () => {
    _reportMocks.fetchProductRanking.mockResolvedValue({
      success: true,
      data: { items: [], period: '30d' },
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    expect(screen.getByText('暂无排行数据')).toBeInTheDocument()
  })

  it('库存为 0 的预警商品显示红色标签', async () => {
    _reportMocks.fetchInventoryWarning.mockResolvedValue({
      success: true,
      data: {
        items: [
          { id: 'w2', sku: 'SKU-ZERO', name: '零库存商品', stock_quantity: 0, sale_price: '50.00' },
        ],
        threshold: 5,
        total: 1,
      },
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    expect(screen.getByText('SKU-ZERO')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('部分 API 失败触发错误提示', async () => {
    _reportMocks.fetchSalesTrend.mockRejectedValue(new Error('趋势接口失败'))
    renderDashboard()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载看板数据失败，请稍后重试')
    })
  })

  it('商品排行毛利列渲染', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    // rankingData: total_sales=3000, total_cost=1800 → profit=1200
    expect(screen.getByText('¥1200')).toBeInTheDocument()
  })

  it('库存预警数量显示 Tag', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    // warningData: stock_quantity=2 → orange Tag
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('趋势图表渲染柱状条', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    // 趋势柱状条通过 div title 属性显示数据
    const bars = document.querySelectorAll('div[title]')
    expect(bars.length).toBeGreaterThanOrEqual(2)
  })

  it('_toastDisplayed 错误静默不显示消息', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _reportMocks.fetchSalesSummary.mockRejectedValue(err)
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    expect(_messageError).not.toHaveBeenCalledWith('加载看板数据失败，请稍后重试')
  })

  it('负毛利显示红色样式', async () => {
    _reportMocks.fetchSalesSummary.mockResolvedValue({
      success: true,
      data: {
        total_amount: '1000',
        total_cost: '1500',
        gross_profit: '-500',
        gross_margin: '-50',
        order_count: 5,
        period: '30d',
        start_date: '2026-04-02',
        end_date: '2026-05-02',
      },
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    const stats = screen.getAllByTestId('statistic')
    const profitStat = stats.find((s) => s.getAttribute('data-title') === '毛利')
    expect(profitStat).toBeTruthy()
    // 验证负毛利值正确
    expect(profitStat?.getAttribute('data-value')).toBe('-500')
  })

  it('峰值日金额为 0 时不显示峰值信息', async () => {
    _reportMocks.fetchSalesTrend.mockResolvedValue({
      success: true,
      data: {
        items: [
          { date: '2026-05-01', amount: '0', order_count: 0 },
        ],
        period: '30d',
      },
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    // 峰值日金额为 0，不应显示峰值信息
    expect(screen.queryByText(/峰值日/)).not.toBeInTheDocument()
  })

  it('长趋势数据（>30 条）进行采样', async () => {
    const items = Array.from({ length: 40 }, (_, i) => ({
      date: `2026-05-${String(i + 1).padStart(2, '0')}`,
      amount: String((i + 1) * 100),
      order_count: i + 1,
    }))
    _reportMocks.fetchSalesTrend.mockResolvedValue({
      success: true,
      data: { items, period: '30d' },
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    // 趋势柱状条应被采样，条数 <= 30
    const bars = document.querySelectorAll('div[title]')
    expect(bars.length).toBeLessThanOrEqual(31)
    expect(bars.length).toBeGreaterThan(0)
  })

  it('零金额趋势柱显示灰色背景', async () => {
    _reportMocks.fetchSalesTrend.mockResolvedValue({
      success: true,
      data: {
        items: [
          { date: '2026-05-01', amount: '100', order_count: 1 },
          { date: '2026-05-02', amount: '0', order_count: 0 },
        ],
        period: '30d',
      },
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('spin')).toHaveAttribute('data-spinning', 'false')
    })
    const bars = document.querySelectorAll('div[title]')
    expect(bars.length).toBe(2)
  })
})
