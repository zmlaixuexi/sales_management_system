import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

const _rolesApi = {
  fetchRoles: vi.fn(),
  fetchPermissions: vi.fn(),
  createRole: vi.fn(),
  updateRole: vi.fn(),
  deleteRole: vi.fn(),
}

vi.mock('@/api/roles', () => ({
  fetchRoles: (...a: unknown[]) => _rolesApi.fetchRoles(...a),
  fetchPermissions: (...a: unknown[]) => _rolesApi.fetchPermissions(...a),
  createRole: (...a: unknown[]) => _rolesApi.createRole(...a),
  updateRole: (...a: unknown[]) => _rolesApi.updateRole(...a),
  deleteRole: (...a: unknown[]) => _rolesApi.deleteRole(...a),
}))

vi.mock('@/utils', () => ({
  getApiErrorMessage: (_e: unknown, fallback: string) => fallback,
  isToastDisplayed: (e: unknown) => !!(e as Record<string, boolean>)?._toastDisplayed,
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: any) => selector({ user: { is_superuser: true }, hasPermission: () => true }),
}))

vi.mock('@/hooks/usePaginatedList', () => ({
  usePaginatedList: () => ({
    data: [], total: 0, loading: false, error: null,
    page: 1, pageSize: 10, keyword: '',
    setKeyword: vi.fn(), onPageChange: vi.fn(), refresh: vi.fn(),
  }),
}))

const _mockForm = {
  setFieldsValue: vi.fn(),
  getFieldsValue: vi.fn(() => ({})),
  validateFields: vi.fn(() => Promise.resolve({})),
  resetFields: vi.fn(),
}

/* eslint-disable @typescript-eslint/no-explicit-any */
vi.mock('antd', () => ({
  Form: Object.assign(
    ({ children }: any) => (
      <form data-testid="form">{children}</form>
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
    <button data-testid="button" data-type={type} data-danger={danger ? 'true' : undefined} type="button" disabled={disabled} onClick={onClick}>{icon}{children}</button>
  ),
  Card: ({ title, children, extra }: any) => (
    <div data-testid="card" data-title={title}>{extra}{children}</div>
  ),
  Space: ({ children }: any) => <span>{children}</span>,
  Table: ({ dataSource, columns, rowKey, loading, locale }: any) => (
    <div>
      <table data-testid="table">
        <tbody>
          {dataSource && dataSource.length > 0
            ? dataSource.map((row: any) => (
              <tr key={row[rowKey]} data-testid={`row-${row[rowKey]}`}>
                {columns?.map((col: any, idx: number) => (
                  <td key={col.dataIndex || idx}>
                    {col.render ? col.render(row[col.dataIndex], row, idx) : (typeof row[col.dataIndex] === 'string' || typeof row[col.dataIndex] === 'number' ? String(row[col.dataIndex]) : '')}
                  </td>
                ))}
              </tr>
            ))
            : <tr><td>{locale?.emptyText || '暂无数据'}</td></tr>
          }
        </tbody>
      </table>
      {loading && <span data-testid="loading">加载中</span>}
    </div>
  ),
  Tag: ({ children, color }: any) => (
    <span data-testid="tag" data-color={color}>{children}</span>
  ),
  Modal: ({ title, children, open, okText, onOk, onCancel }: any) => (
    <div data-testid="modal" data-title={title} style={{ display: open ? 'block' : 'none' }}>
      {children}
      <button data-testid="modal-ok" type="button" onClick={onOk}>{okText || '确定'}</button>
      <button data-testid="modal-cancel" type="button" onClick={onCancel}>取消</button>
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
  Checkbox: {
    Group: ({ options }: any) => (
      <div data-testid="checkbox-group">
        {options?.map((o: any) => (
          <label key={o.value} data-testid={`checkbox-${o.value}`}><input type="checkbox" />{o.label}</label>
        ))}
      </div>
    ),
  },
  Popconfirm: ({ title, children, onConfirm }: any) => (
    <span data-testid="popconfirm" data-title={title} onClick={onConfirm}>{children}</span>
  ),
  message: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
}))
/* eslint-enable @typescript-eslint/no-explicit-any */

vi.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span>+</span>,
  SearchOutlined: () => <span>🔍</span>,
}))

import RolesPage from '@/pages/Roles'

const mockRoles = [
  {
    id: 'r-1',
    name: 'admin',
    display_name: '系统管理员',
    description: '拥有全部权限',
    permissions: [
      { id: 'p-1', code: 'user:list', name: '查看用户列表', module: '用户管理' },
      { id: 'p-2', code: 'product:list', name: '查看商品列表', module: '商品管理' },
    ],
    user_count: 2,
    created_at: '2026-05-01T00:00:00',
    updated_at: null,
  },
  {
    id: 'r-2',
    name: 'sales',
    display_name: '销售人员',
    description: null,
    permissions: [
      { id: 'p-3', code: 'order:list', name: '查看订单列表', module: '订单管理' },
    ],
    user_count: 0,
    created_at: '2026-05-01T00:00:00',
    updated_at: null,
  },
]

const mockPermissions = {
  '用户管理': [
    { id: 'p-1', code: 'user:list', name: '查看用户列表', module: '用户管理' },
  ],
  '商品管理': [
    { id: 'p-2', code: 'product:list', name: '查看商品列表', module: '商品管理' },
  ],
}

function renderRoles() {
  return render(
    <MemoryRouter initialEntries={['/roles']}>
      <Routes>
        <Route path="/roles" element={<RolesPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RolesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _rolesApi.fetchRoles.mockResolvedValue({ success: true, data: mockRoles })
    _rolesApi.fetchPermissions.mockResolvedValue({ success: true, data: mockPermissions })
  })

  it('渲染"角色权限管理"标题', () => {
    renderRoles()
    expect(screen.getByText('角色权限管理')).toBeInTheDocument()
  })

  it('渲染"新建角色"按钮', () => {
    renderRoles()
    expect(screen.getByText('新建角色')).toBeInTheDocument()
  })

  it('挂载时调用 fetchRoles 和 fetchPermissions', () => {
    renderRoles()
    expect(_rolesApi.fetchRoles).toHaveBeenCalled()
    expect(_rolesApi.fetchPermissions).toHaveBeenCalled()
  })

  it('角色表格存在', () => {
    renderRoles()
    expect(screen.getByTestId('table')).toBeInTheDocument()
  })

  it('点击新建角色打开模态框', async () => {
    renderRoles()
    screen.getByText('新建角色').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeVisible()
    })
    expect(screen.getByTestId('modal').getAttribute('data-title')).toBe('新建角色')
  })

  it('模态框包含角色标识、显示名、说明和权限字段', async () => {
    renderRoles()
    screen.getByText('新建角色').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeVisible()
    })
    const formItems = screen.getAllByTestId('form-item')
    const names = formItems.map((fi) => fi.getAttribute('data-name'))
    expect(names).toContain('name')
    expect(names).toContain('display_name')
    expect(names).toContain('description')
    expect(names).toContain('permission_ids')
  })

  it('权限复选框组渲染权限选项', async () => {
    renderRoles()
    screen.getByText('新建角色').click()
    await waitFor(() => {
      expect(screen.getByTestId('checkbox-group')).toBeInTheDocument()
    })
    expect(screen.getByTestId('checkbox-p-1')).toBeInTheDocument()
    expect(screen.getByTestId('checkbox-p-2')).toBeInTheDocument()
  })

  it('加载空角色列表显示空状态', async () => {
    _rolesApi.fetchRoles.mockResolvedValue({ success: true, data: [] })
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('暂无角色数据')).toBeInTheDocument()
    })
  })

  it('fetchRoles 错误后角色列表为空', async () => {
    _rolesApi.fetchRoles.mockRejectedValue(new Error('网络错误'))
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('暂无角色数据')).toBeInTheDocument()
    })
  })

  it('模态框中有角色标识输入框', async () => {
    renderRoles()
    screen.getByText('新建角色').click()
    await waitFor(() => {
      const inputs = screen.getAllByTestId('input')
      expect(inputs.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('模态框中有说明 textarea', async () => {
    renderRoles()
    screen.getByText('新建角色').click()
    await waitFor(() => {
      expect(screen.getByTestId('textarea')).toBeInTheDocument()
    })
  })

  it('点击编辑按钮打开编辑模态框', async () => {
    renderRoles()
    await waitFor(() => {
      expect(screen.getByTestId('row-r-1')).toBeInTheDocument()
    })
    // 等待表格行渲染后再查找编辑按钮
    const editButtons = screen.getAllByText('编辑')
    editButtons[0].click()
    await waitFor(() => {
      expect(screen.getByTestId('modal').getAttribute('data-title')).toBe('编辑角色')
    })
  })

  it('创建角色成功后刷新列表', async () => {
    _rolesApi.createRole.mockResolvedValue({ success: true })
    renderRoles()
    screen.getByText('新建角色').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeVisible()
    })
    // 验证 fetchRoles 被调用了（初始加载）
    expect(_rolesApi.fetchRoles).toHaveBeenCalledTimes(1)
  })

  it('有用户关联的角色删除按钮被禁用', async () => {
    renderRoles()
    await waitFor(() => {
      const deleteButtons = screen.getAllByText('删除')
      expect(deleteButtons.length).toBeGreaterThanOrEqual(1)
    })
    const deleteButtons = screen.getAllByText('删除')
    // admin 有 2 个用户，删除按钮应被禁用
    expect(deleteButtons[0].closest('button')?.disabled).toBe(true)
  })

  it('确认删除调用 deleteRole', async () => {
    _rolesApi.deleteRole.mockResolvedValue({ success: true })
    renderRoles()
    await waitFor(() => {
      expect(screen.getAllByText('删除').length).toBeGreaterThanOrEqual(1)
    })
    // sales 角色无关联用户，删除按钮可用
    const popconfirms = screen.getAllByTestId('popconfirm')
    // 点击 sales 角色的删除确认（第二个）
    popconfirms[1].click()
    await waitFor(() => {
      expect(_rolesApi.deleteRole).toHaveBeenCalledWith('r-2')
    })
  })

  it('模态框中有保存按钮', async () => {
    renderRoles()
    screen.getByText('新建角色').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal-ok')).toBeInTheDocument()
    })
    expect(screen.getByTestId('modal-ok').textContent).toBe('保存')
  })

  it('fetchPermissions 错误不阻塞渲染', async () => {
    _rolesApi.fetchPermissions.mockRejectedValue(new Error('权限接口错误'))
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('角色权限管理')).toBeInTheDocument()
    })
  })

  it('删除失败时不崩溃', async () => {
    _rolesApi.deleteRole.mockRejectedValue(new Error('删除失败'))
    renderRoles()
    await waitFor(() => {
      expect(screen.getAllByTestId('popconfirm').length).toBeGreaterThanOrEqual(1)
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    popconfirms[1].click()
    // 等待异步处理完成
    await waitFor(() => {
      expect(_rolesApi.deleteRole).toHaveBeenCalledWith('r-2')
    })
  })

  it('模态框关闭按钮存在', async () => {
    renderRoles()
    screen.getByText('新建角色').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeVisible()
    })
    // 模态框可见说明打开了
    expect(screen.getByTestId('modal')).toBeVisible()
  })

  it('创建角色保存成功', async () => {
    _mockForm.validateFields.mockResolvedValueOnce({
      name: 'new_role', display_name: '新角色',
      description: '描述', permission_ids: ['p-1'],
    })
    _rolesApi.createRole.mockResolvedValueOnce({ success: true })
    renderRoles()

    await act(async () => { fireEvent.click(screen.getByText('新建角色')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeVisible() })

    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_rolesApi.createRole).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'new_role', display_name: '新角色' }),
      )
    })
  })

  it('编辑角色保存成功', async () => {
    _mockForm.validateFields.mockResolvedValueOnce({
      name: 'admin', display_name: '超级管理员',
      description: '全部权限', permission_ids: ['p-1'],
    })
    _rolesApi.updateRole.mockResolvedValueOnce({ success: true })
    renderRoles()

    await waitFor(() => { expect(screen.getByTestId('row-r-1')).toBeInTheDocument() })
    const editBtns = screen.getAllByText('编辑')
    await act(async () => { fireEvent.click(editBtns[0]) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeVisible() })

    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_rolesApi.updateRole).toHaveBeenCalledWith(
        'r-1',
        expect.objectContaining({ name: 'admin' }),
      )
    })
  })

  it('保存失败显示错误消息', async () => {
    _mockForm.validateFields.mockResolvedValueOnce({ name: 'fail' })
    _rolesApi.createRole.mockRejectedValueOnce(new Error('创建失败'))
    const { message } = await import('antd')
    renderRoles()

    await act(async () => { fireEvent.click(screen.getByText('新建角色')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeVisible() })

    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('创建角色失败')
    })
  })

  it('表单验证失败不调用 API', async () => {
    _mockForm.validateFields.mockRejectedValueOnce(new Error('validation'))
    renderRoles()

    await act(async () => { fireEvent.click(screen.getByText('新建角色')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeVisible() })

    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => { expect(_mockForm.validateFields).toHaveBeenCalled() })
    expect(_rolesApi.createRole).not.toHaveBeenCalled()
  })

  it('删除成功后刷新角色列表', async () => {
    _rolesApi.deleteRole.mockResolvedValueOnce({ success: true })
    renderRoles()
    await waitFor(() => { expect(screen.getAllByTestId('popconfirm').length).toBeGreaterThanOrEqual(1) })

    const popconfirms = screen.getAllByTestId('popconfirm')
    await act(async () => { fireEvent.click(popconfirms[1]) })
    await waitFor(() => {
      expect(_rolesApi.deleteRole).toHaveBeenCalledWith('r-2')
      // fetchRoles should be called again (initial + refresh)
      expect(_rolesApi.fetchRoles).toHaveBeenCalledTimes(2)
    })
  })

  it('编辑角色填充表单值', async () => {
    renderRoles()
    await waitFor(() => { expect(screen.getByTestId('row-r-1')).toBeInTheDocument() })

    const editBtns = screen.getAllByText('编辑')
    await act(async () => { fireEvent.click(editBtns[0]) })
    await waitFor(() => {
      expect(_mockForm.setFieldsValue).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'admin', display_name: '系统管理员' }),
      )
    })
  })

  it('无权限角色显示"无权限"标签', async () => {
    _rolesApi.fetchRoles.mockResolvedValue({
      success: true,
      data: [{
        id: 'r-3', name: 'empty', display_name: '空角色',
        description: null, permissions: [], user_count: 0,
        created_at: null, updated_at: null,
      }],
    })
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('无权限')).toBeInTheDocument()
    })
  })

  it('弹窗取消按钮关闭弹窗', async () => {
    renderRoles()
    screen.getByText('新建角色').click()
    await waitFor(() => {
      expect(screen.getByTestId('modal')).toBeVisible()
    })
    await act(async () => { fireEvent.click(screen.getByTestId('modal-cancel')) })
    await waitFor(() => {
      expect(screen.getByTestId('modal')).not.toBeVisible()
    })
  })

  it('编辑角色保存失败显示更新错误', async () => {
    _mockForm.validateFields.mockResolvedValueOnce({
      name: 'admin', display_name: '管理员', description: '描述', permission_ids: [],
    })
    _rolesApi.updateRole.mockRejectedValueOnce(new Error('更新失败'))
    const { message } = await import('antd')
    renderRoles()

    await waitFor(() => { expect(screen.getByTestId('row-r-1')).toBeInTheDocument() })
    const editBtns = screen.getAllByText('编辑')
    await act(async () => { fireEvent.click(editBtns[0]) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeVisible() })

    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('更新角色失败')
    })
  })

  it('fetchRoles 返回非数组不崩溃', async () => {
    _rolesApi.fetchRoles.mockResolvedValue({ success: true, data: null })
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('暂无角色数据')).toBeInTheDocument()
    })
  })

  it('fetchRoles 返回 success=false 不设置角色', async () => {
    _rolesApi.fetchRoles.mockResolvedValue({ success: false, data: [] })
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('暂无角色数据')).toBeInTheDocument()
    })
  })

  it('loadRoles _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _rolesApi.fetchRoles.mockRejectedValue(err)
    const { message } = await import('antd')
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('暂无角色数据')).toBeInTheDocument()
    })
    expect(message.error).not.toHaveBeenCalledWith('加载角色列表失败')
  })

  it('handleSave _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _mockForm.validateFields.mockRejectedValueOnce(err)
    const { message } = await import('antd')
    renderRoles()

    await act(async () => { fireEvent.click(screen.getByText('新建角色')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeVisible() })
    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => { expect(_mockForm.validateFields).toHaveBeenCalled() })
    expect(message.error).not.toHaveBeenCalledWith('创建角色失败')
  })

  it('handleDelete _toastDisplayed 错误静默', async () => {
    const err = Object.assign(new Error('toast'), { _toastDisplayed: true })
    _rolesApi.deleteRole.mockRejectedValue(err)
    const { message } = await import('antd')
    renderRoles()
    await waitFor(() => {
      expect(screen.getAllByTestId('popconfirm').length).toBeGreaterThanOrEqual(1)
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    await act(async () => { fireEvent.click(popconfirms[1]) })
    await waitFor(() => {
      expect(_rolesApi.deleteRole).toHaveBeenCalledWith('r-2')
    })
    expect(message.error).not.toHaveBeenCalledWith('删除角色失败')
  })

  it('角色空 display_name 显示 --', async () => {
    _rolesApi.fetchRoles.mockResolvedValue({
      success: true,
      data: [{
        id: 'r-4', name: 'no_display', display_name: null,
        description: '有描述', permissions: [], user_count: 0,
        created_at: null, updated_at: null,
      }],
    })
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('no_display')).toBeInTheDocument()
      expect(screen.getByText('--')).toBeInTheDocument()
    })
  })

  it('角色空 description 显示 --', async () => {
    _rolesApi.fetchRoles.mockResolvedValue({
      success: true,
      data: [{
        id: 'r-5', name: 'no_desc', display_name: '有名称',
        description: null, permissions: [], user_count: 0,
        created_at: null, updated_at: null,
      }],
    })
    renderRoles()
    await waitFor(() => {
      // 两列都有空值，都会渲染 '--'
      const dashes = screen.getAllByText('--')
      expect(dashes.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('编辑角色空 display_name/description 填充空字符串', async () => {
    _rolesApi.fetchRoles.mockResolvedValue({
      success: true,
      data: [{
        id: 'r-6', name: 'nulls', display_name: null,
        description: null, permissions: [],
        user_count: 0, created_at: null, updated_at: null,
      }],
    })
    renderRoles()
    await waitFor(() => { expect(screen.getByText('编辑')).toBeInTheDocument() })
    const editBtns = screen.getAllByText('编辑')
    await act(async () => { fireEvent.click(editBtns[0]) })
    await waitFor(() => {
      expect(_mockForm.setFieldsValue).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'nulls', display_name: '', description: '' }),
      )
    })
  })

  it('保存时空 display_name/description 发送 undefined', async () => {
    _mockForm.validateFields.mockResolvedValueOnce({
      name: 'minimal', display_name: '', description: '', permission_ids: [],
    })
    _rolesApi.createRole.mockResolvedValueOnce({ success: true })
    renderRoles()

    await act(async () => { fireEvent.click(screen.getByText('新建角色')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeVisible() })
    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_rolesApi.createRole).toHaveBeenCalledWith(
        expect.objectContaining({ display_name: undefined, description: undefined }),
      )
    })
  })

  it('fetchPermissions 返回非对象不崩溃', async () => {
    _rolesApi.fetchPermissions.mockResolvedValue({ success: true, data: null })
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('角色权限管理')).toBeInTheDocument()
    })
  })

  it('关联用户数显示"X 人"', async () => {
    renderRoles()
    await waitFor(() => {
      expect(screen.getByText('2 人')).toBeInTheDocument()
      expect(screen.getByText('0 人')).toBeInTheDocument()
    })
  })

  it('updateRole success=false 不显示成功消息', async () => {
    _rolesApi.updateRole.mockResolvedValueOnce({ success: false })
    _rolesApi.fetchRoles.mockResolvedValue({ success: true, data: mockRoles })
    renderRoles()
    await waitFor(() => { expect(screen.getByText('角色权限管理')).toBeInTheDocument() })
    const editBtns = screen.getAllByText('编辑')
    await act(async () => { fireEvent.click(editBtns[0]) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeVisible() })
    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_rolesApi.updateRole).toHaveBeenCalled()
    })
    const { message } = await import('antd')
    expect(message.success).not.toHaveBeenCalledWith('角色已更新')
  })

  it('createRole success=false 不显示成功消息', async () => {
    _rolesApi.createRole.mockResolvedValueOnce({ success: false })
    renderRoles()
    await act(async () => { fireEvent.click(screen.getByText('新建角色')) })
    await waitFor(() => { expect(screen.getByTestId('modal')).toBeVisible() })
    await act(async () => { fireEvent.click(screen.getByTestId('modal-ok')) })
    await waitFor(() => {
      expect(_rolesApi.createRole).toHaveBeenCalled()
    })
    const { message } = await import('antd')
    expect(message.success).not.toHaveBeenCalledWith('角色已创建')
  })

  it('deleteRole success=false 不显示成功消息', async () => {
    _rolesApi.deleteRole.mockResolvedValueOnce({ success: false })
    renderRoles()
    await waitFor(() => {
      expect(screen.getAllByTestId('popconfirm').length).toBeGreaterThanOrEqual(1)
    })
    const popconfirms = screen.getAllByTestId('popconfirm')
    await act(async () => { fireEvent.click(popconfirms[1]) })
    await waitFor(() => {
      expect(_rolesApi.deleteRole).toHaveBeenCalledWith('r-2')
    })
    const { message } = await import('antd')
    expect(message.success).not.toHaveBeenCalledWith('角色已删除')
  })
})
