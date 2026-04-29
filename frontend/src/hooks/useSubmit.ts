import { useState, useCallback, useRef } from 'react'
import { message } from 'antd'
import { getApiErrorMessage } from '@/utils'

/**
 * 封装表单提交的 loading / 防重复提交 / 错误提示逻辑。
 *
 * 用法：
 *   const { submitting, handleSubmit } = useSubmit(async (values) => {
 *     await createProduct(values)
 *     message.success('创建成功')
 *     navigate('/products')
 *   })
 */
export function useSubmit<T>(
  onSubmit: (values: T) => Promise<void>,
  fallbackError = '操作失败',
) {
  const [submitting, setSubmitting] = useState(false)
  const locked = useRef(false)

  const handleSubmit = useCallback(async (values: T) => {
    if (locked.current) return
    locked.current = true
    setSubmitting(true)
    try {
      await onSubmit(values)
    } catch (e: unknown) {
      // Ant Design 表单校验错误（errorFields）不弹提示
      if (e && typeof e === 'object' && 'errorFields' in e) return
      message.error(getApiErrorMessage(e, fallbackError))
    } finally {
      setSubmitting(false)
      locked.current = false
    }
  }, [onSubmit, fallbackError])

  return { submitting, handleSubmit }
}
