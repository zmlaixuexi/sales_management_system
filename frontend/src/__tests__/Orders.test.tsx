/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

vi.mock('@/api/orders', () => ({
  fetchOrders: vi.fn(),
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
  formatPercent: (v: any) => `${v}%`,
}))

vi.mock('@/api/request', () => ({
  downloadCsv: vi.fn(),
}))

const _paginatedListReturn = {
  data: [
    { id: 'o1', order_no: 'ORD-20260501-001', status: 'draft', item_count: 3, total_amount: '1000', paid_amount: '0', gross_profit: '400', gross_margin: '40', created_at: '2026-05-01T10:00:00Z' },
    { id: 'o2', order_no: 'ORD-20260501-002', status: 'completed', item_count: 1, total_amount: '500', paid_amount: '500', gross_profit: '200', gross_margin: '40', created_at: '2026-05-01T12:00:00Z' },
    { id: 'o3', order_no: 'ORD-20260501-003', status: 'cancelled', item_count: 2, total_amount: '300', paid_amount: '0', gross_profit: '0', gross_margin: '0', created_at: null },
  ],
  total: 3,
  loading: false,
  error: false,
  page: 1,
  pageSize: 10,
  keyword: '',
  setPage: vi.fn(),
  setKeyword: vi.fn(),
  onPageChange: vi.fn(),
  refresh: vi.fn(),
}

vi.mock('@/hooks/usePaginatedList', () => ({
  usePaginatedList: () => _paginatedListReturn,
}))

vi.mock('antd', () => ({
  Table: ({ dataSource, columns, rowKey, locale }: any) => (
    <table data-testid="orders-table">
      <thead>
        <tr>{columns?.map((col: any) => <th key={col.dataIndex || col.title}>{col.title}</th>)}</tr>
      </thead>
      <tbody>
        {dataSource?.length ? dataSource.map((row: any) => (
          <tr key={row[rowKey]} data-testid={`row-${row[rowKey]}`}>
            {columns?.map((col: any) => (
              <td key={col.dataIndex} data-col={col.dataIndex}>
                {col.render ? col.render(row[col.dataIndex], row) : row[col.dataIndex]}
              </td>
            ))}
          </tr>
        )) : (
          <tr><td colSpan={99}>{typeof locale?.emptyText === 'string' ? locale.emptyText : locale?.emptyText}</td></tr>
        )}
      </tbody>
    </table>
  ),
  Button: ({ children, onClick, icon, type }: any) => (
    <button data-testid="button" data-type={type} onClick={onClick}>{icon}{children}</button>
  ),
  Input: ({ value, onChange, placeholder }: any) => (
    <input data-testid="search-input" placeholder={placeholder} value={value || ''} onChange={(e: any) => onChange?.(e)} />
  ),
  Select: ({ value, onChange, options, placeholder }: any) => (
    <select data-testid="status-select" value={value || ''} onChange={(e: any) => onChange?.(e.target.value)}>
      <option value="">{placeholder || '全部'}</option>
      {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
  message: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span>+</span>,
  SearchOutlined: () => <span>🔍</span>,
  EyeOutlined: () => <span>👁️</span>,
  DownloadOutlined: () => <span>📥</span>,
}))

import OrdersPage from '@/pages/Orders'

function renderOrders() {
  return render(
    <MemoryRouter initialEntries={['/orders']}>
      <Routes>
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/orders/:id" element={<div>Order Detail</div>} />
        <Route path="/orders/new" element={<div>New Order</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('OrdersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染搜索输入和状态筛选器', () => {
    renderOrders()
    expect(screen.getByTestId('search-input')).toBeInTheDocument()
    expect(screen.getByTestId('status-select')).toBeInTheDocument()
  })

  it('渲染新建订单按钮', () => {
    renderOrders()
    expect(screen.getByText('新建订单')).toBeInTheDocument()
  })

  it('渲染订单数据表格', () => {
    renderOrders()
    const table = screen.getByTestId('orders-table')
    expect(table).toBeInTheDocument()
    expect(screen.getByTestId('row-o1')).toBeInTheDocument()
    expect(screen.getByTestId('row-o2')).toBeInTheDocument()
  })

  it('订单行显示订单号和明细数', () => {
    renderOrders()
    expect(screen.getByText('ORD-20260501-001')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('ORD-20260501-002')).toBeInTheDocument()
  })

  it('状态标签正确渲染', () => {
    renderOrders()
    const tags = screen.getAllByTestId('tag')
    const tagTexts = tags.map((t) => t.textContent)
    expect(tagTexts).toContain('草稿')
    expect(tagTexts).toContain('已完成')
    expect(tagTexts).toContain('已取消')
  })

  it('金额字段带货币符号', () => {
    renderOrders()
    const row1 = screen.getByTestId('row-o1')
    expect(row1.textContent).toContain('¥1000')
    expect(row1.textContent).toContain('¥0')
    expect(row1.textContent).toContain('¥400')
  })

  it('空创建时间显示占位符', () => {
    renderOrders()
    const row3 = screen.getByTestId('row-o3')
    expect(row3.textContent).toContain('--')
  })

  it('表格列包含必要字段', () => {
    renderOrders()
    const table = screen.getByTestId('orders-table')
    const headerTexts = Array.from(table.querySelectorAll('th')).map((th) => th.textContent)
    expect(headerTexts).toContain('订单号')
    expect(headerTexts).toContain('状态')
    expect(headerTexts).toContain('明细数')
    expect(headerTexts).toContain('订单金额')
    expect(headerTexts).toContain('已收金额')
    expect(headerTexts).toContain('操作')
  })

  it('无数据时显示空状态提示', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0 })
    renderOrders()
    expect(screen.getByText('暂无订单，点击"新建订单"添加')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: 'o1', order_no: 'ORD-20260501-001', status: 'draft', item_count: 3, total_amount: '1000', paid_amount: '0', gross_profit: '400', gross_margin: '40', created_at: '2026-05-01T10:00:00Z' },
      { id: 'o2', order_no: 'ORD-20260501-002', status: 'completed', item_count: 1, total_amount: '500', paid_amount: '500', gross_profit: '200', gross_margin: '40', created_at: '2026-05-01T12:00:00Z' },
      { id: 'o3', order_no: 'ORD-20260501-003', status: 'cancelled', item_count: 2, total_amount: '300', paid_amount: '0', gross_profit: '0', gross_margin: '0', created_at: null },
    ]
    _paginatedListReturn.total = 3
  })
})
