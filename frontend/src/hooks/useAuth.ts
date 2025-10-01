import { useState } from 'react';
import { useAppStore } from '../store';
import { api } from '../services/api';
import { toast } from 'sonner';

export function useAuth() {
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setAuthenticated, setCurrentPage } = useAppStore();

  const login = async (username: string, password: string) => {
    setIsLoggingIn(true);
    setError(null);
    
    try {
      const response = await api.login(username, password);
      
      if (response.success) {
        setAuthenticated(true, response.data.user);
        localStorage.setItem('authToken', response.data.token);
        toast.success('Successfully logged in!');
        setCurrentPage('dashboard');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoggingIn(false);
    }
  };

  const logout = () => {
    setAuthenticated(false);
    localStorage.removeItem('authToken');
    setCurrentPage('login');
    toast.success('Successfully logged out');
  };

  return {
    login,
    logout,
    isLoggingIn,
    error,
  };
}