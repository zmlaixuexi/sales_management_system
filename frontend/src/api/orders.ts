import { get, post, put } from './request'
import type { PaginatedData } from '@/types'

export interface OrderItem {
  id: string
  product_id: string
  product_sku_snapshot: string
  product_name_snapshot: string
  product_image_url_snapshot: string | null
  quantity: number
  unit_price: string
  discount_amount: string
  discount_rate: string
  cost_price_snapshot: string
  subtotal_amount: string
  subtotal_cost: string
}

export interface OrderPayment {
  id: string
  amount: string
  payment_method: string
  paid_at: string | null
  remark: string | null
  created_at: string | null
}

export interface Order {
  id: string
  order_no: string
  customer_id: string
  sales_user_id: string
  status: string
  status_label: string
  total_amount: string
  total_cost: string
  gross_profit: string
  gross_margin: string
  paid_amount: string
  item_count?: number
  remark: string | null
  created_at: string | null
  updated_at: string | null
}

export interface OrderDetail extends Order {
  items: OrderItem[]
  payments: OrderPayment[]
}

export interface OrderFormValues {
  customer_id: string
  items: Array<{
    product_id: string
    quantity: number
    unit_price?: string
  }>
  remark?: string
}

export async function fetchOrders(params?: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  customer_id?: string
}) {
  return get<PaginatedData<Order>>('/sales-orders', params)
}

export async function fetchOrder(id: string) {
  return get<OrderDetail>(`/sales-orders/${id}`)
}

export async function createOrder(data: OrderFormValues) {
  return post<Order>('/sales-orders', data)
}

export async function updateOrder(id: string, data: Partial<OrderFormValues>) {
  return put<{ id: string; order_no: string }>(`/sales-orders/${id}`, data)
}

export async function confirmOrder(id: string) {
  return post<{ id: string; status: string }>(`/sales-orders/${id}/confirm`)
}

export async function cancelOrder(id: string) {
  return post<{ id: string; status: string }>(`/sales-orders/${id}/cancel`)
}

export interface OrderLog {
  id: string
  actor_id: string | null
  actor_name: string
  action: string
  before_data: Record<string, unknown> | null
  after_data: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string | null
  request_id: string | null
  created_at: string | null
}

export async function fetchOrderLogs(id: string, params?: { page?: number; page_size?: number }) {
  return get<PaginatedData<OrderLog>>(`/sales-orders/${id}/logs`, params)
}
