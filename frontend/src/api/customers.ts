import { get, post, put, del } from './request'
import type { PaginatedData } from '@/types'

export interface Customer {
  id: string
  name: string
  contact_name: string | null
  phone: string | null
  email: string | null
  source: string | null
  level: string | null
  owner_user_id: string | null
  owner_name: string | null
  follow_status: string | null
  remark: string | null
  created_at: string | null
  updated_at: string | null
}

export interface CustomerFormValues {
  name: string
  contact_name?: string
  phone?: string
  email?: string
  source?: string
  level?: string
  owner_user_id?: string
  follow_status?: string
  remark?: string
}

export async function fetchCustomers(params?: {
  page?: number
  page_size?: number
  keyword?: string
  source?: string
  owner_user_id?: string
}) {
  return get<PaginatedData<Customer>>('/customers', params)
}

export async function fetchCustomer(id: string) {
  return get<Customer>(`/customers/${id}`)
}

export async function createCustomer(data: CustomerFormValues) {
  return post<Customer>('/customers', data)
}

export async function updateCustomer(id: string, data: Partial<CustomerFormValues>) {
  return put<Customer>(`/customers/${id}`, data)
}

export async function deleteCustomer(id: string) {
  return del(`/customers/${id}`)
}

export async function transferCustomer(id: string, owner_user_id: string) {
  return post<{ id: string; owner_user_id: string }>(`/customers/${id}/transfer`, { owner_user_id })
}
