/**
 * 安全加固：前端 XSS 防护回归测试
 * 验证前端代码中不存在 XSS 攻击面（回归防护）
 */

import { describe, it, expect } from 'vitest'
import path from 'node:path'
import fs from 'node:fs'

const SRC_DIR = path.resolve(__dirname, '..')

/** 递归收集 src 目录下所有 .ts/.tsx 文件 */
function collectSourceFiles(dir: string): string[] {
  const files: string[] = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory() && entry.name !== '__tests__' && entry.name !== 'node_modules') {
      files.push(...collectSourceFiles(full))
    } else if (/\.[jt]sx?$/.test(entry.name)) {
      files.push(full)
    }
  }
  return files
}

const sourceFiles = collectSourceFiles(SRC_DIR)

describe('前端 XSS 防护回归测试', () => {
  // ═══════════════════════════════════════════════════════
  // 1. dangerouslySetInnerHTML 禁止使用
  // ═══════════════════════════════════════════════════════

  it('源码中不包含 dangerouslySetInnerHTML', () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      if (content.includes('dangerouslySetInnerHTML')) {
        violations.push(path.relative(SRC_DIR, file))
      }
    }
    expect(violations, `发现 dangerouslySetInnerHTML: ${violations.join(', ')}`).toHaveLength(0)
  })

  // ═══════════════════════════════════════════════════════
  // 2. innerHTML / outerHTML 直接赋值禁止
  // ═══════════════════════════════════════════════════════

  it('源码中不包含 .innerHTML 赋值', () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      if (/\.innerHTML\s*=/.test(content)) {
        violations.push(path.relative(SRC_DIR, file))
      }
    }
    expect(violations, `发现 .innerHTML 赋值: ${violations.join(', ')}`).toHaveLength(0)
  })

  it('源码中不包含 .outerHTML 赋值', () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      if (/\.outerHTML\s*=/.test(content)) {
        violations.push(path.relative(SRC_DIR, file))
      }
    }
    expect(violations, `发现 .outerHTML 赋值: ${violations.join(', ')}`).toHaveLength(0)
  })

  // ═══════════════════════════════════════════════════════
  // 3. eval / new Function / document.write 禁止
  // ═══════════════════════════════════════════════════════

  it('源码中不包含 eval() 调用', () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      // 排除注释中的 eval 和字符串引用
      const lines = content.split('\n')
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim()
        // 跳过注释行
        if (line.startsWith('//') || line.startsWith('*') || line.startsWith('/*')) continue
        if (/\beval\s*\(/.test(line)) {
          violations.push(`${path.relative(SRC_DIR, file)}:${i + 1}`)
        }
      }
    }
    expect(violations, `发现 eval() 调用: ${violations.join(', ')}`).toHaveLength(0)
  })

  it('源码中不包含 new Function() 调用', () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      if (/new\s+Function\s*\(/.test(content)) {
        violations.push(path.relative(SRC_DIR, file))
      }
    }
    expect(violations, `发现 new Function(): ${violations.join(', ')}`).toHaveLength(0)
  })

  it('源码中不包含 document.write 调用', () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      if (/document\.write\s*\(/.test(content)) {
        violations.push(path.relative(SRC_DIR, file))
      }
    }
    expect(violations, `发现 document.write: ${violations.join(', ')}`).toHaveLength(0)
  })

  // ═══════════════════════════════════════════════════════
  // 4. insertAdjacentHTML 禁止
  // ═══════════════════════════════════════════════════════

  it('源码中不包含 insertAdjacentHTML 调用', () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      if (/\.insertAdjacentHTML\s*\(/.test(content)) {
        violations.push(path.relative(SRC_DIR, file))
      }
    }
    expect(violations, `发现 insertAdjacentHTML: ${violations.join(', ')}`).toHaveLength(0)
  })

  // ═══════════════════════════════════════════════════════
  // 5. javascript: 协议禁止
  // ═══════════════════════════════════════════════════════

  it('源码中不包含 javascript: 协议链接', () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      // 匹配 href="javascript:" 或 href={'javascript:'} 等
      if (/javascript\s*:/.test(content)) {
        violations.push(path.relative(SRC_DIR, file))
      }
    }
    expect(violations, `发现 javascript: 协议: ${violations.join(', ')}`).toHaveLength(0)
  })

  // ═══════════════════════════════════════════════════════
  // 6. window.location 赋值安全检查
  // ═══════════════════════════════════════════════════════

  it('window.location.href 赋值仅使用硬编码路径', () => {
    const violations: string[] = []
    for (const file of sourceFiles) {
      const content = fs.readFileSync(file, 'utf-8')
      const lines = content.split('\n')
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim()
        // 跳过注释行
        if (line.startsWith('//') || line.startsWith('*') || line.startsWith('/*')) continue
        const match = line.match(/window\.location\.href\s*=\s*(.+)/)
        if (match) {
          const value = match[1].trim()
          // 允许硬编码字符串字面量（'/login', '/' 等）
          if (!/^['"]\/[^'"]*['"]/.test(value)) {
            violations.push(`${path.relative(SRC_DIR, file)}:${i + 1}: ${line}`)
          }
        }
      }
    }
    expect(violations, `发现非硬编码 location.href 赋值: ${violations.join('; ')}`).toHaveLength(0)
  })

  // ═══════════════════════════════════════════════════════
  // 7. 源码文件发现完整性
  // ═══════════════════════════════════════════════════════

  it('至少扫描了 30 个源码文件', () => {
    expect(sourceFiles.length).toBeGreaterThanOrEqual(30)
  })

  it('扫描范围覆盖 pages 和 components 目录', () => {
    const hasPages = sourceFiles.some((f) => f.includes(`${path.sep}pages${path.sep}`))
    const hasComponents = sourceFiles.some((f) => f.includes(`${path.sep}components${path.sep}`))
    expect(hasPages, '未覆盖 pages 目录').toBe(true)
    expect(hasComponents, '未覆盖 components 目录').toBe(true)
  })
})
