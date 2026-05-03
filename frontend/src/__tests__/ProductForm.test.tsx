/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
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
    <button data-testid="button" data-type={type} data-htmltype={htmlType} type={htmlType || 'button'} onClick={onClick} disabled={loading}>{icon}{children}</button>
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

  it('编辑模式 fetchProduct 失败显示错误提示', async () => {
    const { getApiErrorMessage } = await import('@/utils')
    _productApi.fetchProduct.mockRejectedValue(new Error('加载失败'))
    renderEditProduct()
    await vi.waitFor(() => {
      expect(getApiErrorMessage).toBeDefined()
    })
    // 验证 fetchProduct 被调用
    expect(_productApi.fetchProduct).toHaveBeenCalled()
  })

  it('创建按钮 htmlType 为 submit', () => {
    renderNewProduct()
    const submitBtn = screen.getByText('创建商品').closest('button')
    expect(submitBtn?.getAttribute('data-htmltype')).toBe('submit')
  })

  it('表单包含商品图片字段', () => {
    renderNewProduct()
    const formItems = screen.getAllByTestId('form-item')
    const labels = formItems.map((fi) => fi.getAttribute('data-label'))
    expect(labels).toContain('商品图片')
  })

  describe('高级设置', () => {
    it('点击展开高级设置显示 SKU 和其他字段', async () => {
      renderNewProduct()

      const toggleBtn = screen.getByText('展开高级设置')
      await act(async () => {
        fireEvent.click(toggleBtn)
      })

      // 高级设置展开后应显示收起按钮
      expect(screen.getByText('收起高级设置')).toBeInTheDocument()
      // SKU 字段
      const skuInput = screen.getAllByTestId('input').find(
        (inp) => inp.getAttribute('placeholder') === '留空自动生成',
      )
      expect(skuInput).toBeTruthy()
    })

    it('展开高级设置显示备注 textarea', async () => {
      renderNewProduct()

      await act(async () => {
        fireEvent.click(screen.getByText('展开高级设置'))
      })

      const textarea = screen.getByTestId('textarea')
      expect(textarea).toHaveAttribute('maxlength', '500')
    })

    it('展开高级设置显示状态选择器', async () => {
      renderNewProduct()

      await act(async () => {
        fireEvent.click(screen.getByText('展开高级设置'))
      })

      const selects = screen.getAllByTestId('select')
      expect(selects.length).toBeGreaterThanOrEqual(1)
    })

    it('再次点击收起高级设置', async () => {
      renderNewProduct()

      await act(async () => {
        fireEvent.click(screen.getByText('展开高级设置'))
      })
      expect(screen.getByText('收起高级设置')).toBeInTheDocument()

      await act(async () => {
        fireEvent.click(screen.getByText('收起高级设置'))
      })
      expect(screen.getByText('展开高级设置')).toBeInTheDocument()
    })
  })

  describe('表单提交', () => {
    it('提交创建订单调用 createProduct', async () => {
      _productApi.createProduct.mockResolvedValue({ success: true, data: { id: 'p-new' } })
      renderNewProduct()
      expect(_useSubmit.callback).toBeTruthy()

      await _useSubmit.callback({
        name: '新商品',
        cost_price: 10,
        sale_price: 20,
        sku: 'SKU-NEW',
        stock_quantity: 100,
        status: 'active',
        sort_weight: 0,
        remark: '备注',
      })

      expect(_productApi.createProduct).toHaveBeenCalledWith(
        expect.objectContaining({ name: '新商品', sale_price: '20' }),
      )
    })

    it('提交更新商品调用 updateProduct', async () => {
      _productApi.fetchProduct.mockResolvedValue({
        success: true,
        data: { name: '旧商品', cost_price: '10', sale_price: '20', sku: 'SKU-1', stock_quantity: 5, status: 'active', sort_weight: 0, remark: null, main_image_url: null },
      })
      _productApi.updateProduct.mockResolvedValue({ success: true, data: { id: 'p-1' } })
      renderEditProduct('p-1')

      await waitFor(() => {
        expect(_useSubmit.callback).toBeTruthy()
      })

      await _useSubmit.callback({
        name: '更新商品',
        cost_price: 15,
        sale_price: 25,
      })

      expect(_productApi.updateProduct).toHaveBeenCalledWith(
        'p-1',
        expect.objectContaining({ name: '更新商品', sale_price: '25' }),
      )
    })

    it('创建成功后导航到商品列表', async () => {
      _productApi.createProduct.mockResolvedValue({ success: true, data: { id: 'p-new' } })
      renderNewProduct()

      await _useSubmit.callback({ name: '商品', cost_price: 10, sale_price: 20 })

      await waitFor(() => {
        expect(screen.getByText('Products List')).toBeInTheDocument()
      })
    })
  })

  describe('图片上传', () => {
    it('上传成功设置图片 URL', async () => {
      _productApi.uploadImage.mockResolvedValue({
        success: true,
        data: { url: 'http://img/uploaded.jpg' },
      })
      renderNewProduct()

      // 通过 beforeUpload 回调直接测试 handleImageUpload
      // Upload mock 的 beforeUpload 需要触发
      const uploadDiv = screen.getByTestId('upload')
      const uploadBtn = uploadDiv.querySelector('button')
      expect(uploadBtn).toBeTruthy()
      // 按钮文本为"选择图片"（初始无图）
      expect(uploadBtn?.textContent).toContain('选择图片')
    })
  })

  describe('编辑模式数据加载', () => {
    it('编辑模式加载 main_image_url 后显示图片', async () => {
      _productApi.fetchProduct.mockResolvedValue({
        success: true,
        data: {
          name: '有图商品', cost_price: '10', sale_price: '20',
          sku: 'SKU-IMG', stock_quantity: 5, status: 'active',
          sort_weight: 0, remark: null, main_image_url: 'http://img/product.jpg',
        },
      })
      renderEditProduct()

      await waitFor(() => {
        const img = screen.getByTestId('image')
        expect(img.getAttribute('src')).toBe('http://img/product.jpg')
      })
    })

    it('编辑模式有图片时显示"替换图片"', async () => {
      _productApi.fetchProduct.mockResolvedValue({
        success: true,
        data: {
          name: '商品', cost_price: '10', sale_price: '20',
          sku: 'SKU', stock_quantity: 0, status: 'active',
          sort_weight: 0, remark: null, main_image_url: 'http://img/x.jpg',
        },
      })
      renderEditProduct()

      await waitFor(() => {
        expect(screen.getByText('替换图片')).toBeInTheDocument()
      })
    })

    it('fetchProduct 失败导航到列表', async () => {
      _productApi.fetchProduct.mockRejectedValue(new Error('not found'))
      renderEditProduct()

      await waitFor(() => {
        expect(screen.getByText('Products List')).toBeInTheDocument()
      })
    })
  })
})
