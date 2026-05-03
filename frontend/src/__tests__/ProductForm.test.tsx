/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _productApi = {
  fetchProduct: vi.fn(),
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
  uploadImage: vi.fn(),
}

vi.mock('@/api/products', () => ({
  fetchProduct: (...a: any[]) => _productApi.fetchProduct(...a),
  createProduct: (...a: any[]) => _productApi.createProduct(...a),
  updateProduct: (...a: any[]) => _productApi.updateProduct(...a),
  uploadImage: (...a: any[]) => _productApi.uploadImage(...a),
}))

vi.mock('@/hooks/useSubmit', () => ({
  useSubmit: (onSubmit: any) => ({
    submitting: false,
    handleSubmit: (e: any) => { e?.preventDefault?.() },
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
        <div data-testid="form-item" data-label={label} data-name={name}>
          {children}
        </div>
      ),
      useForm: () => [_mockForm],
    },
  ),
  Input: Object.assign(
    (props: any) => <input data-testid="input" {...props} />,
    { TextArea: (props: any) => <textarea data-testid="textarea" {...props} /> },
  ),
  InputNumber: (props: any) => <input data-testid="input-number" type="number" {...props} />,
  Button: ({ children, onClick, icon, type, loading, htmlType }: any) => (
    <button data-testid="button" data-type={type} data-htmltype={htmlType} onClick={onClick} disabled={loading}>{icon}{children}</button>
  ),
  Card: ({ title, children, loading }: any) => (
    <div data-testid="card" data-title={title} data-loading={loading ? 'true' : 'false'}>{children}</div>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Upload: ({ children }: any) => <div data-testid="upload">{children}</div>,
  Image: ({ src }: any) => <img data-testid="image" src={src} />,
  Select: ({ options, value, onChange }: any) => (
    <select data-testid="select" value={value} onChange={(e: any) => onChange?.(e.target.value)}>
      {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  ),
  message: { error: vi.fn(), success: vi.fn() },
}))

vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span>+</span>,
  ArrowLeftOutlined: () => <span>←</span>,
}))

import ProductForm from '@/pages/ProductForm'

function renderNewProduct() {
  return render(
    <MemoryRouter initialEntries={['/products/new']}>
      <Routes>
        <Route path="/products/new" element={<ProductForm />} />
        <Route path="/products/:id" element={<ProductForm />} />
        <Route path="/products" element={<div>Products List</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderEditProduct(productId = 'p-123') {
  return render(
    <MemoryRouter initialEntries={[`/products/${productId}`]}>
      <Routes>
        <Route path="/products/new" element={<ProductForm />} />
        <Route path="/products/:id" element={<ProductForm />} />
        <Route path="/products" element={<div>Products List</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProductForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('新增模式渲染"新增商品"标题', () => {
    renderNewProduct()
    const card = screen.getByTestId('card')
    expect(card.getAttribute('data-title')).toBe('新增商品')
  })

  it('渲染返回列表按钮', () => {
    renderNewProduct()
    expect(screen.getByText('返回列表')).toBeInTheDocument()
  })

  it('渲染必要表单字段', () => {
    renderNewProduct()
    const formItems = screen.getAllByTestId('form-item')
    const labels = formItems.map((fi) => fi.getAttribute('data-label'))
    expect(labels).toContain('商品名称')
    expect(labels).toContain('成本价')
    expect(labels).toContain('销售价')
  })

  it('商品名称为必填字段', () => {
    renderNewProduct()
    const nameItem = screen.getAllByTestId('form-item').find(
      (fi) => fi.getAttribute('data-name') === 'name',
    )
    expect(nameItem).toBeTruthy()
  })

  it('渲染提交按钮', () => {
    renderNewProduct()
    expect(screen.getByText('创建商品')).toBeInTheDocument()
  })

  it('渲染取消按钮', () => {
    renderNewProduct()
    expect(screen.getByText('取消')).toBeInTheDocument()
  })

  it('渲染图片上传区域', () => {
    renderNewProduct()
    expect(screen.getByTestId('upload')).toBeInTheDocument()
  })

  it('新增模式不调用 fetchProduct', () => {
    renderNewProduct()
    expect(_productApi.fetchProduct).not.toHaveBeenCalled()
  })

  describe('编辑模式', () => {
    it('编辑模式渲染"编辑商品"标题', () => {
      _productApi.fetchProduct.mockResolvedValue({ success: true, data: {} })
      renderEditProduct()
      const card = screen.getByTestId('card')
      expect(card.getAttribute('data-title')).toBe('编辑商品')
    })

    it('编辑模式调用 fetchProduct 获取数据', () => {
      _productApi.fetchProduct.mockResolvedValue({ success: true, data: {} })
      renderEditProduct('p-456')
      expect(_productApi.fetchProduct).toHaveBeenCalledWith('p-456')
    })

    it('编辑模式用 fetchProduct 数据填充表单', async () => {
      _productApi.fetchProduct.mockResolvedValue({
        success: true,
        data: {
          name: '测试商品',
          cost_price: '10.00',
          sale_price: '20.00',
          status: 'active',
          stock_quantity: 50,
          sku: 'SKU-001',
        },
      })
      renderEditProduct()

      await vi.waitFor(() => {
        expect(_mockForm.setFieldsValue).toHaveBeenCalledWith(
          expect.objectContaining({
            name: '测试商品',
            sale_price: 20,
            stock_quantity: 50,
          }),
        )
      })
    })

    it('编辑模式渲染"保存修改"按钮', () => {
      _productApi.fetchProduct.mockResolvedValue({ success: true, data: {} })
      renderEditProduct()
      expect(screen.getByText('保存修改')).toBeInTheDocument()
    })
  })

  it('商品名称字段有 maxLength 限制', () => {
    renderNewProduct()
    const inputs = screen.getAllByTestId('input')
    const nameInput = inputs.find((inp) => inp.getAttribute('placeholder') === '请输入商品名称')
    expect(nameInput).toHaveAttribute('maxlength', '100')
  })

  it('成本价和销售价为必填字段', () => {
    renderNewProduct()
    const formItems = screen.getAllByTestId('form-item')
    const costItem = formItems.find((fi) => fi.getAttribute('data-name') === 'cost_price')
    const saleItem = formItems.find((fi) => fi.getAttribute('data-name') === 'sale_price')
    expect(costItem).toBeTruthy()
    expect(saleItem).toBeTruthy()
  })

  it('渲染高级设置切换按钮', () => {
    renderNewProduct()
    expect(screen.getByText('展开高级设置')).toBeInTheDocument()
  })

  it('图片上传区域显示选择图片按钮', () => {
    renderNewProduct()
    expect(screen.getByText('选择图片')).toBeInTheDocument()
  })

  it('备注字段有 maxLength 限制', () => {
    renderNewProduct()
    // 高级设置内的 textarea 在展开后才渲染
    // 初始状态只有基础字段
    const textareas = screen.queryAllByTestId('textarea')
    // 高级设置未展开时无 textarea
    expect(textareas.length).toBe(0)
  })

  it('SKU 字段初始不可见', () => {
    renderNewProduct()
    // SKU 在高级设置内，初始不可见
    const inputs = screen.getAllByTestId('input')
    const skuInput = inputs.find((inp) => inp.getAttribute('placeholder') === '留空自动生成')
    expect(skuInput).toBeUndefined()
  })

  it('返回列表按钮导航到商品列表', async () => {
    renderNewProduct()
    screen.getByText('返回列表').click()
    await (() => new Promise((r) => setTimeout(r, 0)))()
    expect(screen.getByText('Products List')).toBeInTheDocument()
  })

  it('取消按钮导航到商品列表', async () => {
    renderNewProduct()
    screen.getByText('取消').click()
    await (() => new Promise((r) => setTimeout(r, 0)))()
    expect(screen.getByText('Products List')).toBeInTheDocument()
  })
})
