/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _orderMocks = {
  fetchOrder: vi.fn(),
  confirmOrder: vi.fn(),
  cancelOrder: vi.fn(),
}
const _paymentMocks = {
  createPayment: vi.fn(),
  reversePayment: vi.fn(),
}

vi.mock('@/api/orders', () => ({
  fetchOrder: (...args: any[]) => _orderMocks.fetchOrder(...args),
  confirmOrder: (...args: any[]) => _orderMocks.confirmOrder(...args),
  cancelOrder: (...args: any[]) => _orderMocks.cancelOrder(...args),
}))

vi.mock('@/api/payments', () => ({
  createPayment: (...args: any[]) => _paymentMocks.createPayment(...args),
  reversePayment: (...args: any[]) => _paymentMocks.reversePayment(...args),
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
  formatPercent: (v: any) => `${v}%`,
  getApiErrorMessage: (_e: any, fallback: string) => fallback,
}))

const _messageError = vi.fn()
vi.mock('antd', () => ({
  Card: ({ title, children }: any) => (
    <div data-testid="card" data-title={title}>{children}</div>
  ),
  Descriptions: Object.assign(
    ({ children }: any) => <div data-testid="descriptions">{children}</div>,
    { Item: ({ children, label }: any) => <div data-testid="desc-item" data-label={label}>{children}</div> },
  ),
  Table: ({ dataSource, columns, rowKey, footer }: any) => (
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
      {footer && <div data-testid="table-footer">{footer()}</div>}
    </div>
  ),
  Button: ({ children, onClick, icon, type, danger, disabled }: any) => (
    <button data-testid="button" data-type={type} data-danger={danger ? 'true' : undefined} disabled={disabled} onClick={onClick}>{icon}{children}</button>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
  Popconfirm: ({ title, children }: any) => (
    <span data-testid="popconfirm" data-title={title}>{children}</span>
  ),
  InputNumber: ({ value, onChange }: any) => (
    <input data-testid="input-number" value={value} onChange={(e: any) => onChange?.(parseFloat(e.target.value))} />
  ),
  Select: ({ value, onChange, options }: any) => (
    <select data-testid="select" value={value} onChange={(e: any) => onChange?.(e.target.value)}>
      {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  ),
  Input: ({ value, onChange, placeholder }: any) => (
    <input data-testid="input" value={value || ''} placeholder={placeholder} onChange={(e: any) => onChange?.(e)} />
  ),
  Image: ({ src }: any) => <img data-testid="image" src={src} />,
  Modal: ({ title, children, open }: any) => open ? <div data-testid="modal" data-title={title}>{children}</div> : null,
  message: { error: (...args: any[]) => _messageError(...args), success: vi.fn() },
}))

vi.mock('@ant-design/icons', () => ({
  ArrowLeftOutlined: () => <span>←</span>,
  EditOutlined: () => <span>✏️</span>,
  DollarOutlined: () => <span>$</span>,
}))

const mockOrderData = {
  success: true,
  data: {
    id: 'order-1',
    order_no: 'ORD-20260501-001',
    status: 'draft',
    total_amount: '1000',
    total_cost: '600',
    gross_profit: '400',
    gross_margin: '40',
    paid_amount: '0',
    created_at: '2026-05-01T10:00:00Z',
    remark: '测试订单备注',
    items: [
      { id: 'item-1', product_name_snapshot: '商品A', product_sku_snapshot: 'SKU-001', quantity: 2, unit_price: '500', discount_amount: '0', subtotal_amount: '1000', product_image_url_snapshot: null },
    ],
    payments: [
      { id: 'pay-1', amount: '500', payment_method: 'cash', paid_at: '2026-05-01T12:00:00Z', remark: '首笔' },
    ],
  },
}

import OrderDetail from '@/pages/OrderDetail'

function renderOrderDetail() {
  return render(
    <MemoryRouter initialEntries={['/orders/order-1']}>
      <Routes>
        <Route path="/orders/:id" element={<OrderDetail />} />
        <Route path="/orders" element={<div>Orders List</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('OrderDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _orderMocks.fetchOrder.mockResolvedValue(mockOrderData)
  })

  it('加载并显示订单号', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
  })

  it('显示返回列表按钮', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('返回列表')).toBeInTheDocument()
    })
  })

  it('草稿订单显示编辑和确认按钮', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
      expect(screen.getByText('确认订单')).toBeInTheDocument()
    })
  })

  it('显示订单状态标签', async () => {
    renderOrderDetail()
    await waitFor(() => {
      const tags = screen.getAllByTestId('tag')
      const tagTexts = tags.map((t) => t.textContent)
      expect(tagTexts).toContain('草稿')
    })
  })

  it('渲染订单明细表格', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByTestId('row-item-1')).toBeInTheDocument()
      expect(screen.getByText('商品A')).toBeInTheDocument()
      expect(screen.getByText('SKU-001')).toBeInTheDocument()
    })
  })

  it('渲染收款记录表格', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByTestId('row-pay-1')).toBeInTheDocument()
      expect(screen.getByText('现金')).toBeInTheDocument()
    })
  })

  it('fetchOrder 使用正确 ID 调用', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(_orderMocks.fetchOrder).toHaveBeenCalledWith('order-1')
    })
  })

  it('加载失败显示错误提示', async () => {
    _orderMocks.fetchOrder.mockRejectedValue(new Error('network'))
    renderOrderDetail()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载订单详情失败')
    })
  })
})
