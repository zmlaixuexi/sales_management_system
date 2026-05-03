import { create } from 'zustand';
import { authApi, type CurrentUser } from '@/api/auth';

interface AuthState {
  token: string | null;
  user: CurrentUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  hasPermission: (code: string) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('access_token'),
  user: null,
  loading: false,

  login: async (username: string, password: string) => {
    set({ loading: true });
    try {
      const { data } = await authApi.login({ username, password });
      if (!data.success) {
        throw new Error(data.error?.message || '登录失败');
      }
      localStorage.setItem('access_token', data.data.access_token);
      localStorage.setItem('refresh_token', data.data.refresh_token);
      set({ token: data.data.access_token });
      await get().fetchUser();
    } finally {
      set({ loading: false });
    }
  },

  logout: () => {
    authApi.logout().catch(() => {});
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ token: null, user: null });
  },

  fetchUser: async () => {
    try {
      const { data } = await authApi.getMe();
      if (data.success) {
        set({ user: data.data });
      }
    } catch {
      set({ token: null, user: null });
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  },

  hasPermission: (code: string) => {
    const { user } = get();
    if (!user) return false;
    if (user.is_superuser) return true;
    return user.permissions.includes(code);
  },
}));
