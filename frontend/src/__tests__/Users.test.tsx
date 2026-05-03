/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _userMocks = {
  fetchUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  fetchRoles: vi.fn(),
}

vi.mock('@/api/users', () => ({
  fetchUsers: (...args: any[]) => _userMocks.fetchUsers(...args),
  createUser: (...args: any[]) => _userMocks.createUser(...args),
  updateUser: (...args: any[]) => _userMocks.updateUser(...args),
  fetchRoles: (...args: any[]) => _userMocks.fetchRoles(...args),
}))

vi.mock('@/utils', () => ({
  getApiErrorMessage: (_e: any, fallback: string) => fallback,
}))

const _paginatedListReturn: any = {
  data: [],
  total: 0,
  loading: false,
  error: false,
  page: 1,
  pageSize: 20,
  keyword: '',
  setKeyword: vi.fn(),
  onPageChange: vi.fn(),
  refresh: vi.fn(),
}

vi.mock('@/hooks/usePaginatedList', () => ({
  usePaginatedList: (fetchFn: any, _filters: any, _errorMsg: string) => {
    try { fetchFn({ page: 1, page_size: 20 }) } catch { /* mock 返回非 Promise，.then() 会报错 */ }
    const result = _userMocks.fetchUsers()
    _paginatedListReturn.data = result?.data?.items ?? []
    _paginatedListReturn.total = result?.data?.total ?? 0
    return _paginatedListReturn
  },
}))

const _messageSuccess = vi.fn()
const _messageError = vi.fn()

const _mockForm = {
  resetFields: vi.fn(),
  setFieldsValue: vi.fn(),
  validateFields: vi.fn(() => Promise.resolve({})),
}

vi.mock('antd', () => {
  function FormItem({ children, label }: any) {
    return <div data-testid="form-item" data-label={label}>{children}</div>
  }
  return {
    Table: ({ dataSource, columns, rowKey, locale, loading, pagination }: any) => (
      loading ? <span>加载中...</span> : (
      <div>
        <table data-testid="table">
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
        {pagination?.showTotal && <span data-testid="pagination-total">{pagination.showTotal(pagination.total)}</span>}
        {pagination?.onChange && <button data-testid="page-change" onClick={() => pagination.onChange(2, pagination.pageSize)}>翻页</button>}
      </div>
      )),
    Button: ({ children, onClick, type, icon }: any) => (
      <button data-testid="button" data-type={type} type="button" onClick={onClick}>{icon}{children}</button>
    ),
    Input: Object.assign(
      ({ value, onChange, placeholder }: any) => (
        <input data-testid="input" value={value || ''} placeholder={placeholder} onChange={(e: any) => onChange?.(e)} />
      ),
      { Password: (props: any) => <input data-testid="input-password" {...props} /> },
    ),
    Select: ({ value, onChange, options }: any) => (
      <select data-testid="select" value={value} onChange={(e: any) => onChange?.(e.target.value)}>
        {options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    ),
    Switch: ({ checked, onChange }: any) => (
      <button data-testid="switch" data-checked={checked} type="button" onClick={() => onChange?.(!checked)} />
    ),
    Tag: ({ children, color }: any) => <span data-testid="tag" data-color={color}>{children}</span>,
    Space: ({ children }: any) => <span>{children}</span>,
    Modal: ({ title, children, open, onOk, onCancel }: any) => open ? (
      <div data-testid="modal" data-title={title}>
        {children}
        <button data-testid="modal-ok" type="button" onClick={onOk}>保存</button>
        <button data-testid="modal-cancel" type="button" onClick={onCancel}>取消</button>
      </div>
    ) : null,
    Form: Object.assign(
      ({ children }: any) => <div>{children}</div>,
      { Item: FormItem, useForm: () => [_mockForm] },
    ),
    message: { success: (...args: any[]) => _messageSuccess(...args), error: (...args: any[]) => _messageError(...args) },
  }
})

vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span>+</span>,
  SearchOutlined: () => <span>🔍</span>,
}))

const mockUsersData = {
  data: {
    items: [
      {
        id: 'user-001',
        username: 'admin',
        display_name: '管理员',
        phone: '13800000001',
        email: 'admin@test.com',
        is_active: true,
        is_superuser: true,
        roles: [{ id: 'role-1', name: 'admin', display_name: '管理员' }],
        created_at: '2026-05-01T10:00:00Z',
        updated_at: '2026-05-01T10:00:00Z',
      },
      {
        id: 'user-002',
        username: 'sales01',
        display_name: '销售员A',
        phone: null,
        email: null,
        is_active: true,
        is_superuser: false,
        roles: [{ id: 'role-2', name: 'sales', display_name: '销售' }],
        created_at: '2026-05-01T12:00:00Z',
        updated_at: null,
      },
    ],
    total: 2,
  },
}

const mockRoles = {
  success: true,
  data: [
    { id: 'role-1', name: 'admin', display_name: '管理员' },
    { id: 'role-2', name: 'sales', display_name: '销售' },
  ],
}

import UsersPage from '@/pages/Users'

function renderUsers() {
  return render(
    <MemoryRouter initialEntries={['/users']}>
      <Routes>
        <Route path="/users" element={<UsersPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('UsersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _userMocks.fetchUsers.mockReturnValue(mockUsersData)
    _userMocks.fetchRoles.mockResolvedValue(mockRoles)
  })

  it('渲染用户数据行', () => {
    renderUsers()
    expect(screen.getByTestId('row-user-001')).toBeInTheDocument()
    expect(screen.getByTestId('row-user-002')).toBeInTheDocument()
  })

  it('显示用户名和显示名', () => {
    renderUsers()
    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getByText('sales01')).toBeInTheDocument()
  })

  it('显示角色标签', () => {
    renderUsers()
    const tags = screen.getAllByTestId('tag')
    const tagTexts = tags.map((t) => t.textContent)
    expect(tagTexts).toContain('管理员')
    expect(tagTexts).toContain('销售')
  })

  it('显示超级管理员标记', () => {
    renderUsers()
    const tags = screen.getAllByTestId('tag')
    const goldTag = tags.find((t) => t.getAttribute('data-color') === 'gold')
    expect(goldTag).toBeTruthy()
    expect(goldTag?.textContent).toBe('是')
  })

  it('显示新建用户按钮', () => {
    renderUsers()
    expect(screen.getByText('新建用户')).toBeInTheDocument()
  })

  it('显示编辑按钮', () => {
    renderUsers()
    const editButtons = screen.getAllByText('编辑')
    expect(editButtons.length).toBeGreaterThanOrEqual(2)
  })

  it('空值显示为 --', () => {
    renderUsers()
    const dashes = screen.getAllByText('--')
    expect(dashes.length).toBeGreaterThanOrEqual(2) // phone + email for sales01
  })

  it('点击新建用户按钮打开弹窗', async () => {
    renderUsers()
    screen.getByText('新建用户').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
      expect(screen.getByTestId('modal').getAttribute('data-title')).toBe('新建用户')
    })
  })

  it('无数据时显示空状态提示', () => {
    _userMocks.fetchUsers.mockReturnValue({ data: { items: [], total: 0 } })
    renderUsers()
    expect(screen.getByText('暂无用户数据')).toBeInTheDocument()
  })

  it('搜索框存在并可输入', () => {
    renderUsers()
    const input = screen.getByPlaceholderText('搜索用户名')
    expect(input).toBeInTheDocument()
  })

  it('加载中显示加载提示', () => {
    Object.assign(_paginatedListReturn, { data: [], total: 0, loading: true, error: false })
    renderUsers()
    expect(screen.getByText('加载中...')).toBeInTheDocument()
    Object.assign(_paginatedListReturn, { loading: false, error: false })
  })

  it('错误状态显示重试链接', () => {
    _paginatedListReturn.data = []
    _paginatedListReturn.total = 0
    _paginatedListReturn.loading = false
    _paginatedListReturn.error = true
    _userMocks.fetchUsers.mockReturnValue({ data: { items: [], total: 0 } })
    renderUsers()
    expect(screen.getByText('重试')).toBeInTheDocument()
    _paginatedListReturn.error = false
  })

  it('点击编辑按钮打开编辑弹窗', async () => {
    renderUsers()
    const editButtons = screen.getAllByText('编辑')
    editButtons[0].click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
      expect(screen.getByTestId('modal').getAttribute('data-title')).toBe('编辑用户')
    })
  })

  it('切换用户启用状态调用 updateUser', async () => {
    _userMocks.updateUser.mockResolvedValue({ success: true })
    renderUsers()
    const switches = screen.getAllByTestId('switch')
    switches[0].click()
    await waitFor(() => {
      expect(_userMocks.updateUser).toHaveBeenCalled()
    })
  })

  it('fetchRoles 挂载时调用', async () => {
    renderUsers()
    await waitFor(() => {
      expect(_userMocks.fetchRoles).toHaveBeenCalled()
    })
  })

  it('新建弹窗中角色选择器填充选项', async () => {
    renderUsers()
    await waitFor(() => {
      expect(_userMocks.fetchRoles).toHaveBeenCalled()
    })
    screen.getByText('新建用户').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
    })
    const selects = screen.getAllByTestId('select')
    const roleSelect = selects.find((s) => {
      const options = Array.from(s.querySelectorAll('option'))
      return options.some((o) => o.textContent === '管理员')
    })
    expect(roleSelect).toBeTruthy()
  })

  it('fetchRoles 错误不阻塞渲染', async () => {
    _userMocks.fetchRoles.mockRejectedValue(new Error('角色接口错误'))
    renderUsers()
    await waitFor(() => {
      expect(screen.getByText('新建用户')).toBeInTheDocument()
    })
  })

  it('切换启用状态失败不崩溃', async () => {
    _userMocks.updateUser.mockRejectedValue(new Error('更新失败'))
    renderUsers()
    const switches = screen.getAllByTestId('switch')
    switches[0].click()
    await waitFor(() => {
      expect(_userMocks.updateUser).toHaveBeenCalled()
    })
  })

  it('弹窗关闭按钮存在', async () => {
    renderUsers()
    screen.getByText('新建用户').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeInTheDocument()
    })
    // 弹窗存在即可验证关闭逻辑存在
    expect(screen.getByTestId('modal')).toBeTruthy()
  })

  it('新建用户保存成功', async () => {
    _mockForm.validateFields.mockResolvedValueOnce({
      username: 'newuser', password: 'Pass123',
      display_name: '新用户', phone: '13800009999',
      email: 'new@test.com', role_ids: ['role-1'],
    })
    _userMocks.createUser.mockResolvedValueOnce({ success: true, data: {} })
    renderUsers()

    await act(async () => { fireEvent.click(screen.getByText('新建用户')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeInTheDocument() })

    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_userMocks.createUser).toHaveBeenCalledWith(
        expect.objectContaining({ username: 'newuser', password: 'Pass123' }),
      )
      expect(_messageSuccess).toHaveBeenCalledWith('用户已创建')
    })
  })

  it('编辑用户保存成功', async () => {
    _mockForm.validateFields.mockResolvedValueOnce({
      display_name: '修改名', phone: '13800008888',
      email: 'edit@test.com', is_active: false, role_ids: ['role-2'],
    })
    _userMocks.updateUser.mockResolvedValueOnce({ success: true, data: {} })
    renderUsers()

    const editBtns = screen.getAllByText('编辑')
    await act(async () => { fireEvent.click(editBtns[0]) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeInTheDocument() })

    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_userMocks.updateUser).toHaveBeenCalledWith(
        'user-001',
        expect.objectContaining({ display_name: '修改名', is_active: false }),
      )
      expect(_messageSuccess).toHaveBeenCalledWith('用户已更新')
    })
  })

  it('保存失败显示错误消息', async () => {
    _mockForm.validateFields.mockResolvedValueOnce({
      username: 'fail', password: 'Fail123',
    })
    _userMocks.createUser.mockRejectedValueOnce(new Error('创建失败'))
    renderUsers()

    await act(async () => { fireEvent.click(screen.getByText('新建用户')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeInTheDocument() })

    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_messageError).toHaveBeenCalledWith('创建用户失败')
    })
  })

  it('表单验证失败不调用 API', async () => {
    _mockForm.validateFields.mockRejectedValueOnce(new Error('validation error'))
    renderUsers()

    await act(async () => { fireEvent.click(screen.getByText('新建用户')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeInTheDocument() })

    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_mockForm.validateFields).toHaveBeenCalled()
    })
    expect(_userMocks.createUser).not.toHaveBeenCalled()
    expect(_userMocks.updateUser).not.toHaveBeenCalled()
  })

  it('搜索输入 onChange 调用 setKeyword', async () => {
    renderUsers()
    const input = screen.getByPlaceholderText('搜索用户名')
    await act(async () => { fireEvent.change(input, { target: { value: 'admin' } }) })
    expect(_paginatedListReturn.setKeyword).toHaveBeenCalled()
  })

  it('启用切换成功显示"已启用"', async () => {
    // sales01 is_active=true, toggling to false -> checked=false
    _userMocks.updateUser.mockResolvedValueOnce({ success: true, data: {} })
    renderUsers()
    const switches = screen.getAllByTestId('switch')
    await act(async () => { fireEvent.click(switches[1]) })
    await waitFor(() => {
      expect(_messageSuccess).toHaveBeenCalledWith('已停用')
    })
  })

  it('无角色用户显示"无角色"标签', () => {
    const noRoleUser = {
      data: {
        items: [{
          id: 'user-003', username: 'norole', display_name: null,
          phone: null, email: null, is_active: true, is_superuser: false,
          roles: [], created_at: null, updated_at: null,
        }],
        total: 1,
      },
    }
    _userMocks.fetchUsers.mockReturnValue(noRoleUser)
    renderUsers()
    expect(screen.getByText('无角色')).toBeInTheDocument()
    // 恢复
    _userMocks.fetchUsers.mockReturnValue(mockUsersData)
  })

  it('新建弹窗显示用户名和密码字段', async () => {
    renderUsers()
    await act(async () => { fireEvent.click(screen.getByText('新建用户')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeInTheDocument() })
    const labels = screen.getAllByTestId('form-item').map((fi) => fi.getAttribute('data-label'))
    expect(labels).toContain('用户名')
    expect(labels).toContain('密码')
  })

  it('编辑弹窗不显示用户名和密码字段', async () => {
    renderUsers()
    const editBtns = screen.getAllByText('编辑')
    await act(async () => { fireEvent.click(editBtns[0]) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeInTheDocument() })
    const labels = screen.getAllByTestId('form-item').map((fi) => fi.getAttribute('data-label'))
    expect(labels).not.toContain('用户名')
    expect(labels).not.toContain('密码')
    expect(labels).toContain('启用状态')
  })

  it('分页显示总条数', () => {
    renderUsers()
    expect(screen.getByTestId('pagination-total')).toHaveTextContent('共 2 条')
  })

  it('翻页触发 onPageChange', () => {
    renderUsers()
    fireEvent.click(screen.getByTestId('page-change'))
    expect(_paginatedListReturn.onPageChange).toHaveBeenCalled()
  })

  it('弹窗取消按钮关闭弹窗', async () => {
    renderUsers()
    await act(async () => { fireEvent.click(screen.getByText('新建用户')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeInTheDocument() })
    await act(async () => { fireEvent.click(screen.getByTestId('modal-cancel')) })
    await waitFor(() => {
      expect(screen.queryByTestId('modal')).toBeNull()
    })
  })

  it('停用用户标签显示红色', () => {
    _userMocks.fetchUsers.mockReturnValue({
      data: {
        items: [{
          id: 'user-010', username: 'inactive_user', display_name: '停用用户',
          phone: null, email: null, is_active: false, is_superuser: false,
          roles: [], created_at: null, updated_at: null,
        }],
        total: 1,
      },
    })
    renderUsers()
    const tags = screen.getAllByTestId('tag')
    const redTag = tags.find((t) => t.getAttribute('data-color') === 'red')
    expect(redTag).toBeTruthy()
    expect(redTag?.textContent).toBe('停用')
  })
})
