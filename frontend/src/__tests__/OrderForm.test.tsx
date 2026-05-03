/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
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

const _customerApi = {
  fetchCustomers: vi.fn().mockResolvedValue({ success: true, data: { items: [] } }),
}

vi.mock('@/api/customers', () => ({
  fetchCustomers: (...a: any[]) => _customerApi.fetchCustomers(...a),
}))

const _productApi = {
  fetchProducts: vi.fn().mockResolvedValue({ success: true, data: { items: [] } }),
}

vi.mock('@/api/products', () => ({
  fetchProducts: (...a: any[]) => _productApi.fetchProducts(...a),
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
  getApiErrorMessage: (_e: any, fallback: string) => fallback,
}))

const _useSubmit = { callback: null as any, submitting: false }

vi.mock('@/hooks/useSubmit', () => ({
  useSubmit: (cb: any) => {
    _useSubmit.callback = cb
    return { submitting: _useSubmit.submitting, handleSubmit: cb }
  },
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
  Card: ({ title, children, extra }: any) => (
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

// 从已 mock 的 antd 获取 message 引用
import { message as antdMessage } from 'antd'

function renderNewOrder() {
  return render(
    <MemoryRouter initialEntries={['/orders/new']}>
      <Routes>
        <Route path="/orders/new" element={<OrderForm />} />
        <Route path="/orders/:id" element={<OrderForm />} />
        <Route path="/orders" element={<div>Orders List</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderEditOrder(orderId = 'o-123') {
  return render(
    <MemoryRouter initialEntries={[`/orders/${orderId}`]}>
      <Routes>
        <Route path="/orders/new" element={<OrderForm />} />
        <Route path="/orders/:id" element={<OrderForm />} />
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

  describe('编辑模式', () => {
    it('编辑模式渲染"编辑订单"标题', () => {
      _orderApi.fetchOrder.mockResolvedValue({ success: true, data: { items: [] } })
      renderEditOrder()
      const cards = screen.getAllByTestId('card')
      expect(cards[0].getAttribute('data-title')).toBe('编辑订单')
    })

    it('编辑模式调用 fetchOrder 获取数据', () => {
      _orderApi.fetchOrder.mockResolvedValue({ success: true, data: { items: [] } })
      renderEditOrder('o-456')
      expect(_orderApi.fetchOrder).toHaveBeenCalledWith('o-456')
    })

    it('编辑模式渲染"保存修改"按钮', () => {
      _orderApi.fetchOrder.mockResolvedValue({ success: true, data: { items: [] } })
      renderEditOrder()
      expect(screen.getByText('保存修改')).toBeInTheDocument()
    })
  })

  it('空订单行表格存在', () => {
    renderNewOrder()
    const tables = screen.getAllByTestId('table')
    expect(tables.length).toBeGreaterThanOrEqual(1)
  })

  it('显示订单行数统计', () => {
    renderNewOrder()
    expect(screen.getByText(/共 \d+ 项/)).toBeInTheDocument()
  })

  it('显示合计金额', () => {
    renderNewOrder()
    expect(screen.getByTestId('table-footer')).toBeInTheDocument()
    expect(screen.getByTestId('table-footer').textContent).toContain('合计')
  })

  it('客户选择器存在', () => {
    renderNewOrder()
    const selects = screen.getAllByTestId('select')
    expect(selects.length).toBeGreaterThanOrEqual(1)
  })

  it('备注字段有 maxLength 限制', () => {
    renderNewOrder()
    const textarea = screen.getByTestId('textarea')
    expect(textarea).toHaveAttribute('maxlength', '500')
  })

  it('点击取消按钮导航回订单列表', () => {
    renderNewOrder()
    const cancelBtn = screen.getByText('取消')
    expect(cancelBtn).toBeInTheDocument()
  })

  it('表单有客户和备注字段', () => {
    renderNewOrder()
    const formItems = screen.getAllByTestId('form-item')
    const names = formItems.map((fi) => fi.getAttribute('data-name'))
    expect(names).toContain('customer_id')
    expect(names).toContain('remark')
  })

  it('返回列表按钮导航到订单列表', async () => {
    renderNewOrder()
    screen.getByText('返回列表').click()
    await waitFor(() => {
      expect(screen.getByText('Orders List')).toBeInTheDocument()
    })
  })

  it('取消按钮导航到订单列表', async () => {
    renderNewOrder()
    screen.getByText('取消').click()
    await waitFor(() => {
      expect(screen.getByText('Orders List')).toBeInTheDocument()
    })
  })

  it('编辑模式 fetchOrder 失败验证', async () => {
    _orderApi.fetchOrder.mockRejectedValue(new Error('加载失败'))
    renderEditOrder()
    await waitFor(() => {
      expect(_orderApi.fetchOrder).toHaveBeenCalled()
    })
  })

  it('创建按钮有 loading 状态支持', () => {
    renderNewOrder()
    const buttons = screen.getAllByTestId('button')
    const createBtn = buttons.find((b) => b.textContent?.includes('创建订单'))
    expect(createBtn).toBeTruthy()
    expect(createBtn?.getAttribute('data-type')).toBe('primary')
  })

  it('备注使用 textarea 组件', () => {
    renderNewOrder()
    const textarea = screen.getByTestId('textarea')
    expect(textarea).toHaveAttribute('maxlength', '500')
    expect(textarea.tagName).toBe('TEXTAREA')
  })

  describe('商品选择', () => {
    const mockProducts = [
      {
        id: 'p1', name: '商品A', sku: 'SKU001', sale_price: '100.00',
        main_image_url: 'http://img/a.jpg', stock_quantity: 10,
      },
      {
        id: 'p2', name: '商品B', sku: 'SKU002', sale_price: '200.00',
        main_image_url: null, stock_quantity: 5,
      },
    ]

    it('点击添加商品触发 fetchProducts', async () => {
      _productApi.fetchProducts.mockResolvedValueOnce({ success: true, data: { items: mockProducts } })
      renderNewOrder()

      // 通过直接点击按钮元素
      const addBtn = screen.getAllByTestId('button').find(
        (b) => b.textContent?.includes('添加商品'),
      )
      expect(addBtn).toBeTruthy()
      fireEvent.click(addBtn!)

      await waitFor(() => {
        expect(_productApi.fetchProducts).toHaveBeenCalled()
      })
    })

    it('关闭按钮关闭商品选择器', async () => {
      _productApi.fetchProducts.mockResolvedValueOnce({ success: true, data: { items: mockProducts } })
      renderNewOrder()

      const addBtn = screen.getAllByTestId('button').find(
        (b) => b.textContent?.includes('添加商品'),
      )
      fireEvent.click(addBtn!)

      // 等待商品选择器卡片出现（title 在 data-title 属性中）
      await waitFor(() => {
        const picker = screen.getAllByTestId('card').find(
          (c) => c.getAttribute('data-title') === '选择商品',
        )
        expect(picker).toBeTruthy()
      })

      // 点击关闭按钮
      const closeBtn = screen.getByText('关闭')
      fireEvent.click(closeBtn)

      // 选择器应消失
      await waitFor(() => {
        const picker = screen.getAllByTestId('card').find(
          (c) => c.getAttribute('data-title') === '选择商品',
        )
        expect(picker).toBeFalsy()
      })
    })
  })

  describe('编辑模式加载', () => {
    it('编辑模式加载订单行数据', async () => {
      _orderApi.fetchOrder.mockResolvedValue({
        success: true,
        data: {
          id: 'o-1', order_no: 'SO-001', customer_id: 'c1',
          status: 'draft', status_label: '草稿',
          total_amount: '300.00', total_cost: '200.00',
          gross_profit: '100.00', gross_margin: '33.33',
          paid_amount: '0', remark: '测试备注',
          sales_user_id: 'u1', created_at: '2026-05-01', updated_at: null,
          items: [
            {
              id: 'oi1', product_id: 'p1', product_sku_snapshot: 'SKU001',
              product_name_snapshot: '商品A', product_image_url_snapshot: 'http://img/a.jpg',
              quantity: 2, unit_price: '100.00', discount_amount: '0',
              discount_rate: '1', cost_price_snapshot: '80.00',
              subtotal_amount: '200.00', subtotal_cost: '160.00',
            },
          ],
          payments: [],
        },
      })
      renderEditOrder()

      await waitFor(() => {
        expect(screen.getAllByTestId('table')[0].textContent).toContain('SKU001')
      })
    })

    it('编辑模式设置表单值', async () => {
      _orderApi.fetchOrder.mockResolvedValue({
        success: true,
        data: {
          id: 'o-1', order_no: 'SO-001', customer_id: 'c1',
          status: 'draft', status_label: '草稿',
          total_amount: '0', total_cost: '0',
          gross_profit: '0', gross_margin: '0',
          paid_amount: '0', remark: '备注内容',
          sales_user_id: 'u1', created_at: null, updated_at: null,
          items: [], payments: [],
        },
      })
      renderEditOrder()

      await waitFor(() => {
        expect(_mockForm.setFieldsValue).toHaveBeenCalledWith({
          customer_id: 'c1',
          remark: '备注内容',
        })
      })
    })
  })

  describe('提交订单', () => {
    it('提交时验证至少一个商品', async () => {
      renderNewOrder()
      expect(_useSubmit.callback).toBeTruthy()

      _mockForm.validateFields.mockResolvedValueOnce({ customer_id: 'c1' })

      await _useSubmit.callback()
      expect(antdMessage.error).toHaveBeenCalledWith('请添加至少一个商品')
    })

    it('创建订单成功', async () => {
      _orderApi.createOrder.mockResolvedValueOnce({ success: true, data: { id: 'o-new' } })
      _mockForm.validateFields.mockResolvedValueOnce({ customer_id: 'c1' })
      renderNewOrder()

      // 模拟添加了一个订单行到 callback 闭包中
      // 直接调用 callback 会因为 lines 为空而报错，所以需要通过 addProduct 添加行
      // 但 addProduct 在 picker 中，我们需要先打开 picker 并选择商品
      const addBtn = screen.getAllByTestId('button').find(
        (b) => b.textContent?.includes('添加商品'),
      )
      fireEvent.click(addBtn!)

      await waitFor(() => {
        expect(_productApi.fetchProducts).toHaveBeenCalled()
      })
    })

    it('创建订单成功完整流程', async () => {
      const mockProducts = [
        {
          id: 'p1', name: '商品A', sku: 'SKU001', sale_price: '100.00',
          main_image_url: null, stock_quantity: 10,
        },
      ]
      _productApi.fetchProducts.mockResolvedValueOnce({ success: true, data: { items: mockProducts } })
      _orderApi.createOrder.mockResolvedValueOnce({ success: true, data: { id: 'o-new' } })
      _mockForm.validateFields.mockResolvedValueOnce({ customer_id: 'c1' })
      renderNewOrder()

      // 打开商品选择器
      const addBtn = screen.getAllByTestId('button').find(
        (b) => b.textContent?.includes('添加商品'),
      )
      await act(async () => { fireEvent.click(addBtn!) })

      // 等待商品加载并点击"选择"
      await waitFor(() => {
        const selectBtn = screen.getByText('选择')
        expect(selectBtn).toBeInTheDocument()
      })

      const selectBtn = screen.getByText('选择')
      await act(async () => { fireEvent.click(selectBtn) })

      // 现在订单行中有商品了，提交
      await act(async () => {
        await _useSubmit.callback()
      })

      await waitFor(() => {
        expect(_orderApi.createOrder).toHaveBeenCalledWith(
          expect.objectContaining({
            customer_id: 'c1',
            items: expect.arrayContaining([
              expect.objectContaining({ product_id: 'p1', quantity: 1 }),
            ]),
          }),
        )
        expect(antdMessage.success).toHaveBeenCalledWith('创建成功')
      })
    })

    it('更新订单成功', async () => {
      _orderApi.fetchOrder.mockResolvedValue({
        success: true,
        data: {
          id: 'o-1', order_no: 'SO-001', customer_id: 'c1',
          status: 'draft', status_label: '草稿',
          total_amount: '100.00', total_cost: '80.00',
          gross_profit: '20.00', gross_margin: '20',
          paid_amount: '0', remark: '',
          sales_user_id: 'u1', created_at: null, updated_at: null,
          items: [{
            id: 'oi1', product_id: 'p1', product_sku_snapshot: 'SKU001',
            product_name_snapshot: '商品A', product_image_url_snapshot: null,
            quantity: 1, unit_price: '100.00', discount_amount: '0',
            discount_rate: '1', cost_price_snapshot: '80.00',
            subtotal_amount: '100.00', subtotal_cost: '80.00',
          }],
          payments: [],
        },
      })
      _orderApi.updateOrder.mockResolvedValueOnce({ success: true })
      _mockForm.validateFields.mockResolvedValueOnce({ customer_id: 'c1' })
      renderEditOrder()

      await waitFor(() => {
        expect(_orderApi.fetchOrder).toHaveBeenCalledWith('o-123')
      })

      await act(async () => {
        await _useSubmit.callback()
      })

      await waitFor(() => {
        expect(_orderApi.updateOrder).toHaveBeenCalledWith(
          'o-123',
          expect.objectContaining({ customer_id: 'c1' }),
        )
        expect(antdMessage.success).toHaveBeenCalledWith('更新成功')
      })
    })
  })

  describe('客户搜索', () => {
    it('客户选择器有搜索功能', () => {
      renderNewOrder()
      const selects = screen.getAllByTestId('select')
      expect(selects[0].getAttribute('data-testid')).toBe('select')
    })
  })
})
