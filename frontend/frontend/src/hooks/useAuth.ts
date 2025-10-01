// src/hooks/useAuth.ts

import { create } from 'zustand';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as api from '../services/api';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  setToken: (token: string | null) => void;
  logout: () => void;
}

// Create a separate store for auth state for better separation of concerns
export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('accessToken'),
  isAuthenticated: !!localStorage.getItem('accessToken'),
  setToken: (token) => {
    if (token) {
      localStorage.setItem('accessToken', token);
      set({ token, isAuthenticated: true });
    } else {
      localStorage.removeItem('accessToken');
      set({ token: null, isAuthenticated: false });
    }
  },
  logout: () => {
    localStorage.removeItem('accessToken');
    set({ token: null, isAuthenticated: false });
    toast.info('You have been logged out.');
  },
}));

export const useAuth = () => {
  const { setToken } = useAuthStore();
  
  const loginMutation = useMutation({
    mutationFn: ({ username, password }: api.LoginCredentials) => {
      const credentials = new URLSearchParams();
      credentials.append('username', username);
      credentials.append('password', password);
      return api.login(credentials);
    },
    onSuccess: (data) => {
      const accessToken = data.data.access_token;
      setToken(accessToken);
      toast.success('Login successful!');
    },
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onError: (error: any) => {
      const errorMessage = error.response?.data?.detail || 'Invalid username or password.';
      toast.error(`Login failed: ${errorMessage}`);
      // Return the error message so it can be displayed on the form
      return errorMessage;
    },
  });

  return {
    login: (username: string, password: string) => loginMutation.mutateAsync({ username, password }),
    isLoggingIn: loginMutation.isPending,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    error: loginMutation.error ? (loginMutation.error as any).response?.data?.detail || 'An unknown error occurred.' : null,
  };
};