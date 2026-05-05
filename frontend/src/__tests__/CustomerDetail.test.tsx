/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
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
  isToastDisplayed: (e: any) => !!e?._toastDisplayed,
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: any) => selector({ hasPermission: () => true }),
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

  it('删除失败不崩溃', async () => {
    _customerMocks.deleteCustomer.mockRejectedValue(new Error('删除失败'))
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

  it('无关联订单显示"暂无关联订单"', async () => {
    _orderMocks.fetchOrders.mockResolvedValue({
      success: true,
      data: { items: [], total: 0 },
    })
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('暂无关联订单')).toBeInTheDocument()
    })
  })

  it('来源显示中文映射', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('转介绍')).toBeInTheDocument()
    })
  })

  it('订单加载失败不阻塞页面', async () => {
    _orderMocks.fetchOrders.mockRejectedValue(new Error('订单接口错误'))
    renderCustomerDetail()
    await waitFor(() => {
      const cards = screen.getAllByTestId('card')
      expect(cards[0].getAttribute('data-title')).toBe('测试客户')
    })
  })

  it('无等级客户不显示等级标签', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: { ...mockCustomerData.data, level: null },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const levelItems = screen.getAllByTestId('desc-item').filter(
        (el) => el.getAttribute('data-label') === '等级',
      )
      expect(levelItems[0].textContent).toBe('--')
    })
  })

  it('未知等级显示原始值', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: { ...mockCustomerData.data, level: 'custom_level' },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const tags = screen.getAllByTestId('tag')
      const tagTexts = tags.map((t) => t.textContent)
      expect(tagTexts).toContain('custom_level')
    })
  })

  it('无来源客户显示 --', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: { ...mockCustomerData.data, source: null },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const sourceItems = screen.getAllByTestId('desc-item').filter(
        (el) => el.getAttribute('data-label') === '来源',
      )
      expect(sourceItems[0].textContent).toBe('--')
    })
  })

  it('未知来源显示原始值', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: { ...mockCustomerData.data, source: 'wechat_mini' },
    })
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('wechat_mini')).toBeInTheDocument()
    })
  })

  it('无备注不显示备注行', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: { ...mockCustomerData.data, remark: null },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const remarkItems = screen.getAllByTestId('desc-item').filter(
        (el) => el.getAttribute('data-label') === '备注',
      )
      expect(remarkItems.length).toBe(0)
    })
  })

  it('订单未知状态显示原始值', async () => {
    _orderMocks.fetchOrders.mockResolvedValue({
      success: true,
      data: {
        items: [{
          id: 'order-x', order_no: 'ORD-X', status: 'pending_review',
          total_amount: '100', created_at: '2026-05-01T00:00:00Z',
        }],
        total: 1,
      },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const tags = screen.getAllByTestId('tag')
      const tagTexts = tags.map((t) => t.textContent)
      expect(tagTexts).toContain('pending_review')
    })
  })

  it('订单空创建时间显示 --', async () => {
    _orderMocks.fetchOrders.mockResolvedValue({
      success: true,
      data: {
        items: [{
          id: 'order-y', order_no: 'ORD-Y', status: 'draft',
          total_amount: '200', created_at: null,
        }],
        total: 1,
      },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const row = screen.getByTestId('row-order-y')
      expect(row.textContent).toContain('--')
    })
  })

  it('空联系人电话邮箱显示 --', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: {
        ...mockCustomerData.data,
        contact_name: null, phone: null, email: null,
      },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const items = screen.getAllByTestId('desc-item')
      const labels = ['联系人', '电话', '邮箱']
      labels.forEach((label) => {
        const item = items.find((el) => el.getAttribute('data-label') === label)
        expect(item?.textContent).toBe('--')
      })
    })
  })

  it('删除 _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _customerMocks.deleteCustomer.mockRejectedValue(err)
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
    })
    const popconfirm = screen.getByTestId('popconfirm')
    await act(async () => { fireEvent.click(popconfirm) })
    await waitFor(() => {
      expect(_customerMocks.deleteCustomer).toHaveBeenCalledWith('cust-1')
    })
    // 不应显示错误消息
    expect(_messageError).not.toHaveBeenCalledWith('删除失败')
  })

  it('空更新时间显示 --', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: { ...mockCustomerData.data, updated_at: null },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const items = screen.getAllByTestId('desc-item')
      const item = items.find((el) => el.getAttribute('data-label') === '更新时间')
      expect(item?.textContent).toBe('--')
    })
  })

  it('空归属销售显示 --', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: { ...mockCustomerData.data, owner_name: null },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const items = screen.getAllByTestId('desc-item')
      const item = items.find((el) => el.getAttribute('data-label') === '归属销售')
      expect(item?.textContent).toBe('--')
    })
  })

  it('空跟进状态显示 --', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: { ...mockCustomerData.data, follow_status: null },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const items = screen.getAllByTestId('desc-item')
      const item = items.find((el) => el.getAttribute('data-label') === '跟进状态')
      expect(item?.textContent).toBe('--')
    })
  })

  it('点击订单号导航到订单详情', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByTestId('row-order-1')).toBeInTheDocument()
    })
    // 找到订单号链接并点击
    const link = screen.getByText('ORD-20260501-001')
    await act(async () => { fireEvent.click(link) })
    await waitFor(() => {
      expect(screen.getByText('Order Detail')).toBeInTheDocument()
    })
  })

  it('删除中再次点击不重复调用', async () => {
    let resolveDelete: (_v: any) => void
    _customerMocks.deleteCustomer.mockReturnValue(new Promise((r) => { resolveDelete = r }))
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
    })
    const popconfirm = screen.getByTestId('popconfirm')
    await act(async () => { fireEvent.click(popconfirm) })
    await waitFor(() => {
      expect(_customerMocks.deleteCustomer).toHaveBeenCalledTimes(1)
    })
    // 再次点击不应触发第二次调用
    await act(async () => { fireEvent.click(popconfirm) })
    expect(_customerMocks.deleteCustomer).toHaveBeenCalledTimes(1)
    resolveDelete!({ success: true })
  })

  it('fetchCustomer success=false 不设置客户', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({ success: false, data: null })
    renderCustomerDetail()
    await waitFor(() => {
      expect(_customerMocks.fetchCustomer).toHaveBeenCalledWith('cust-1')
    })
    // Should show loading state (no customer data)
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('loadCustomer _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _customerMocks.fetchCustomer.mockRejectedValue(err)
    renderCustomerDetail()
    await waitFor(() => {
      expect(_customerMocks.fetchCustomer).toHaveBeenCalledWith('cust-1')
    })
    expect(_messageError).not.toHaveBeenCalledWith('加载客户详情失败')
  })

  it('fetchOrders success=false 不设置订单', async () => {
    _orderMocks.fetchOrders.mockResolvedValue({ success: false, data: null })
    renderCustomerDetail()
    await waitFor(() => {
      expect(_orderMocks.fetchOrders).toHaveBeenCalled()
    })
    // Should show empty orders
    expect(screen.getByText('暂无关联订单')).toBeInTheDocument()
  })

  it('点击返回列表按钮导航到客户列表', async () => {
    renderCustomerDetail()
    await waitFor(() => {
      expect(screen.getByText('返回列表')).toBeInTheDocument()
    })
    const buttons = screen.getAllByTestId('button')
    const backBtn = buttons.find((b) => b.textContent?.includes('返回列表'))
    backBtn!.click()
    await waitFor(() => {
      expect(screen.getByText('Customers List')).toBeInTheDocument()
    })
  })

  it('空创建时间显示 --', async () => {
    _customerMocks.fetchCustomer.mockResolvedValue({
      success: true,
      data: { ...mockCustomerData.data, created_at: null },
    })
    renderCustomerDetail()
    await waitFor(() => {
      const items = screen.getAllByTestId('desc-item')
      const item = items.find((el) => el.getAttribute('data-label') === '创建时间')
      expect(item?.textContent).toBe('--')
    })
  })

  it('无 id 时不调用 API', async () => {
    render(
      <MemoryRouter initialEntries={['/customers']}>
        <Routes>
          <Route path="/customers" element={<CustomerDetail />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('加载中...')).toBeInTheDocument()
    })
    expect(_customerMocks.fetchCustomer).not.toHaveBeenCalled()
    expect(_orderMocks.fetchOrders).not.toHaveBeenCalled()
  })
})
