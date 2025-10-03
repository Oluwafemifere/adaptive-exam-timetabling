// frontend/src/hooks/useAuth.ts
import { useState } from 'react';
import { useAppStore } from '../store';
import { api } from '../services/api';
import apiService from '../services/api';
import { toast } from 'sonner';
import { User, UserRole } from '../store/types';

export function useAuth() {
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setAuthenticated, initializeApp } = useAppStore();

  const login = async (username: string, password: string) => {
    console.log(`Attempting to log in user: ${username}`);
    setIsLoggingIn(true);
    setError(null);
    
    try {
      const response = await api.login(username, password);
      console.log('Login API response received:', response);
      
      if (response.success) {
        const { access_token: token } = response.data;
        console.log('Login successful. Token received.');
        localStorage.setItem('authToken', token);
        apiService.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        console.log('Authorization header set on apiService.');
        
        // Fetch the full user object from the /me endpoint
        const userResponse = await api.getCurrentUser();
        const userData = userResponse.data;

        // *** FIX: Construct the user object using the correct 'role' property ***
        const user: User = {
          id: userData.id,
          name: `${userData.first_name} ${userData.last_name}`,
          email: userData.email,
          // The backend now returns a single `role` field.
          role: userData.role as UserRole,
        };
        console.log('User object created from API response:', user);
        
        setAuthenticated(true, user);
        toast.success('Successfully logged in!');
        
        console.log('Initializing application data post-login.');
        await initializeApp();
        console.log('App data initialized.');
      }
    } catch (err: any) {
      const errorMessage = (err.response?.data?.detail || err.message) || 'Login failed';
      console.error('Login failed:', errorMessage, err);
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      console.log('Login process finished.');
      setIsLoggingIn(false);
    }
  };

  const logout = () => {
    console.log('Logging out user.');
    setAuthenticated(false, null);
    localStorage.removeItem('authToken');
    console.log('Auth token removed from local storage.');
    
    delete apiService.defaults.headers.common['Authorization'];
    console.log('Authorization header removed from apiService.');
    
    toast.info('You have been logged out.');
    console.log('Logout process complete.');
  };

  return {
    login,
    logout,
    isLoggingIn,
    error,
  };
}