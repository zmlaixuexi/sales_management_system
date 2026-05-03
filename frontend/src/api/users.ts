import { get, post, put } from './request'
import type { PaginatedData } from '@/types'

export interface RoleItem {
  id: string
  name: string
  display_name: string | null
}

export interface User {
  id: string
  username: string
  display_name: string | null
  phone: string | null
  email: string | null
  is_active: boolean
  is_superuser: boolean
  roles: RoleItem[]
  created_at: string | null
  updated_at: string | null
}

export interface UserCreate {
  username: string
  password: string
  display_name?: string
  phone?: string
  email?: string
  role_ids?: string[]
}

export interface UserUpdate {
  display_name?: string
  phone?: string
  email?: string
  is_active?: boolean
  role_ids?: string[]
}

export async function fetchUsers(params?: {
  page?: number
  page_size?: number
  keyword?: string
}) {
  return get<PaginatedData<User>>('/users', params)
}

export async function createUser(data: UserCreate) {
  return post<{ id: string; username: string }>('/users', data)
}

export async function updateUser(id: string, data: UserUpdate) {
  return put(`/users/${id}`, data)
}

export async function fetchRoles() {
  return get<RoleItem[]>('/users/roles')
}
