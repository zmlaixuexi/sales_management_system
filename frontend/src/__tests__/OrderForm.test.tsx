/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _orderApi = {
  fetchOrder: vi.fn(),
  createOrder: vi.fn(),
  updateOrder: vi.fn(),
}

vi.mock('@/api/orders', () => ({
  fetchOrder: (...a: any[]) => _orderApi.fetchOrder(...a),
  createOrder: (...a: any[]) => _orderApi.createOrder(...a),
  updateOrder: (...a: any[]) => _orderApi.updateOrder(...a),
}))

vi.mock('@/api/customers', () => ({
  fetchCustomers: vi.fn().mockResolvedValue({ success: true, data: { items: [] } }),
}))

vi.mock('@/api/products', () => ({
  fetchProducts: vi.fn().mockResolvedValue({ success: true, data: { items: [] } }),
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
}))

vi.mock('@/hooks/useSubmit', () => ({
  useSubmit: (onSubmit: any) => ({
    submitting: false,
    handleSubmit: onSubmit,
  }),
}))

const _mockForm = {
  setFieldsValue: vi.fn(),
  getFieldsValue: vi.fn(() => ({})),
  validateFields: vi.fn(() => Promise.resolve({})),
  resetFields: vi.fn(),
}

vi.mock('antd', () => ({
  Form: Object.assign(
    ({ children, onFinish, initialValues }: any) => (
      <form data-testid="form" onSubmit={(e) => { e.preventDefault(); onFinish?.(initialValues || {}) }}>
        {children}
      </form>
    ),
    {
      Item: ({ children, label, name }: any) => (
        <div data-testid="form-item" data-label={label} data-name={name}>{children}</div>
      ),
      useForm: () => [_mockForm],
    },
  ),
  Input: Object.assign(
    (props: any) => <input data-testid="input" {...props} />,
    { TextArea: (props: any) => <textarea data-testid="textarea" {...props} /> },
  ),
  InputNumber: (props: any) => <input data-testid="input-number" type="number" {...props} />,
  Button: ({ children, onClick, icon, type, danger, disabled }: any) => (
    <button data-testid="button" data-type={type} data-danger={danger ? 'true' : undefined} disabled={disabled} onClick={onClick}>{icon}{children}</button>
  ),
  Card: ({ title, children, loading, extra }: any) => (
    <div data-testid="card" data-title={title}>{extra}{children}</div>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Table: ({ dataSource, columns, rowKey, footer }: any) => (
    <div>
      <table data-testid="table">
        <tbody>
          {dataSource?.map((row: any) => (
            <tr key={row[rowKey]} data-testid={`row-${row[rowKey]}`}>
              {columns?.map((col: any) => (
                <td key={col.dataIndex}>{col.render ? col.render(row[col.dataIndex], row) : row[col.dataIndex]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {footer && <div data-testid="table-footer">{footer()}</div>}
    </div>
  ),
  Select: Object.assign(
    ({ children, placeholder, value, onChange }: any) => (
      <select data-testid="select" value={value} onChange={(e: any) => onChange?.(e.target.value)}>
        <option value="">{placeholder}</option>
        {children}
      </select>
    ),
    { Option: ({ children, value }: any) => <option value={value}>{children}</option> },
  ),
  Image: ({ src }: any) => <img data-testid="image" src={src} />,
  message: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
}))

vi.mock('@ant-design/icons', () => ({
  ArrowLeftOutlined: () => <span>←</span>,
  PlusOutlined: () => <span>+</span>,
  DeleteOutlined: () => <span>🗑️</span>,
  SearchOutlined: () => <span>🔍</span>,
}))

import OrderForm from '@/pages/OrderForm'

function renderNewOrder() {
  return render(
    <MemoryRouter initialEntries={['/orders/new']}>
      <Routes>
        <Route path="/orders/new" element={<OrderForm />} />
        <Route path="/orders" element={<div>Orders List</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('OrderForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('新建模式渲染"新建订单"标题', () => {
    renderNewOrder()
    const cards = screen.getAllByTestId('card')
    expect(cards[0].getAttribute('data-title')).toBe('新建订单')
  })

  it('渲染返回列表按钮', () => {
    renderNewOrder()
    expect(screen.getByText('返回列表')).toBeInTheDocument()
  })

  it('渲染客户选择字段', () => {
    renderNewOrder()
    const customerItem = screen.getAllByTestId('form-item').find(
      (fi) => fi.getAttribute('data-name') === 'customer_id',
    )
    expect(customerItem).toBeTruthy()
  })

  it('渲染添加商品按钮', () => {
    renderNewOrder()
    expect(screen.getByText('添加商品')).toBeInTheDocument()
  })

  it('渲染创建订单按钮', () => {
    renderNewOrder()
    expect(screen.getByText('创建订单')).toBeInTheDocument()
  })

  it('渲染取消按钮', () => {
    renderNewOrder()
    expect(screen.getByText('取消')).toBeInTheDocument()
  })

  it('渲染备注字段', () => {
    renderNewOrder()
    const remarkItem = screen.getAllByTestId('form-item').find(
      (fi) => fi.getAttribute('data-name') === 'remark',
    )
    expect(remarkItem).toBeTruthy()
  })

  it('新建模式不调用 fetchOrder', () => {
    renderNewOrder()
    expect(_orderApi.fetchOrder).not.toHaveBeenCalled()
  })
})
