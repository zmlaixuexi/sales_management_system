/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _customerMocks = {
  fetchCustomer: vi.fn(),
  deleteCustomer: vi.fn(),
}
const _orderMocks = {
  fetchOrders: vi.fn(),
}

vi.mock('@/api/customers', () => ({
  fetchCustomer: (...args: any[]) => _customerMocks.fetchCustomer(...args),
  deleteCustomer: (...args: any[]) => _customerMocks.deleteCustomer(...args),
}))

vi.mock('@/api/orders', () => ({
  fetchOrders: (...args: any[]) => _orderMocks.fetchOrders(...args),
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
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
  Button: ({ children, onClick, icon, danger, loading }: any) => (
    <button data-testid="button" data-danger={danger ? 'true' : undefined} disabled={loading} onClick={onClick}>{icon}{children}</button>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
  Popconfirm: ({ title, children, onConfirm }: any) => (
    <span data-testid="popconfirm" data-title={title} onClick={onConfirm}>{children}</span>
  ),
  message: { error: (...args: any[]) => _messageError(...args), success: vi.fn() },
}))

vi.mock('@ant-design/icons', () => ({
  ArrowLeftOutlined: () => <span>←</span>,
  EditOutlined: () => <span>✏️</span>,
  DeleteOutlined: () => <span>🗑️</span>,
}))

const mockCustomerData = {
  success: true,
  data: {
    id: 'cust-1',
    name: '测试客户',
    contact_name: '张三',
    phone: '13800138000',
    email: 'test@example.com',
    source: 'referral',
    level: 'vip',
    owner_user_id: 'user-1',
    owner_name: '销售员A',
    follow_status: '跟进中',
    remark: '重要客户备注',
    created_at: '2026-05-01T10:00:00Z',
    updated_at: '2026-05-01T12:00:00Z',
  },
}

const mockOrdersData = {
  success: true,
  data: {
    items: [
      {
        id: 'order-1',
        order_no: 'ORD-20260501-001',
        status: 'completed',
        total_amount: '5000',
        created_at: '2026-05-01T14:00:00Z',
      },
    ],
    total: 1,
  },
}

import CustomerDetail from '@/pages/CustomerDetail'

function renderCustomerDetail() {
  return render(
    <MemoryRouter initialEntries={['/customers/cust-1']}>
      <Routes>
        <Route path="/customers/:id" element={<CustomerDetail />} />
        <Route path="/customers" element={<div>Customers List</div>} />
        <Route path="/customers/:id/edit" element={<div>Edit Form</div>} />
        <Route path="/orders/:id" element={<div>Order Detail</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CustomerDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _customerMocks.fetchCustomer.mockResolvedValue(mockCustomerData)
    _orderMocks.fetchOrders.mockResolvedValue(mockOrdersData)
  })

  it('加载并显示客户名称', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      const cards = screen.getAllByTestId('card')
      expect(cards[0].getAttribute('data-title')).toBe('测试客户')
    })
  })

  it('显示返回列表按钮', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('返回列表')).toBeInTheDocument()
    })
  })

  it('显示编辑和删除按钮', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
      expect(screen.getByText('删除')).toBeInTheDocument()
    })
  })

  it('显示客户等级标签', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      const tags = screen.getAllByTestId('tag')
      const tagTexts = tags.map((t) => t.textContent)
      expect(tagTexts).toContain('VIP')
    })
  })

  it('渲染关联订单表格', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByTestId('row-order-1')).toBeInTheDocument()
      expect(screen.getByText('ORD-20260501-001')).toBeInTheDocument()
    })
  })

  it('fetchCustomer 使用正确 ID 调用', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      expect(_customerMocks.fetchCustomer).toHaveBeenCalledWith('cust-1')
    })
  })

  it('fetchOrders 使用 customer_id 筛选', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      expect(_orderMocks.fetchOrders).toHaveBeenCalledWith(
        expect.objectContaining({ customer_id: 'cust-1' }),
      )
    })
  })

  it('加载失败显示错误提示', async () => {
    _customerMocks.fetchCustomer.mockRejectedValue(new Error('network'))
    renderCustomerDetail()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('加载客户详情失败')
    })
  })

  it('加载中显示加载提示', async () => {
    let resolveFn: (_v: any) => void
    _customerMocks.fetchCustomer.mockReturnValue(new Promise((r) => { resolveFn = r }))
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('加载中...')).toBeInTheDocument()
    })
    resolveFn!(mockCustomerData)
  })

  it('确认删除调用 deleteCustomer', async () => {
    _customerMocks.deleteCustomer.mockResolvedValue({ success: true })
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
    })
    const popconfirm = screen.getByTestId('popconfirm')
    popconfirm.click()
    await waitFor(() => {
      expect(_customerMocks.deleteCustomer).toHaveBeenCalledWith('cust-1')
    })
  })

  it('编辑按钮跳转到编辑页', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
    })
    const buttons = screen.getAllByTestId('button')
    const editBtn = buttons.find((b) => b.textContent?.includes('编辑'))
    editBtn!.click()
    await waitFor(() => {
      expect(screen.getByText('Edit Form')).toBeInTheDocument()
    })
  })
})
