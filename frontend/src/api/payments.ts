import { get, post } from './request'
import type { PaginatedData } from '@/types'

export interface Payment {
  id: string
  order_id: string
  amount: string
  payment_method: string
  status: string
  remark: string | null
  paid_at: string | null
  created_at: string | null
}

export async function fetchPayments(params?: {
  page?: number
  page_size?: number
  order_id?: string
}) {
  return get<PaginatedData<Payment>>('/payments', params)
}

export async function createPayment(orderId: string, data: {
  amount: string
  payment_method: string
  remark?: string
}) {
  return post<{
    id: string
    order_id: string
    amount: string
    payment_method: string
    order_status: string
  }>(`/sales-orders/${orderId}/payments`, data)
}

export async function reversePayment(paymentId: string) {
  return post<{ id: string; status: string }>(`/payments/${paymentId}/reverse`)
}
