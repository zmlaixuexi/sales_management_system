/**
 * 代码质量：前端拦截器边界测试
 * 覆盖错误优先级链、请求拦截器边界、配置常量、429 Retry-After 边界、
 * _toastDisplayed 标记、downloadCsv 文件名解析
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import { downloadCsv } from '@/api/request'
import type { ApiResponse, PaginatedData } from '@/types'

// ═══════════════════════════════════════════════════════
// Part A: downloadCsv 边界测试（需要 mock apiClient）
// ═══════════════════════════════════════════════════════

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { handlers: [] },
      response: { handlers: [] },
    },
    defaults: { baseURL: '/api/v1', headers: { common: {} } },
  },
}))

import apiClient from '@/api/client'

const mockClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
}

describe('downloadCsv 边界', () => {
  beforeEach(() => {
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue('blob:http://test/fake')
    globalThis.URL.revokeObjectURL = vi.fn()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('content-disposition 无 filename 时使用默认 "export.csv"', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: new Blob(['x'], { type: 'text/csv' }),
      headers: {},
    })

    const createElementSpy = vi.spyOn(document, 'createElement')
    await downloadCsv('/exports/test')

    const anchor = createElementSpy.mock.results.find(
      (r) => (r.value as HTMLAnchorElement).tagName === 'A',
    )?.value as HTMLAnchorElement | undefined
    expect(anchor?.download).toBe('export.csv')
  })

  it('content-disposition 包含中文文件名时提取正确', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: new Blob(['x'], { type: 'text/csv' }),
      headers: { 'content-disposition': 'filename=产品导出.csv' },
    })

    const createElementSpy = vi.spyOn(document, 'createElement')
    await downloadCsv('/exports/test')

    const anchor = createElementSpy.mock.results.find(
      (r) => (r.value as HTMLAnchorElement).tagName === 'A',
    )?.value as HTMLAnchorElement | undefined
    expect(anchor?.download).toBe('产品导出.csv')
  })

  it('所有参数为 undefined/空字符串时传空 params', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: new Blob(['x'], { type: 'text/csv' }),
      headers: { 'content-disposition': 'filename=out.csv' },
    })
    await downloadCsv('/exports/test', { a: undefined, b: '', c: undefined })
    expect(mockClient.get).toHaveBeenCalledWith('/exports/test', {
      params: {},
      responseType: 'blob',
    })
  })

  it('content-disposition 包含空格文件名时正确提取', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: new Blob(['x'], { type: 'text/csv' }),
      headers: { 'content-disposition': 'filename=report 2024.csv' },
    })

    const createElementSpy = vi.spyOn(document, 'createElement')
    await downloadCsv('/exports/test')

    const anchor = createElementSpy.mock.results.find(
      (r) => (r.value as HTMLAnchorElement).tagName === 'A',
    )?.value as HTMLAnchorElement | undefined
    expect(anchor?.download).toBe('report 2024.csv')
  })

  it('JSON 错误 blob 优先使用 error.message', async () => {
    const errorJson = JSON.stringify({ error: { message: '导出权限不足' } })
    mockClient.get.mockResolvedValueOnce({
      data: new Blob([errorJson], { type: 'application/json' }),
      headers: {},
    })
    await expect(downloadCsv('/exports/products')).rejects.toThrow('导出权限不足')
  })

  it('JSON 错误无 error.message 时使用 message 字段', async () => {
    const errorJson = JSON.stringify({ message: '服务器内部错误' })
    mockClient.get.mockResolvedValueOnce({
      data: new Blob([errorJson], { type: 'application/json' }),
      headers: {},
    })
    await expect(downloadCsv('/exports/products')).rejects.toThrow('服务器内部错误')
  })

  it('JSON 错误无消息字段使用默认文案', async () => {
    const errorJson = JSON.stringify({ code: 'UNKNOWN' })
    mockClient.get.mockResolvedValueOnce({
      data: new Blob([errorJson], { type: 'application/json' }),
      headers: {},
    })
    await expect(downloadCsv('/exports/products')).rejects.toThrow('导出失败')
  })

  it('成功下载调用 createObjectURL 和 revokeObjectURL', async () => {
    mockClient.get.mockResolvedValueOnce({
      data: new Blob(['x'], { type: 'text/csv' }),
      headers: { 'content-disposition': 'filename=data.csv' },
    })
    await downloadCsv('/exports/products')
    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(URL.revokeObjectURL).toHaveBeenCalled()
  })
})
