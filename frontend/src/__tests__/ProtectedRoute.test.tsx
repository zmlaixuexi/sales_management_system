import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import ProtectedRoute from '../routes/ProtectedRoute';
import { useAuthStore } from '../stores/auth';

// mock antd Spin
vi.mock('antd', () => ({
  Spin: ({ size }: { size: string }) => <div data-testid="spin">loading-{size}</div>,
}));

// mock auth store
vi.mock('../stores/auth', () => ({
  useAuthStore: vi.fn(),
}));

const mockedUseAuthStore = vi.mocked(useAuthStore);

function renderWithRouter(initial: string = '/') {
  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/" element={<ProtectedRoute><div>protected-content</div></ProtectedRoute>} />
        <Route path="/login" element={<div>login-page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute', () => {
  const mockFetchUser = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('无 token 时重定向到登录页', () => {
    mockedUseAuthStore.mockReturnValue({
      token: null,
      user: null,
      fetchUser: mockFetchUser,
    } as ReturnType<typeof useAuthStore>);

    renderWithRouter();
    expect(screen.getByText('login-page')).toBeInTheDocument();
  });

  it('有 token 无 user 时显示加载中并调用 fetchUser', () => {
    mockFetchUser.mockResolvedValue(undefined);
    mockedUseAuthStore.mockReturnValue({
      token: 'test-token',
      user: null,
      fetchUser: mockFetchUser,
    } as ReturnType<typeof useAuthStore>);

    renderWithRouter();
    expect(screen.getByTestId('spin')).toBeInTheDocument();
    expect(mockFetchUser).toHaveBeenCalled();
  });

  it('有 token 和 user 时渲染子组件', () => {
    mockedUseAuthStore.mockReturnValue({
      token: 'test-token',
      user: { id: '1', username: 'admin', is_superuser: false, permissions: [] },
      fetchUser: mockFetchUser,
    } as ReturnType<typeof useAuthStore>);

    renderWithRouter();
    expect(screen.getByText('protected-content')).toBeInTheDocument();
  });

  it('fetchUser 失败后 user 为 null 时重定向到登录', async () => {
    const storeValues = {
      token: 'test-token',
      user: null,
      fetchUser: vi.fn().mockResolvedValue(undefined),
    };
    mockedUseAuthStore.mockReturnValue(storeValues as ReturnType<typeof useAuthStore>);

    renderWithRouter();
    expect(screen.getByTestId('spin')).toBeInTheDocument();

    // 等待 fetchUser 完成，loading 变为 false，user 仍为 null → 重定向到登录
    await waitFor(() => {
      expect(screen.getByText('login-page')).toBeInTheDocument();
    });
  });

  it('加载中 Spin 使用 large 尺寸', () => {
    mockFetchUser.mockReturnValue(new Promise(() => {})); // 永不 resolve，保持 loading
    mockedUseAuthStore.mockReturnValue({
      token: 'test-token',
      user: null,
      fetchUser: mockFetchUser,
    } as ReturnType<typeof useAuthStore>);

    renderWithRouter();
    expect(screen.getByTestId('spin')).toHaveTextContent('loading-large');
  });
});
