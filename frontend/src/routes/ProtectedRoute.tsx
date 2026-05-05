import { type ReactNode, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { Result, Button, Spin } from 'antd';
import { useAuthStore } from '@/stores/auth';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token, user, fetchUser } = useAuthStore();
  const [loading, setLoading] = useState(!!token && !user);

  useEffect(() => {
    if (token && !user) {
      fetchUser().finally(() => setLoading(false));
    }
  }, [token, user, fetchUser]);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

/** 路由权限映射 */
const ROUTE_PERMISSIONS: Record<string, string | null> = {
  '/': null,
  '/products': 'product:list',
  '/products/new': 'product:create',
  '/products/:id/edit': 'product:update',
  '/inventory': 'inventory:list',
  '/customers': 'customer:list',
  '/customers/new': 'customer:create',
  '/customers/:id': 'customer:list',
  '/customers/:id/edit': 'customer:update',
  '/orders': 'order:list',
  '/orders/new': 'order:create',
  '/orders/:id': 'order:list',
  '/orders/:id/edit': 'order:update',
  '/payments': 'payment:list',
  '/audit-logs': 'audit:view',
  '/reports': 'report:sales',
  '/users': '__superuser__',
  '/roles': '__superuser__',
};

export function getRoutePermission(pathname: string): string | null {
  // 精确匹配
  if (ROUTE_PERMISSIONS[pathname] !== undefined) return ROUTE_PERMISSIONS[pathname];
  // 动态路径匹配
  const segments = pathname.split('/').filter(Boolean);
  for (const [pattern, perm] of Object.entries(ROUTE_PERMISSIONS)) {
    const patternSegs = pattern.split('/').filter(Boolean);
    if (patternSegs.length !== segments.length) continue;
    const match = patternSegs.every((seg, i) => seg.startsWith(':') || seg === segments[i]);
    if (match) return perm;
  }
  return null;
}

/** 检查用户是否有路由权限 */
export function checkRoutePermission(pathname: string): boolean {
  const perm = getRoutePermission(pathname);
  if (perm === null) return true;
  const { user, hasPermission } = useAuthStore.getState();
  if (!user) return false;
  if (perm === '__superuser__') return user.is_superuser === true;
  return hasPermission(perm);
}

/** 路由权限守卫组件 */
export function RouteGuard({ children, pathname }: { children: ReactNode; pathname: string }) {
  if (!checkRoutePermission(pathname)) {
    return (
      <Result
        status="403"
        title="无访问权限"
        subTitle="您没有权限访问此页面"
        extra={<Button type="primary" href="/">返回首页</Button>}
      />
    );
  }
  return <>{children}</>;
}
