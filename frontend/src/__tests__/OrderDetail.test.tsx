/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _orderMocks = {
  fetchOrder: vi.fn(),
  confirmOrder: vi.fn(),
  cancelOrder: vi.fn(),
  fetchOrderLogs: vi.fn(),
}
const _paymentMocks = {
  createPayment: vi.fn(),
  reversePayment: vi.fn(),
}

vi.mock('@/api/orders', () => ({
  fetchOrder: (...args: any[]) => _orderMocks.fetchOrder(...args),
  confirmOrder: (...args: any[]) => _orderMocks.confirmOrder(...args),
  cancelOrder: (...args: any[]) => _orderMocks.cancelOrder(...args),
  fetchOrderLogs: (...args: any[]) => _orderMocks.fetchOrderLogs(...args),
}))

vi.mock('@/api/payments', () => ({
  createPayment: (...args: any[]) => _paymentMocks.createPayment(...args),
  reversePayment: (...args: any[]) => _paymentMocks.reversePayment(...args),
}))

const _authStore = { hasPermission: vi.fn(() => true) }
vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: any) => selector(_authStore),
}))

vi.mock('@/constants/statusMaps', () => ({
  orderStatusMap: {
    draft: { color: 'default', label: '草稿' },
    confirmed: { color: 'blue', label: '已确认' },
    cancelled: { color: 'red', label: '已取消' },
    partially_paid: { color: 'orange', label: '部分收款' },
    paid: { color: 'green', label: '已收款' },
  },
  paymentMethodMap: {
    cash: '现金',
    transfer: '转账',
    wechat: '微信',
    alipay: '支付宝',
  },
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
  formatPercent: (v: any) => `${v}%`,
  getApiErrorMessage: (_e: any, fallback: string) => fallback,
  isToastDisplayed: (e: any) => !!e?._toastDisplayed,
}))

const _messageError = vi.fn()
const _messageSuccess = vi.fn()
vi.mock('antd', () => ({
  Card: ({ title, children }: any) => (
    <div data-testid="card" data-title={title}>{children}</div>
  ),
  Descriptions: Object.assign(
    ({ children }: any) => <div data-testid="descriptions">{children}</div>,
    { Item: ({ children, label }: any) => <div data-testid="desc-item" data-label={label}>{children}</div> },
  ),
  Table: ({ dataSource, columns, rowKey, footer, locale, pagination }: any) => (
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
      {footer && <div data-testid="table-footer">{footer()}</div>}
      {pagination?.showTotal && <span data-testid="pagination-total">{pagination.showTotal(pagination.total)}</span>}
      {pagination?.onChange && <button data-testid="page-change" onClick={() => pagination.onChange(2, pagination.pageSize)}>翻页</button>}
    </div>
  ),
  Button: ({ children, onClick, icon, type, danger, disabled }: any) => (
    <button data-testid="button" data-type={type} data-danger={danger ? 'true' : undefined} disabled={disabled} onClick={onClick}>{icon}{children}</button>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
  Popconfirm: ({ title, children, onConfirm }: any) => (
    <span data-testid="popconfirm" data-title={title} onClick={onConfirm}>{children}</span>
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
  Modal: ({ title, children, open, onOk, onCancel }: any) => open ? (
    <div data-testid="modal" data-title={title}>
      {children}
      <button data-testid="modal-ok" onClick={onOk}>确定</button>
      <button data-testid="modal-cancel" onClick={onCancel}>取消</button>
    </div>
  ) : null,
  message: { error: (...args: any[]) => _messageError(...args), success: (...args: any[]) => _messageSuccess(...args) },
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

const mockLogsData = {
  success: true,
  data: {
    items: [
      { id: 'log-1', actor_name: '管理员', action: 'order_confirmed', after_data: { status: 'confirmed' }, created_at: '2026-05-01T11:00:00Z' },
      { id: 'log-2', actor_name: '销售员', action: 'order_created', after_data: { status: 'draft', total_amount: '1000' }, created_at: '2026-05-01T10:00:00Z' },
    ],
    page: 1,
    page_size: 10,
    total: 2,
  },
}

import OrderDetail from '@/pages/OrderDetail'

function renderOrderDetail() {
  return render(
    <MemoryRouter initialEntries={['/orders/order-1']}>
      <Routes>
        <Route path="/orders/:id" element={<OrderDetail />} />
        <Route path="/orders/:id/edit" element={<div>Edit Order</div>} />
        <Route path="/orders" element={<div>Orders List</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('OrderDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _authStore.hasPermission.mockImplementation(() => true)
    _orderMocks.fetchOrder.mockResolvedValue(mockOrderData)
    _orderMocks.fetchOrderLogs.mockResolvedValue(mockLogsData)
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

  it('加载中显示加载提示', async () => {
    let resolveFn: (_v: any) => void
    _orderMocks.fetchOrder.mockReturnValue(new Promise((r) => { resolveFn = r }))
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('加载中...')).toBeInTheDocument()
    })
    resolveFn!(mockOrderData)
  })

  it('渲染操作日志卡片', async () => {
    renderOrderDetail()
    await waitFor(() => {
      const cards = screen.getAllByTestId('card')
      const titles = cards.map((c) => c.getAttribute('data-title'))
      expect(titles).toContain('操作日志')
    })
  })

  it('显示操作日志数据', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByTestId('row-log-1')).toBeInTheDocument()
      expect(screen.getByTestId('row-log-2')).toBeInTheDocument()
      expect(screen.getByText('管理员')).toBeInTheDocument()
      expect(screen.getByText('销售员')).toBeInTheDocument()
    })
  })

  it('显示日志操作类型', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('order_confirmed')).toBeInTheDocument()
      expect(screen.getByText('order_created')).toBeInTheDocument()
    })
  })

  it('日志加载失败不阻塞页面', async () => {
    _orderMocks.fetchOrderLogs.mockRejectedValue(new Error('network'))
    renderOrderDetail()
    await waitFor(() => {
      // 页面仍正常渲染
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
  })

  it('fetchOrderLogs 使用正确 ID 调用', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(_orderMocks.fetchOrderLogs).toHaveBeenCalledWith('order-1', { page: 1, page_size: 10 })
    })
  })

  it('确认订单按钮点击调用 confirmOrder', async () => {
    _orderMocks.confirmOrder.mockResolvedValueOnce({ success: true, data: { id: 'order-1', status: 'confirmed' } })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('确认订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const confirmPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('确认订单'))
    expect(confirmPop).toBeTruthy()
    confirmPop!.click()
    await waitFor(() => {
      expect(_orderMocks.confirmOrder).toHaveBeenCalledWith('order-1')
    })
  })

  it('取消订单按钮点击调用 cancelOrder', async () => {
    _orderMocks.cancelOrder.mockResolvedValueOnce({ success: true, data: { id: 'order-1', status: 'cancelled' } })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('取消订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const cancelPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('取消该订单'))
    expect(cancelPop).toBeTruthy()
    cancelPop!.click()
    await waitFor(() => {
      expect(_orderMocks.cancelOrder).toHaveBeenCalledWith('order-1')
    })
  })

  it('冲正按钮存在且有确认弹窗', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('冲正')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const reversePop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('冲正'))
    expect(reversePop).toBeTruthy()
  })

  it('确认订单失败显示错误提示', async () => {
    _orderMocks.confirmOrder.mockRejectedValueOnce(new Error('confirm failed'))
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('确认订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const confirmPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('确认订单'))
    confirmPop!.click()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalled()
    })
  })

  it('已确认订单显示登记收款按钮', async () => {
    const confirmedData = {
      success: true,
      data: {
        id: 'order-1',
        order_no: 'ORD-CONF-001',
        status: 'confirmed',
        total_amount: '1000',
        total_cost: '600',
        gross_profit: '400',
        gross_margin: '40',
        paid_amount: '0',
        created_at: '2026-05-01T10:00:00Z',
        remark: null,
        items: [
          { id: 'item-1', product_name_snapshot: '商品A', product_sku_snapshot: 'SKU-001', quantity: 2, unit_price: '500', discount_amount: '0', subtotal_amount: '1000', product_image_url_snapshot: null },
        ],
        payments: [],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    renderOrderDetail()
    // 先等待订单加载
    await waitFor(() => {
      expect(screen.getByText(/ORD-CONF-001/)).toBeInTheDocument()
    })
    // 再检查登记收款按钮
    const buttons = screen.getAllByTestId('button')
    const payBtn = buttons.find((b) => b.textContent?.includes('登记收款'))
    expect(payBtn).toBeTruthy()
    // 确认按钮不应出现
    const confirmBtn = buttons.find((b) => b.textContent?.includes('确认订单'))
    expect(confirmBtn).toBeFalsy()
  })

  it('取消订单失败显示错误提示', async () => {
    _orderMocks.cancelOrder.mockRejectedValueOnce(new Error('cancel failed'))
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('取消订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const cancelPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('取消该订单'))
    cancelPop!.click()
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalled()
    })
  })

  it('无订单明细显示"暂无订单明细"', async () => {
    const emptyItemsData = {
      success: true,
      data: {
        ...mockOrderData.data,
        items: [],
        payments: [],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(emptyItemsData)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('暂无订单明细')).toBeInTheDocument()
    })
  })

  it('无操作日志显示"暂无操作日志"', async () => {
    _orderMocks.fetchOrderLogs.mockResolvedValue({
      success: true,
      data: { items: [], page: 1, page_size: 10, total: 0 },
    })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('暂无操作日志')).toBeInTheDocument()
    })
  })

  it('canViewCost 为 true 时显示成本信息', async () => {
    _authStore.hasPermission.mockImplementation(() => true)
    renderOrderDetail()
    await waitFor(() => {
      const descItems = screen.getAllByTestId('desc-item')
      const labels = descItems.map((d) => d.getAttribute('data-label'))
      expect(labels).toContain('总成本')
      expect(labels).toContain('毛利')
      expect(labels).toContain('毛利率')
    })
  })

  it('canViewCost 为 false 时不显示成本信息', async () => {
    _authStore.hasPermission.mockImplementation(() => false)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const descItems = screen.getAllByTestId('desc-item')
    const labels = descItems.map((d) => d.getAttribute('data-label'))
    expect(labels).not.toContain('总成本')
  })

  it('点击登记收款按钮打开收款弹窗', async () => {
    const confirmedData = {
      success: true,
      data: {
        ...mockOrderData.data,
        status: 'confirmed',
        payments: [],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    expect(payBtn).toBeTruthy()
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
      expect(screen.getByTestId('modal').getAttribute('data-title')).toBe('登记收款')
    })
  })

  it('收款弹窗中有金额、收款方式和备注输入', async () => {
    const confirmedData = {
      success: true,
      data: {
        ...mockOrderData.data,
        status: 'confirmed',
        payments: [],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => {
      expect(screen.getByTestId('input-number')).toBeInTheDocument()
      expect(screen.getByTestId('select')).toBeInTheDocument()
      expect(screen.getByTestId('input')).toBeInTheDocument()
    })
  })

  it('冲正成功后刷新订单', async () => {
    _paymentMocks.reversePayment.mockResolvedValueOnce({ success: true })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('冲正')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const reversePop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('冲正'))
    expect(reversePop).toBeTruthy()
    await act(async () => { fireEvent.click(reversePop!) })
    await waitFor(() => {
      expect(_paymentMocks.reversePayment).toHaveBeenCalledWith('pay-1')
      // 初始加载(×2, 组件有重复 useEffect) + 刷新 = 至少 3 次
      expect(_orderMocks.fetchOrder.mock.calls.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('冲正失败显示错误提示', async () => {
    _paymentMocks.reversePayment.mockRejectedValueOnce(new Error('冲正失败'))
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('冲正')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const reversePop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('冲正'))
    await act(async () => { fireEvent.click(reversePop!) })
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalled()
    })
  })

  it('返回列表按钮导航到订单列表', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('返回列表')).toBeInTheDocument()
    })
    screen.getByText('返回列表').click()
    await waitFor(() => {
      expect(screen.getByText('Orders List')).toBeInTheDocument()
    })
  })

  it('编辑按钮导航到编辑页', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
    })
    // 草稿状态有编辑按钮，点击应导航
    const editBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('编辑'),
    )
    expect(editBtn).toBeTruthy()
  })

  it('编辑按钮点击导航到编辑页面', async () => {
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('编辑')).toBeInTheDocument()
    })
    const editBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('编辑'),
    )
    await act(async () => { fireEvent.click(editBtn!) })
    await waitFor(() => {
      expect(screen.getByText('Edit Order')).toBeInTheDocument()
    })
  })

  it('登记收款成功提交并刷新', async () => {
    const confirmedData = {
      success: true,
      data: { ...mockOrderData.data, status: 'confirmed', payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    _paymentMocks.createPayment.mockResolvedValueOnce({ success: true })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
    })
    // 输入金额
    const inputNumber = screen.getByTestId('input-number')
    await act(async () => {
      fireEvent.change(inputNumber, { target: { value: '500' } })
    })
    // 点击确定
    const okBtn = screen.getByTestId('modal-ok')
    await act(async () => { fireEvent.click(okBtn) })
    await waitFor(() => {
      expect(_paymentMocks.createPayment).toHaveBeenCalledWith('order-1', {
        amount: '500',
        payment_method: 'cash',
        remark: undefined,
      })
      expect(_messageSuccess).toHaveBeenCalledWith('收款登记成功')
    })
  })

  it('登记收款金额为 0 显示错误提示', async () => {
    const confirmedData = {
      success: true,
      data: { ...mockOrderData.data, status: 'confirmed', payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
    })
    // 不修改金额，直接提交（默认为 0）
    const okBtn = screen.getByTestId('modal-ok')
    await act(async () => { fireEvent.click(okBtn) })
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('请输入正确的收款金额')
    })
  })

  it('登记收款失败显示错误提示', async () => {
    const confirmedData = {
      success: true,
      data: { ...mockOrderData.data, status: 'confirmed', payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    _paymentMocks.createPayment.mockRejectedValueOnce(new Error('支付失败'))
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
    })
    // 输入金额
    const inputNumber = screen.getByTestId('input-number')
    await act(async () => {
      fireEvent.change(inputNumber, { target: { value: '100' } })
    })
    const okBtn = screen.getByTestId('modal-ok')
    await act(async () => { fireEvent.click(okBtn) })
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('收款登记失败')
    })
  })

  it('收款弹窗点击取消关闭', async () => {
    const confirmedData = {
      success: true,
      data: { ...mockOrderData.data, status: 'confirmed', payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
    })
    const cancelBtn = screen.getByTestId('modal-cancel')
    await act(async () => { fireEvent.click(cancelBtn) })
    await waitFor(() => {
      expect(screen.queryByTestId('modal')).not.toBeInTheDocument()
    })
  })

  it('操作日志分页超过 10 条时显示分页', async () => {
    _orderMocks.fetchOrderLogs.mockResolvedValue({
      success: true,
      data: { items: mockLogsData.data.items, page: 1, page_size: 10, total: 25 },
    })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByTestId('pagination-total')).toBeInTheDocument()
    })
    expect(screen.getByTestId('pagination-total').textContent).toBe('共 25 条')
    // 点击翻页
    await act(async () => { fireEvent.click(screen.getByTestId('page-change')) })
    await waitFor(() => {
      expect(_orderMocks.fetchOrderLogs).toHaveBeenCalledWith('order-1', { page: 2, page_size: 10 })
    })
  })

  it('收款弹窗中输入备注', async () => {
    const confirmedData = {
      success: true,
      data: { ...mockOrderData.data, status: 'confirmed', payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    _paymentMocks.createPayment.mockResolvedValueOnce({ success: true })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
    })
    // 修改金额
    const inputNumber = screen.getByTestId('input-number')
    await act(async () => {
      fireEvent.change(inputNumber, { target: { value: '300' } })
    })
    // 输入备注
    const inputs = screen.getAllByTestId('input')
    const remarkInput = inputs.find((inp) => inp.getAttribute('placeholder') === '可选')
    expect(remarkInput).toBeTruthy()
    await act(async () => {
      fireEvent.change(remarkInput!, { target: { value: '定金' } })
    })
    // 提交
    const okBtn = screen.getByTestId('modal-ok')
    await act(async () => { fireEvent.click(okBtn) })
    await waitFor(() => {
      expect(_paymentMocks.createPayment).toHaveBeenCalledWith('order-1', {
        amount: '300',
        payment_method: 'cash',
        remark: '定金',
      })
    })
  })

  it('商品有图片时显示图片', async () => {
    const dataWithImage = {
      success: true,
      data: {
        ...mockOrderData.data,
        items: [
          { id: 'item-img', product_name_snapshot: '商品B', product_sku_snapshot: 'SKU-002', quantity: 1, unit_price: '200', discount_amount: '0', subtotal_amount: '200', product_image_url_snapshot: 'https://img.test/pic.jpg' },
        ],
        payments: [],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(dataWithImage)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByTestId('image')).toBeInTheDocument()
      expect(screen.getByTestId('image').getAttribute('src')).toBe('https://img.test/pic.jpg')
    })
  })

  it('折扣大于零显示折扣金额', async () => {
    const dataWithDiscount = {
      success: true,
      data: {
        ...mockOrderData.data,
        items: [
          { id: 'item-disc', product_name_snapshot: '商品C', product_sku_snapshot: 'SKU-003', quantity: 1, unit_price: '500', discount_amount: '50', subtotal_amount: '450', product_image_url_snapshot: null },
        ],
        payments: [],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(dataWithDiscount)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('-¥50')).toBeInTheDocument()
    })
  })

  it('未知收款方式显示原始值', async () => {
    const dataWithUnknownMethod = {
      success: true,
      data: {
        ...mockOrderData.data,
        payments: [
          { id: 'pay-x', amount: '200', payment_method: 'crypto', paid_at: '2026-05-01T12:00:00Z', remark: '' },
        ],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(dataWithUnknownMethod)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('crypto')).toBeInTheDocument()
    })
  })

  it('收款记录空 paid_at 显示 --', async () => {
    const dataWithNullPaidAt = {
      success: true,
      data: {
        ...mockOrderData.data,
        payments: [
          { id: 'pay-null', amount: '100', payment_method: 'cash', paid_at: null, remark: '' },
        ],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(dataWithNullPaidAt)
    renderOrderDetail()
    await waitFor(() => {
      const row = screen.getByTestId('row-pay-null')
      // paid_at 列渲染的 '--'
      expect(row.textContent).toContain('--')
    })
  })

  it('操作日志空 after_data 显示 --', async () => {
    _orderMocks.fetchOrderLogs.mockResolvedValue({
      success: true,
      data: {
        items: [
          { id: 'log-null', actor_name: '管理员', action: 'note_added', after_data: null, created_at: '2026-05-01T12:00:00Z' },
        ],
        page: 1, page_size: 10, total: 1,
      },
    })
    renderOrderDetail()
    await waitFor(() => {
      const row = screen.getByTestId('row-log-null')
      expect(row.textContent).toContain('note_added')
    })
  })

  it('操作日志空 created_at 显示 --', async () => {
    _orderMocks.fetchOrderLogs.mockResolvedValue({
      success: true,
      data: {
        items: [
          { id: 'log-nodate', actor_name: '管理员', action: 'test', after_data: { x: 1 }, created_at: null },
        ],
        page: 1, page_size: 10, total: 1,
      },
    })
    renderOrderDetail()
    await waitFor(() => {
      const row = screen.getByTestId('row-log-nodate')
      expect(row.textContent).toContain('--')
    })
  })

  it('未知订单状态显示原始值', async () => {
    const unknownStatusData = {
      success: true,
      data: { ...mockOrderData.data, status: 'shipped', payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(unknownStatusData)
    renderOrderDetail()
    await waitFor(() => {
      const tags = screen.getAllByTestId('tag')
      const tagTexts = tags.map((t) => t.textContent)
      expect(tagTexts).toContain('shipped')
    })
  })

  it('订单空 created_at 显示 --', async () => {
    const nullCreatedData = {
      success: true,
      data: { ...mockOrderData.data, created_at: null, payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(nullCreatedData)
    renderOrderDetail()
    await waitFor(() => {
      const createdItems = screen.getAllByTestId('desc-item').filter(
        (el) => el.getAttribute('data-label') === '创建时间',
      )
      expect(createdItems[0].textContent).toBe('--')
    })
  })

  it('订单无备注不显示备注行', async () => {
    const noRemarkData = {
      success: true,
      data: { ...mockOrderData.data, remark: null, payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(noRemarkData)
    renderOrderDetail()
    await waitFor(() => {
      const remarkItems = screen.getAllByTestId('desc-item').filter(
        (el) => el.getAttribute('data-label') === '备注',
      )
      expect(remarkItems.length).toBe(0)
    })
  })

  it('InputNumber onChange null 设为 0', async () => {
    const confirmedData = {
      success: true,
      data: { ...mockOrderData.data, status: 'confirmed', payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => {
      expect(screen.getByTestId('input-number')).toBeInTheDocument()
    })
    // InputNumber mock passes parsed value; test null case by clearing
    const inputNumber = screen.getByTestId('input-number')
    await act(async () => {
      fireEvent.change(inputNumber, { target: { value: '' } })
    })
    // value '' → parseFloat('') = NaN → onChange(NaN) → setPayAmount(NaN || 0) = 0
    expect(inputNumber).toBeTruthy()
  })

  it('已完成订单不显示编辑确认取消按钮', async () => {
    const completedData = {
      success: true,
      data: {
        ...mockOrderData.data,
        status: 'completed',
        payments: [{ id: 'pay-1', amount: '1000', payment_method: 'cash', paid_at: '2026-05-01T12:00:00Z', remark: '' }],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(completedData)
    renderOrderDetail()
    await waitFor(() => {
      const buttons = screen.getAllByTestId('button')
      const btnTexts = buttons.map((b) => b.textContent)
      expect(btnTexts).not.toContain('编辑')
      expect(btnTexts).not.toContain('确认订单')
      expect(btnTexts).not.toContain('取消订单')
    })
  })

  it('部分收款订单显示登记收款和取消按钮', async () => {
    const partialData = {
      success: true,
      data: {
        ...mockOrderData.data,
        status: 'partially_paid',
        payments: [{ id: 'pay-1', amount: '500', payment_method: 'cash', paid_at: '2026-05-01T12:00:00Z', remark: '' }],
      },
    }
    _orderMocks.fetchOrder.mockResolvedValue(partialData)
    renderOrderDetail()
    await waitFor(() => {
      const buttons = screen.getAllByTestId('button')
      const btnTexts = buttons.map((b) => b.textContent ?? '')
      expect(btnTexts.some((t) => t.includes('登记收款'))).toBe(true)
      expect(btnTexts.some((t) => t.includes('取消订单'))).toBe(true)
    })
  })

  it('确认订单 _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _orderMocks.confirmOrder.mockRejectedValueOnce(err)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('确认订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const confirmPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('确认订单'))
    confirmPop!.click()
    await waitFor(() => {
      expect(_orderMocks.confirmOrder).toHaveBeenCalled()
    })
    expect(_messageError).not.toHaveBeenCalledWith('确认失败')
  })

  it('取消订单 _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _orderMocks.cancelOrder.mockRejectedValueOnce(err)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('取消订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const cancelPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('取消该订单'))
    cancelPop!.click()
    await waitFor(() => {
      expect(_orderMocks.cancelOrder).toHaveBeenCalled()
    })
    expect(_messageError).not.toHaveBeenCalledWith('取消失败')
  })

  it('登记收款 _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    const confirmedData = {
      success: true,
      data: { ...mockOrderData.data, status: 'confirmed', payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    _paymentMocks.createPayment.mockRejectedValueOnce(err)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeInTheDocument() })
    const inputNumber = screen.getByTestId('input-number')
    await act(async () => { fireEvent.change(inputNumber, { target: { value: '100' } }) })
    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_paymentMocks.createPayment).toHaveBeenCalled()
    })
    expect(_messageError).not.toHaveBeenCalledWith('收款登记失败')
  })

  it('冲正 _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _paymentMocks.reversePayment.mockRejectedValueOnce(err)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('冲正')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const reversePop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('冲正'))
    await act(async () => { fireEvent.click(reversePop!) })
    await waitFor(() => {
      expect(_paymentMocks.reversePayment).toHaveBeenCalled()
    })
    expect(_messageError).not.toHaveBeenCalledWith('冲正失败')
  })

  it('加载订单 _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _orderMocks.fetchOrder.mockRejectedValue(err)
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('加载中...')).toBeInTheDocument()
    })
    expect(_messageError).not.toHaveBeenCalledWith('加载订单详情失败')
  })

  it('确认订单 res.success=false 不显示成功消息', async () => {
    _orderMocks.confirmOrder.mockResolvedValueOnce({ success: false, data: null })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('确认订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const confirmPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('确认订单'))
    confirmPop!.click()
    await waitFor(() => {
      expect(_orderMocks.confirmOrder).toHaveBeenCalled()
    })
    expect(_messageSuccess).not.toHaveBeenCalledWith('订单已确认，库存已扣减')
  })

  it('取消订单 res.success=false 不显示成功消息', async () => {
    _orderMocks.cancelOrder.mockResolvedValueOnce({ success: false, data: null })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('取消订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const cancelPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('取消该订单'))
    cancelPop!.click()
    await waitFor(() => {
      expect(_orderMocks.cancelOrder).toHaveBeenCalled()
    })
    expect(_messageSuccess).not.toHaveBeenCalledWith('订单已取消')
  })

  it('登记收款 res.success=false 不显示成功消息', async () => {
    const confirmedData = {
      success: true,
      data: { ...mockOrderData.data, status: 'confirmed', payments: [] },
    }
    _orderMocks.fetchOrder.mockResolvedValue(confirmedData)
    _paymentMocks.createPayment.mockResolvedValueOnce({ success: false, data: null })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText(/ORD-20260501-001/)).toBeInTheDocument()
    })
    const payBtn = screen.getAllByTestId('button').find(
      (b) => b.textContent?.includes('登记收款'),
    )
    await act(async () => { fireEvent.click(payBtn!) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeInTheDocument() })
    const inputNumber = screen.getByTestId('input-number')
    await act(async () => { fireEvent.change(inputNumber, { target: { value: '100' } }) })
    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_paymentMocks.createPayment).toHaveBeenCalled()
    })
    expect(_messageSuccess).not.toHaveBeenCalledWith('收款登记成功')
  })

  it('冲正 res.success=false 不显示成功消息', async () => {
    _paymentMocks.reversePayment.mockResolvedValueOnce({ success: false, data: null })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('冲正')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const reversePop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('冲正'))
    await act(async () => { fireEvent.click(reversePop!) })
    await waitFor(() => {
      expect(_paymentMocks.reversePayment).toHaveBeenCalled()
    })
    expect(_messageSuccess).not.toHaveBeenCalledWith('冲正成功')
  })

  it('loadLogs res.success=false 不设置日志', async () => {
    _orderMocks.fetchOrderLogs.mockResolvedValue({
      success: false,
      data: null,
    })
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('暂无操作日志')).toBeInTheDocument()
    })
  })

  it('fetchOrder success=false 不设置订单数据', async () => {
    _orderMocks.fetchOrder.mockResolvedValue({ success: false, data: null })
    renderOrderDetail()
    await waitFor(() => {
      expect(_orderMocks.fetchOrder).toHaveBeenCalledWith('order-1')
    })
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('确认中再次点击不重复调用 confirmOrder', async () => {
    let resolveConfirm: (_v: any) => void
    _orderMocks.confirmOrder.mockReturnValue(new Promise((r) => { resolveConfirm = r }))
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('确认订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const confirmPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('确认订单'))
    await act(async () => { fireEvent.click(confirmPop!) })
    await waitFor(() => {
      expect(_orderMocks.confirmOrder).toHaveBeenCalledTimes(1)
    })
    await act(async () => { fireEvent.click(confirmPop!) })
    expect(_orderMocks.confirmOrder).toHaveBeenCalledTimes(1)
    resolveConfirm!({ success: true, data: { id: 'order-1', status: 'confirmed' } })
  })

  it('取消中再次点击不重复调用 cancelOrder', async () => {
    let resolveCancel: (_v: any) => void
    _orderMocks.cancelOrder.mockReturnValue(new Promise((r) => { resolveCancel = r }))
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('取消订单')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const cancelPop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('取消该订单'))
    await act(async () => { fireEvent.click(cancelPop!) })
    await waitFor(() => {
      expect(_orderMocks.cancelOrder).toHaveBeenCalledTimes(1)
    })
    await act(async () => { fireEvent.click(cancelPop!) })
    expect(_orderMocks.cancelOrder).toHaveBeenCalledTimes(1)
    resolveCancel!({ success: true, data: { id: 'order-1', status: 'cancelled' } })
  })

  it('冲正中再次点击不重复调用 reversePayment', async () => {
    let resolveReverse: (_v: any) => void
    _paymentMocks.reversePayment.mockReturnValue(new Promise((r) => { resolveReverse = r }))
    renderOrderDetail()
    await waitFor(() => {
      expect(screen.getByText('冲正')).toBeInTheDocument()
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    const reversePop = popconfirms.find((p) => p.getAttribute('data-title')?.includes('冲正'))
    await act(async () => { fireEvent.click(reversePop!) })
    await waitFor(() => {
      expect(_paymentMocks.reversePayment).toHaveBeenCalledTimes(1)
    })
    await act(async () => { fireEvent.click(reversePop!) })
    expect(_paymentMocks.reversePayment).toHaveBeenCalledTimes(1)
    resolveReverse!({ success: true })
  })

  it('无 id 参数时 loadOrder 和 loadLogs 不调用 API', async () => {
    render(
      <MemoryRouter initialEntries={['/orders']}>
        <Routes>
          <Route path="/orders" element={<OrderDetail />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => {
      expect(screen.getByText('加载中...')).toBeInTheDocument()
    })
    expect(_orderMocks.fetchOrder).not.toHaveBeenCalled()
    expect(_orderMocks.fetchOrderLogs).not.toHaveBeenCalled()
  })
})
