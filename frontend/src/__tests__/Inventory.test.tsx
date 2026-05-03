/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _inventoryMocks = {
  fetchInventoryMovements: vi.fn(),
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

vi.mock('@/api/inventory', () => ({
  fetchInventoryMovements: (...args: any[]) => _inventoryMocks.fetchInventoryMovements(...args),
}))

vi.mock('@/hooks/usePaginatedList', () => ({
  usePaginatedList: (_fetchFn: any, _filters: any, _errorMsg: string) => {
    const result = _inventoryMocks.fetchInventoryMovements()
    _paginatedListReturn.data = result?.data?.items ?? []
    _paginatedListReturn.total = result?.data?.total ?? 0
    return _paginatedListReturn
  },
}))

vi.mock('antd', () => ({
  Table: ({ dataSource, columns, rowKey, locale, loading, pagination }: any) => (
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
      {pagination?.showTotal && <span data-testid="pagination-total">{pagination.showTotal(pagination.total)}</span>}
      {pagination?.onChange && (
        <button data-testid="page-change" onClick={() => pagination.onChange(2, pagination.pageSize)}>翻页</button>
      )}
    </div>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  message: { error: vi.fn(), success: vi.fn() },
}))

import InventoryPage from '@/pages/Inventory'

const mockData = {
  data: {
    items: [
      {
        id: 'mov-001',
        product_id: 'prod-001',
        movement_type: 'order_deduct',
        quantity_before: 100,
        quantity_change: -5,
        quantity_after: 95,
        related_type: 'sales_order',
        related_id: 'order-001',
        remark: '订单扣减库存',
        created_at: '2026-05-01T10:00:00Z',
      },
      {
        id: 'mov-002',
        product_id: 'prod-002',
        movement_type: 'manual_adjust',
        quantity_before: 50,
        quantity_change: 10,
        quantity_after: 60,
        related_type: null,
        related_id: null,
        remark: null,
        created_at: '2026-05-01T12:00:00Z',
      },
    ],
    total: 2,
  },
}

function renderInventory() {
  return render(
    <MemoryRouter initialEntries={['/inventory']}>
      <Routes>
        <Route path="/inventory" element={<InventoryPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('InventoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _inventoryMocks.fetchInventoryMovements.mockReturnValue(mockData)
  })

  it('渲染页面标题', () => {
    renderInventory()
    expect(screen.getByText('库存流水')).toBeInTheDocument()
  })

  it('显示总记录数', () => {
    renderInventory()
    expect(screen.getByText(/共 2 条记录/)).toBeInTheDocument()
  })

  it('渲染库存变动行', () => {
    renderInventory()
    expect(screen.getByTestId('row-mov-001')).toBeInTheDocument()
    expect(screen.getByTestId('row-mov-002')).toBeInTheDocument()
  })

  it('显示变动类型标签', () => {
    renderInventory()
    expect(screen.getByText('订单扣减')).toBeInTheDocument()
    expect(screen.getByText('手动调整')).toBeInTheDocument()
  })

  it('变动量正数显示绿色 + 号', () => {
    renderInventory()
    expect(screen.getByText('+10')).toBeInTheDocument()
  })

  it('变动量负数显示红色', () => {
    renderInventory()
    const negEl = screen.getByText('-5')
    expect(negEl).toBeInTheDocument()
  })

  it('显示关联类型', () => {
    renderInventory()
    expect(screen.getByText('销售订单')).toBeInTheDocument()
  })

  it('空数据显示空状态', () => {
    _inventoryMocks.fetchInventoryMovements.mockReturnValue({ data: { items: [], total: 0 } })
    renderInventory()
    expect(screen.getByText('暂无库存变动记录')).toBeInTheDocument()
  })

  it('加载中显示加载提示', () => {
    _paginatedListReturn.loading = true
    _paginatedListReturn.data = []
    _inventoryMocks.fetchInventoryMovements.mockReturnValue({ data: { items: [], total: 0 } })
    renderInventory()
    expect(screen.getByText('加载中...')).toBeInTheDocument()
    _paginatedListReturn.loading = false
  })

  it('错误状态显示重试链接', () => {
    _paginatedListReturn.loading = false
    _paginatedListReturn.error = true
    _paginatedListReturn.data = []
    _inventoryMocks.fetchInventoryMovements.mockReturnValue({ data: { items: [], total: 0 } })
    renderInventory()
    expect(screen.getByText('重试')).toBeInTheDocument()
    _paginatedListReturn.error = false
  })

  it('空备注显示为 --', () => {
    renderInventory()
    const row = screen.getByTestId('row-mov-002')
    expect(row.textContent).toContain('--')
  })

  it('未知变动类型显示原始值', () => {
    const customData = {
      data: {
        items: [{
          id: 'mov-003', product_id: 'prod-003', movement_type: 'unknown_type',
          quantity_before: 10, quantity_change: 0, quantity_after: 10,
          related_type: null, related_id: null, remark: null, created_at: '2026-05-01T00:00:00Z',
        }],
        total: 1,
      },
    }
    _inventoryMocks.fetchInventoryMovements.mockReturnValue(customData)
    renderInventory()
    expect(screen.getByText('unknown_type')).toBeInTheDocument()
  })

  it('未知关联类型显示原始值', () => {
    const customData = {
      data: {
        items: [{
          id: 'mov-004', product_id: 'prod-004', movement_type: 'manual_adjust',
          quantity_before: 20, quantity_change: 5, quantity_after: 25,
          related_type: 'purchase_order', related_id: 'po-001', remark: null, created_at: '2026-05-01T00:00:00Z',
        }],
        total: 1,
      },
    }
    _inventoryMocks.fetchInventoryMovements.mockReturnValue(customData)
    renderInventory()
    expect(screen.getByText('purchase_order')).toBeInTheDocument()
  })

  it('变动量为 0 时无正负前缀', () => {
    const customData = {
      data: {
        items: [{
          id: 'mov-005', product_id: 'prod-005', movement_type: 'manual_adjust',
          quantity_before: 30, quantity_change: 0, quantity_after: 30,
          related_type: null, related_id: null, remark: null, created_at: '2026-05-01T00:00:00Z',
        }],
        total: 1,
      },
    }
    _inventoryMocks.fetchInventoryMovements.mockReturnValue(customData)
    renderInventory()
    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('空关联类型显示 --', () => {
    renderInventory()
    const row = screen.getByTestId('row-mov-002')
    // mov-002 的 related_type 为 null
    const cells = row.querySelectorAll('td')
    const relatedCell = Array.from(cells).find((td) => td.getAttribute('data-col') === 'related_type')
    expect(relatedCell?.textContent).toBe('--')
  })

  it('分页显示总条数', () => {
    renderInventory()
    expect(screen.getByTestId('pagination-total')).toBeInTheDocument()
    expect(screen.getByTestId('pagination-total').textContent).toBe('共 2 条')
  })

  it('翻页调用 onPageChange', async () => {
    renderInventory()
    const pageBtn = screen.getByTestId('page-change')
    await act(async () => { fireEvent.click(pageBtn) })
    expect(_paginatedListReturn.onPageChange).toHaveBeenCalledWith(2, 20)
  })

  it('时间列格式化显示', () => {
    renderInventory()
    // created_at 列经过 render 函数格式化
    const row = screen.getByTestId('row-mov-001')
    expect(row.textContent).toContain('2026')
  })

  it('变动量正数颜色为绿色', () => {
    renderInventory()
    const posEl = screen.getByText('+10')
    expect(posEl).toBeInTheDocument()
    expect(posEl.style.color).toBe('rgb(82, 196, 26)')
  })

  it('变动量负数颜色为红色', () => {
    renderInventory()
    const negEl = screen.getByText('-5')
    expect(negEl).toBeInTheDocument()
    expect(negEl.style.color).toBe('rgb(255, 77, 79)')
  })

  it('重试链接调用 refresh', async () => {
    _paginatedListReturn.loading = false
    _paginatedListReturn.error = true
    _paginatedListReturn.data = []
    _inventoryMocks.fetchInventoryMovements.mockReturnValue({ data: { items: [], total: 0 } })
    renderInventory()
    const retryLink = screen.getByText('重试')
    await act(async () => { fireEvent.click(retryLink) })
    expect(_paginatedListReturn.refresh).toHaveBeenCalled()
    _paginatedListReturn.error = false
  })
})
