import { get, post, put, del } from './request'

export interface PermissionItem {
  id: string
  code: string
  name: string
  module: string
}

export interface RoleItem {
  id: string
  name: string
  display_name: string | null
  description: string | null
  permissions: PermissionItem[]
  user_count: number
  created_at: string | null
  updated_at: string | null
}

export interface RoleCreate {
  name: string
  display_name?: string
  description?: string
  permission_ids?: string[]
}

export interface RoleUpdate {
  name?: string
  display_name?: string
  description?: string
  permission_ids?: string[]
}

export async function fetchRoles() {
  return get<RoleItem[]>('/roles')
}

export async function fetchPermissions() {
  return get<Record<string, PermissionItem[]>>('/roles/permissions')
}

export async function createRole(data: RoleCreate) {
  return post<RoleItem>('/roles', data)
}

export async function updateRole(id: string, data: RoleUpdate) {
  return put<RoleItem>(`/roles/${id}`, data)
}

export async function deleteRole(id: string) {
  return del(`/roles/${id}`)
}
