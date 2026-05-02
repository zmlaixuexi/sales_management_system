import { useState, useEffect, useCallback } from 'react'
import { Table, Button, Input, Space, Tag, Modal, Form, Select, Switch, message } from 'antd'
import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { fetchUsers, createUser, updateUser, fetchRoles } from '@/api/users'
import type { User, RoleItem } from '@/api/users'
import { usePaginatedList } from '@/hooks/usePaginatedList'
import { getApiErrorMessage } from '@/utils'

export default function UsersPage() {
  const [roles, setRoles] = useState<RoleItem[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const { data, total, loading, error, page, pageSize, keyword, setKeyword, onPageChange, refresh } = usePaginatedList<User>(
    (params) => fetchUsers(params).then(r => r.data),
    {},
    '加载用户列表失败',
  )

  const loadRoles = useCallback(async () => {
    try {
      const res = await fetchRoles()
      if (res.success && Array.isArray(res.data)) setRoles(res.data)
    } catch { /* 静默 */ }
  }, [])

  useEffect(() => { loadRoles() }, [loadRoles])

  const openCreate = () => {
    setEditingUser(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (user: User) => {
    setEditingUser(user)
    form.setFieldsValue({
      display_name: user.display_name || '',
      phone: user.phone || '',
      email: user.email || '',
      is_active: user.is_active,
      role_ids: user.roles.map((r) => r.id),
    })
    setModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      if (editingUser) {
        const res = await updateUser(editingUser.id, {
          display_name: values.display_name || undefined,
          phone: values.phone || undefined,
          email: values.email || undefined,
          is_active: values.is_active,
          role_ids: values.role_ids || [],
        })
        if (res.success) {
          message.success('用户已更新')
          setModalOpen(false)
          refresh()
        }
      } else {
        const res = await createUser({
          username: values.username,
          password: values.password,
          display_name: values.display_name || undefined,
          phone: values.phone || undefined,
          email: values.email || undefined,
          role_ids: values.role_ids || [],
        })
        if (res.success) {
          message.success('用户已创建')
          setModalOpen(false)
          refresh()
        }
      }
    } catch (e: unknown) {
      if ((e as Record<string, boolean>)?._toastDisplayed) return
      const msg = editingUser ? '更新用户失败' : '创建用户失败'
      message.error(getApiErrorMessage(e, msg))
    } finally {
      setSaving(false)
    }
  }

  const handleToggleActive = async (user: User, checked: boolean) => {
    try {
      const res = await updateUser(user.id, { is_active: checked })
      if (res.success) {
        message.success(checked ? '已启用' : '已停用')
        refresh()
      }
    } catch (e: unknown) {
      if (!(e as Record<string, boolean>)?._toastDisplayed) message.error(getApiErrorMessage(e, '操作失败'))
    }
  }

  const columns: ColumnsType<User> = [
    {
      title: '用户名',
      dataIndex: 'username',
      width: 120,
    },
    {
      title: '显示名',
      dataIndex: 'display_name',
      width: 120,
      render: (v: string | null) => v || '--',
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      width: 130,
      render: (v: string | null) => v || '--',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      width: 180,
      render: (v: string | null) => v || '--',
    },
    {
      title: '角色',
      dataIndex: 'roles',
      width: 160,
      render: (roles: RoleItem[]) =>
        roles.length > 0
          ? roles.map((r) => <Tag key={r.id} color="blue">{r.display_name || r.name}</Tag>)
          : <Tag>无角色</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 80,
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '停用'}</Tag>
      ),
    },
    {
      title: '超级管理员',
      dataIndex: 'is_superuser',
      width: 100,
      render: (v: boolean) => v ? <Tag color="gold">是</Tag> : '--',
    },
    {
      title: '操作',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" onClick={() => openEdit(record)}>编辑</Button>
          <Switch
            size="small"
            checked={record.is_active}
            onChange={(checked) => handleToggleActive(record, checked)}
          />
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Space>
          <Input
            placeholder="搜索用户名"
            prefix={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            style={{ width: 240 }}
            allowClear
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建用户
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50],
          showTotal: (t) => `共 ${t} 条`,
          onChange: onPageChange,
        }}
        locale={{ emptyText: error && !loading ? <span>加载失败，<a onClick={refresh}>重试</a></span> : '暂无用户数据' }}
      />

      <Modal
        title={editingUser ? '编辑用户' : '新建用户'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存"
      >
        <Form form={form} layout="vertical">
          {!editingUser && (
            <>
              <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
                <Input />
              </Form.Item>
              <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
                <Input.Password />
              </Form.Item>
            </>
          )}
          <Form.Item name="display_name" label="显示名">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="手机号">
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input />
          </Form.Item>
          {editingUser && (
            <Form.Item name="is_active" label="启用状态" valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
          <Form.Item name="role_ids" label="角色">
            <Select
              mode="multiple"
              placeholder="选择角色"
              options={roles.map((r) => ({ label: r.display_name || r.name, value: r.id }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
