import { useEffect, useRef } from 'react'

const APP_TITLE = '销售管理系统'

/**
 * 设置浏览器标签页标题，组件卸载时恢复默认标题。
 * 用法：useDocumentTitle('商品列表')
 * 效果：document.title = '商品列表 - 销售管理系统'
 */
export default function useDocumentTitle(title?: string) {
  const prevTitleRef = useRef(document.title)

  useEffect(() => {
    if (title) {
      document.title = `${title} - ${APP_TITLE}`
    } else {
      document.title = APP_TITLE
    }
    return () => {
      document.title = prevTitleRef.current
    }
  }, [title])
}
