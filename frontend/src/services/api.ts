// frontend/src/services/api.ts
import axios from 'axios';
import { config } from '../config';
import { useAppStore } from '../store';
import { toast } from 'sonner';

// Create an Axios instance
const apiService = axios.create({
  baseURL: config.api.baseUrl,
  timeout: config.api.timeout,
});

// Request Interceptor: Attaches the auth token to every outgoing request
apiService.interceptors.request.use(
  (axiosConfig) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      axiosConfig.headers.Authorization = `Bearer ${token}`;
    }
    return axiosConfig;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Handles 401 Unauthorized errors globally
apiService.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      useAppStore.getState().setAuthenticated(false, null);
      localStorage.removeItem('authToken');
      toast.error('Session expired. Please log in again.');
    }
    return Promise.reject(error);
  }
);

// Define API methods
export const api = {
  login: async (username: string, password: string): Promise<{ success: boolean; data: { access_token: string } }> => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const response = await apiService.post('/auth/token', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return { success: true, data: response.data };
  },

  getActiveSession: () => apiService.get('/sessions/active'),
  
  getCurrentUser: () => apiService.get('/users/me'),
  
  getDashboardKpis: (sessionId: string) => apiService.get(`/system/dashboard/${sessionId}`),
  
  getLatestTimetableForActiveSession: () => apiService.get('/timetables/active/latest'),
  
  getJobStatus: (jobId: string) => apiService.get(`/jobs/${jobId}`),

  // --- Portal Data Endpoint ---
  getPortalData: (userId: string) => apiService.get(`/portal/${userId}`),
  
  startScheduling: (data: any) => {
    return apiService.post('/scheduling/generate', data);
  },
  
  cancelScheduling: (jobId: string) => apiService.delete(`/jobs/${jobId}`),
  
  uploadFile: (formData: FormData, entityType: string) => {
    return apiService.post(`/uploads/?entity_type=${entityType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};


export default apiService;