import { api, uploadFile, uploadMultipleFiles } from './api';
import { User } from '../store/authSlice';

// Auth API functions
export const authApi = {
  // Login user
  login: (email: string, password: string) =>
    api.post<{
      user: User;
      token: string;
      refreshToken: string;
    }>('/auth/login', { email, password }, { requireAuth: false }),

  // Register user (if needed)
  register: (userData: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
    role?: string;
  }) =>
    api.post<{
      user: User;
      token: string;
      refreshToken: string;
    }>('/auth/register', userData, { requireAuth: false }),

  // Refresh token
  refresh: (refreshToken: string) =>
    api.post<{
      token: string;
      refreshToken: string;
      user: User;
    }>('/auth/refresh', { refreshToken }, { requireAuth: false }),

  // Logout
  logout: () => api.post('/auth/logout'),

  // Get current user profile
  getProfile: () => api.get<User>('/auth/profile'),

  // Update user profile
  updateProfile: (updates: Partial<User>) =>
    api.patch<User>('/auth/profile', updates),

  // Change password
  changePassword: (oldPassword: string, newPassword: string) =>
    api.post('/auth/change-password', { oldPassword, newPassword }),

  // Request password reset
  requestPasswordReset: (email: string) =>
    api.post('/auth/forgot-password', { email }, { requireAuth: false }),

  // Reset password with token
  resetPassword: (token: string, newPassword: string) =>
    api.post('/auth/reset-password', { token, newPassword }, { requireAuth: false }),

  // Verify email
  verifyEmail: (token: string) =>
    api.post('/auth/verify-email', { token }, { requireAuth: false }),

  // Resend verification email
  resendVerification: () => api.post('/auth/resend-verification'),
};