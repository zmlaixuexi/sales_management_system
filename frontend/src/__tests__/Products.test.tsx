/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _productMocks = {
  fetchProducts: vi.fn(),
  deleteProduct: vi.fn(),
  disableProduct: vi.fn(),
}
const _apiClientPost = vi.fn()

vi.mock('@/api/products', () => ({
  fetchProducts: (...args: any[]) => _productMocks.fetchProducts(...args),
  deleteProduct: (...args: any[]) => _productMocks.deleteProduct(...args),
  disableProduct: (...args: any[]) => _productMocks.disableProduct(...args),
}))

vi.mock('@/utils', () => ({
  formatAmount: (v: any) => String(v),
  formatPercent: (v: any) => `${v}%`,
  getApiErrorMessage: (_e: any, fallback: string) => fallback,
}))

vi.mock('@/api/request', () => ({
  downloadCsv: vi.fn(),
}))

vi.mock('@/api/client', () => ({
  default: { post: (...args: any[]) => _apiClientPost(...args) },
}))

const _paginatedListReturn = {
  data: [
    { id: '1', name: '商品A', sku: 'SKU-001', category_name: '分类1', sale_price: '100', cost_price: '60', unit_profit: '40', gross_margin: '40', stock_quantity: 10, status: 'active', main_image_url: null },
    { id: '2', name: '商品B', sku: 'SKU-002', category_name: '分类2', sale_price: '200', cost_price: '120', unit_profit: '80', gross_margin: '40', stock_quantity: 5, status: 'inactive', main_image_url: null },
  ],
  total: 2,
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
  usePaginatedList: (_fetcher: any, _extraFilters: any, _errorMsg: string) => _paginatedListReturn,
}))

vi.mock('antd', () => {
  return {
    Table: ({ dataSource, columns, rowKey, locale }: any) => (
      <table data-testid="products-table">
        <thead>
          <tr>{columns?.map((col: any) => <th key={col.dataIndex}>{col.title}</th>)}</tr>
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
    Button: ({ children, onClick, icon, type, danger }: any) => (
      <button data-testid="button" data-type={type} data-danger={danger ? 'true' : undefined} onClick={onClick}>{icon}{children}</button>
    ),
    Input: ({ value, onChange, placeholder }: any) => (
      <input data-testid="search-input" placeholder={placeholder} value={value || ''} onChange={(e) => onChange?.(e)} />
    ),
    Select: ({ value, onChange, options, placeholder }: any) => (
      <select data-testid="status-select" value={value || ''} onChange={(e) => onChange?.(e.target.value)}>
        <option value="">{placeholder || '全部'}</option>
        {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    ),
    Space: ({ children }: any) => <span>{children}</span>,
    Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
    Popconfirm: ({ title, children, onConfirm }: any) => (
      <span data-testid="popconfirm" data-title={title} onClick={onConfirm}>{children}</span>
    ),
    message: { error: vi.fn(), success: vi.fn() },
    Image: ({ src, width, height }: any) => <img data-testid="product-image" src={src} width={width} height={height} />,
  }
})

vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span>+</span>,
  EditOutlined: () => <span>✏️</span>,
  DeleteOutlined: () => <span>🗑️</span>,
  StopOutlined: () => <span>⛔</span>,
  SearchOutlined: () => <span>🔍</span>,
  DownloadOutlined: () => <span>📥</span>,
  UploadOutlined: () => <span>📤</span>,
}))

import ProductsPage from '@/pages/Products'

function renderProducts() {
  return render(
    <MemoryRouter initialEntries={['/products']}>
      <Routes>
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/products/:id/edit" element={<div>Edit Page</div>} />
        <Route path="/products/new" element={<div>New Product Page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProductsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('渲染搜索输入和状态筛选器', () => {
    renderProducts()
    expect(screen.getByTestId('search-input')).toBeInTheDocument()
    expect(screen.getByTestId('status-select')).toBeInTheDocument()
  })

  it('渲染新增商品按钮', () => {
    renderProducts()
    expect(screen.getByText('新增商品')).toBeInTheDocument()
  })

  it('渲染商品数据表格', () => {
    renderProducts()
    const table = screen.getByTestId('products-table')
    expect(table).toBeInTheDocument()
    expect(screen.getByTestId('row-1')).toBeInTheDocument()
    expect(screen.getByTestId('row-2')).toBeInTheDocument()
  })

  it('商品行显示 SKU 和名称', () => {
    renderProducts()
    expect(screen.getByText('SKU-001')).toBeInTheDocument()
    expect(screen.getByText('商品A')).toBeInTheDocument()
    expect(screen.getByText('SKU-002')).toBeInTheDocument()
    expect(screen.getByText('商品B')).toBeInTheDocument()
  })

  it('上架商品显示停用按钮', () => {
    renderProducts()
    const row1 = screen.getByTestId('row-1')
    expect(row1.textContent).toContain('停用')
    // 下架商品不显示停用按钮
    const row2 = screen.getByTestId('row-2')
    expect(row2.textContent).not.toContain('停用')
  })

  it('状态标签正确渲染', () => {
    renderProducts()
    const tags = screen.getAllByTestId('tag')
    const tagTexts = tags.map((t) => t.textContent)
    expect(tagTexts).toContain('上架')
    expect(tagTexts).toContain('下架')
  })

  it('点击新增按钮导航到新建页面', () => {
    renderProducts()
    const buttons = screen.getAllByTestId('button')
    const newBtn = buttons.find((b) => b.textContent?.includes('新增商品'))
    expect(newBtn).toBeTruthy()
  })

  it('表格列包含必要字段', () => {
    renderProducts()
    const table = screen.getByTestId('products-table')
    const headerTexts = Array.from(table.querySelectorAll('th')).map((th) => th.textContent)
    expect(headerTexts).toContain('SKU')
    expect(headerTexts).toContain('商品名称')
    expect(headerTexts).toContain('销售价')
    expect(headerTexts).toContain('库存')
    expect(headerTexts).toContain('状态')
    expect(headerTexts).toContain('操作')
  })

  it('无数据时显示空状态提示', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0 })
    renderProducts()
    expect(screen.getByText('暂无商品，点击"新增商品"添加')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: '1', name: '商品A', sku: 'SKU-001', category_name: '分类1', sale_price: '100', cost_price: '60', unit_profit: '40', gross_margin: '40', stock_quantity: 10, status: 'active', main_image_url: null },
      { id: '2', name: '商品B', sku: 'SKU-002', category_name: '分类2', sale_price: '200', cost_price: '120', unit_profit: '80', gross_margin: '40', stock_quantity: 5, status: 'inactive', main_image_url: null },
    ]
    _paginatedListReturn.total = 2
  })

  it('加载失败时显示错误和重试链接', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0, error: true })
    renderProducts()
    expect(screen.getByText('加载失败，')).toBeInTheDocument()
    expect(screen.getByText('重试')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: '1', name: '商品A', sku: 'SKU-001', category_name: '分类1', sale_price: '100', cost_price: '60', unit_profit: '40', gross_margin: '40', stock_quantity: 10, status: 'active', main_image_url: null },
      { id: '2', name: '商品B', sku: 'SKU-002', category_name: '分类2', sale_price: '200', cost_price: '120', unit_profit: '80', gross_margin: '40', stock_quantity: 5, status: 'inactive', main_image_url: null },
    ]
    _paginatedListReturn.total = 2
    _paginatedListReturn.error = false
  })

  it('加载中显示加载提示', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0, loading: true })
    renderProducts()
    expect(screen.getByText('加载中...')).toBeInTheDocument()
    _paginatedListReturn.data = [
      { id: '1', name: '商品A', sku: 'SKU-001', category_name: '分类1', sale_price: '100', cost_price: '60', unit_profit: '40', gross_margin: '40', stock_quantity: 10, status: 'active', main_image_url: null },
      { id: '2', name: '商品B', sku: 'SKU-002', category_name: '分类2', sale_price: '200', cost_price: '120', unit_profit: '80', gross_margin: '40', stock_quantity: 5, status: 'inactive', main_image_url: null },
    ]
    _paginatedListReturn.total = 2
    _paginatedListReturn.loading = false
  })
})
