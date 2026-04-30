import apiClient from './client';

export interface LoginParams {
  username: string;
  password: string;
}

export interface TokenData {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  username: string;
  display_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  roles: { id: string; name: string; display_name: string | null }[];
  permissions: string[];
}

export const authApi = {
  login: (params: LoginParams) =>
    apiClient.post<{ success: boolean; data: TokenData }>('/auth/login', params),

  refresh: (refreshToken: string) =>
    apiClient.post<{ success: boolean; data: TokenData }>('/auth/refresh', { refresh_token: refreshToken }),

  logout: () => apiClient.post('/auth/logout'),

  getMe: () =>
    apiClient.get<{ success: boolean; data: CurrentUser }>('/auth/me'),

  changePassword: (oldPassword: string, newPassword: string) =>
    apiClient.post<{ success: boolean; message: string }>('/auth/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    }),
};
