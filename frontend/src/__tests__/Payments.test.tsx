/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _paymentMocks = {
  fetchPayments: vi.fn(),
}

const _paginatedListReturn: any = {
  data: [],
  total: 0,
  loading: false,
  error: false,
  page: 1,
  pageSize: 20,
  onPageChange: vi.fn(),
  refresh: vi.fn(),
}

vi.mock('@/hooks/usePaginatedList', () => ({
  usePaginatedList: (_fetchFn: any, _filters: any, _errorMsg: string) => {
    const result = _paymentMocks.fetchPayments()
    _paginatedListReturn.data = result?.data?.items ?? []
    _paginatedListReturn.total = result?.data?.total ?? 0
    return _paginatedListReturn
  },
}))

vi.mock('@/api/payments', () => ({
  fetchPayments: (...args: any[]) => _paymentMocks.fetchPayments(...args),
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
}))

vi.mock('antd', () => ({
  Table: ({ dataSource, columns, rowKey, locale, loading }: any) => (
    <div>
      {loading ? <span>加载中...</span> : (
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
      )}
      {(!dataSource || dataSource.length === 0) && !loading && locale?.emptyText && <span>{locale.emptyText}</span>}
    </div>
  ),
  Button: ({ children, onClick, type }: any) => (
    <button data-testid="button" data-type={type} onClick={onClick}>{children}</button>
  ),
  Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
  Space: ({ children }: any) => <span>{children}</span>,
  message: { error: vi.fn(), success: vi.fn() },
}))

import PaymentsPage from '@/pages/Payments'

const mockPaymentsData = {
  data: {
    items: [
      {
        id: 'pay-001-abcdef',
        order_id: 'order-001-ghijkl',
        amount: '5000.00',
        payment_method: 'cash',
        status: 'normal',
        remark: '首笔收款',
        paid_at: '2026-05-01T12:00:00Z',
        created_at: '2026-05-01T12:00:00Z',
      },
      {
        id: 'pay-002-mnopqr',
        order_id: 'order-002-stuvwx',
        amount: '3000.00',
        payment_method: 'wechat',
        status: 'reversed',
        remark: null,
        paid_at: null,
        created_at: '2026-05-01T14:00:00Z',
      },
    ],
    total: 2,
  },
}

function renderPayments() {
  return render(
    <MemoryRouter initialEntries={['/payments']}>
      <Routes>
        <Route path="/payments" element={<PaymentsPage />} />
        <Route path="/orders/:id" element={<div>Order Detail</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PaymentsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _paymentMocks.fetchPayments.mockReturnValue(mockPaymentsData)
  })

  it('渲染页面标题', () => {
    renderPayments()
    expect(screen.getByText('收款记录')).toBeInTheDocument()
  })

  it('显示总记录数', () => {
    renderPayments()
    expect(screen.getByText(/共 2 条记录/)).toBeInTheDocument()
  })

  it('渲染收款数据行', () => {
    renderPayments()
    expect(screen.getByTestId('row-pay-001-abcdef')).toBeInTheDocument()
    expect(screen.getByTestId('row-pay-002-mnopqr')).toBeInTheDocument()
  })

  it('显示金额格式化', () => {
    renderPayments()
    expect(screen.getByText('¥5000.00')).toBeInTheDocument()
    expect(screen.getByText('¥3000.00')).toBeInTheDocument()
  })

  it('显示收款方式中文', () => {
    renderPayments()
    expect(screen.getByText('现金')).toBeInTheDocument()
    expect(screen.getByText('微信')).toBeInTheDocument()
  })

  it('显示状态标签', () => {
    renderPayments()
    const tags = screen.getAllByTestId('tag')
    const tagTexts = tags.map((t) => t.textContent)
    expect(tagTexts).toContain('正常')
    expect(tagTexts).toContain('已冲正')
  })

  it('订单 ID 可点击跳转', () => {
    renderPayments()
    const buttons = screen.getAllByTestId('button')
    const orderLink = buttons.find((b) => b.textContent?.includes('order-00'))
    expect(orderLink).toBeTruthy()
  })

  it('无数据时显示空状态', () => {
    _paymentMocks.fetchPayments.mockReturnValue({ data: { items: [], total: 0 } })
    renderPayments()
    expect(screen.getByText('暂无收款记录')).toBeInTheDocument()
  })

  it('加载中显示加载提示', () => {
    _paginatedListReturn.loading = true
    _paginatedListReturn.data = []
    _paymentMocks.fetchPayments.mockReturnValue({ data: { items: [], total: 0 } })
    renderPayments()
    expect(screen.getByText('加载中...')).toBeInTheDocument()
    _paginatedListReturn.loading = false
  })

  it('错误状态显示重试链接', () => {
    _paginatedListReturn.loading = false
    _paginatedListReturn.error = true
    _paginatedListReturn.data = []
    _paymentMocks.fetchPayments.mockReturnValue({ data: { items: [], total: 0 } })
    renderPayments()
    expect(screen.getByText('重试')).toBeInTheDocument()
    _paginatedListReturn.error = false
  })

  it('收款 ID 截断显示前 8 位', () => {
    renderPayments()
    expect(screen.getByText('pay-001-')).toBeInTheDocument()
  })

  it('空备注显示为 --', () => {
    renderPayments()
    const row = screen.getByTestId('row-pay-002-mnopqr')
    expect(row.textContent).toContain('--')
  })

  it('渲染导出按钮', () => {
    renderPayments()
    expect(screen.getByText('导出')).toBeInTheDocument()
  })
})
