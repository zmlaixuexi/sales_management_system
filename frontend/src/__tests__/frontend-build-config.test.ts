/**
 * 部署体验：前端构建与环境变量配置验证测试
 * 覆盖 Vite 构建配置、环境变量声明、TypeScript 配置、
 * package.json 脚本、开发代理配置
 */

import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..', '..', '..')
const frontend = resolve(root, 'frontend')

function readJson(filePath: string) {
  return JSON.parse(readFileSync(resolve(frontend, filePath), 'utf-8'))
}

function readText(filePath: string) {
  return readFileSync(resolve(frontend, filePath), 'utf-8')
}

const viteConfig = readText('vite.config.ts')
const tsconfigApp = readText('tsconfig.app.json')
const packageJson = readJson('package.json')

// ═══════════════════════════════════════════════════════════
// 1. Vite 构建配置验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('Vite 构建配置', () => {
  it('使用 react 插件', () => {
    expect(viteConfig).toContain("import react from '@vitejs/plugin-react'")
    expect(viteConfig).toContain('plugins: [react()]')
  })

  it('配置 @ 路径别名', () => {
    expect(viteConfig).toContain("'@'")
    expect(viteConfig).toContain("path.resolve(__dirname, './src')")
  })

  it('配置代码分割（manualChunks）', () => {
    expect(viteConfig).toContain('manualChunks')
    expect(viteConfig).toContain('vendor-react')
    expect(viteConfig).toContain('vendor-antd')
  })

  it('配置 API 代理转发', () => {
    expect(viteConfig).toContain("'/api'")
    expect(viteConfig).toContain("'/uploads'")
    expect(viteConfig).toContain('changeOrigin: true')
  })

  it('读取 VITE_PROXY_TARGET 环境变量', () => {
    expect(viteConfig).toContain('VITE_PROXY_TARGET')
    expect(viteConfig).toContain('loadEnv')
  })
})

// ═══════════════════════════════════════════════════════════
// 2. 环境变量声明验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('环境变量声明', () => {
  it('.env.example 文件存在', () => {
    expect(existsSync(resolve(frontend, '.env.example'))).toBe(true)
  })

  it('.env.example 包含 VITE_API_BASE_URL', () => {
    const envExample = readText('.env.example')
    expect(envExample).toContain('VITE_API_BASE_URL')
  })

  it('.env.example 包含 VITE_PROXY_TARGET', () => {
    const envExample = readText('.env.example')
    expect(envExample).toContain('VITE_PROXY_TARGET')
  })

  it('源码中使用 import.meta.env.VITE_API_BASE_URL', () => {
    const clientTs = readFileSync(resolve(frontend, 'src/api/client.ts'), 'utf-8')
    expect(clientTs).toContain('import.meta.env.VITE_API_BASE_URL')
  })

  it('VITE_API_BASE_URL 有回退默认值', () => {
    const clientTs = readFileSync(resolve(frontend, 'src/api/client.ts'), 'utf-8')
    expect(clientTs).toContain('||')
    expect(clientTs).toContain('localhost')
  })
})

// ═══════════════════════════════════════════════════════════
// 3. TypeScript 配置验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('TypeScript 配置', () => {
  it('启用 strict 模式', () => {
    expect(tsconfigApp).toContain('"strict": true')
  })

  it('启用 noUnusedLocals 和 noUnusedParameters', () => {
    expect(tsconfigApp).toContain('"noUnusedLocals": true')
    expect(tsconfigApp).toContain('"noUnusedParameters": true')
  })

  it('启用 noUncheckedIndexedAccess', () => {
    expect(tsconfigApp).toContain('"noUncheckedIndexedAccess": true')
  })

  it('配置 @ 路径别名与 Vite 一致', () => {
    expect(tsconfigApp).toContain('"@/*"')
    expect(tsconfigApp).toContain('"src/*"')
  })

  it('include 覆盖 src 目录', () => {
    expect(tsconfigApp).toContain('"include"')
    expect(tsconfigApp).toContain('"src"')
  })
})

// ═══════════════════════════════════════════════════════════
// 4. package.json 脚本验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('package.json 脚本', () => {
  it('定义 dev/build/lint/test 脚本', () => {
    const scripts = packageJson.scripts
    expect(scripts.dev).toBeDefined()
    expect(scripts.build).toBeDefined()
    expect(scripts.lint).toBeDefined()
    expect(scripts.test).toBeDefined()
  })

  it('build 脚本包含 tsc 类型检查', () => {
    expect(packageJson.scripts.build).toContain('tsc')
    expect(packageJson.scripts.build).toContain('vite build')
  })

  it('使用 ESM 模块系统', () => {
    expect(packageJson.type).toBe('module')
  })

  it('核心依赖包含 react/antd/axios/zustand/react-router-dom', () => {
    const deps = packageJson.dependencies
    expect(deps.react).toBeDefined()
    expect(deps.antd).toBeDefined()
    expect(deps.axios).toBeDefined()
    expect(deps.zustand).toBeDefined()
    expect(deps['react-router-dom']).toBeDefined()
  })

  it('devDependencies 包含 vitest 和 typescript', () => {
    const devDeps = packageJson.devDependencies
    expect(devDeps.vitest).toBeDefined()
    expect(devDeps.typescript).toBeDefined()
  })
})

// ═══════════════════════════════════════════════════════════
// 5. 前端 Dockerfile 配置验证（5 项）
// ═══════════════════════════════════════════════════════════

describe('前端 Dockerfile 配置', () => {
  it('前端 Dockerfile 存在', () => {
    expect(existsSync(resolve(root, 'frontend', 'Dockerfile'))).toBe(true)
  })

  it('使用多阶段构建', () => {
    const dockerfile = readFileSync(resolve(root, 'frontend', 'Dockerfile'), 'utf-8')
    const fromCount = (dockerfile.match(/^FROM /gm) || []).length
    expect(fromCount).toBeGreaterThanOrEqual(2)
  })

  it('包含 npm run build 指令', () => {
    const dockerfile = readFileSync(resolve(root, 'frontend', 'Dockerfile'), 'utf-8')
    expect(dockerfile).toContain('npm run build')
  })

  it('使用 nginx 作为生产服务器', () => {
    const dockerfile = readFileSync(resolve(root, 'frontend', 'Dockerfile'), 'utf-8')
    expect(dockerfile.toLowerCase()).toContain('nginx')
  })

  it('前端 dev Dockerfile 存在', () => {
    expect(existsSync(resolve(root, 'frontend', 'Dockerfile.dev'))).toBe(true)
  })
})
