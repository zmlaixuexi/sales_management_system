import { type ReactNode, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { Spin } from 'antd';
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
