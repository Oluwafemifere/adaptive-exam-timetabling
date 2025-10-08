// frontend/src/services/api.ts
import axios from 'axios';
import { config } from '../config';
import { useAppStore } from '../store';
import { toast } from 'sonner';
import { SessionSetupCreate } from '../pages/SessionSetup'; // Import type from component

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

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
}

export interface SystemConfiguration {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
}

export interface ConstraintParameter {
  key: string;
  type: string;
  value: any;
}

export interface Constraint {
  id: string;
  name: string;
  description: string;
  type: 'hard' | 'soft';
  category_id: string;
  is_enabled: boolean;
  weight: number;
  parameters: ConstraintParameter[];
}

export interface SystemConfigurationDetails extends SystemConfiguration {
  solver_parameters: Record<string, any>;
  constraints: Constraint[];
}

export interface SystemConfigConstraintsUpdate {
  constraints: {
    constraint_id: string;
    is_enabled: boolean;
    weight: number;
    custom_parameters: ConstraintParameter[];
  }[];
}
export interface SystemConfigRulesUpdate {
  constraints: { // The API endpoint expects a key named 'constraints' for the update
    rule_id: string;
    is_enabled: boolean;
    weight: number;
    parameter_overrides: Record<string, any>;
  }[];
}

// Define API methods
export const api = {
  login: async (username: string, password: string): Promise<{ success: boolean; data: LoginResponse }> => {
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
  
  // --- UPDATED & NEW DASHBOARD ENDPOINTS ---
  getDashboardKpis: (sessionId: string) => apiService.get(`/dashboard/${sessionId}/kpis`),
  getConflictHotspots: (sessionId: string) => apiService.get(`/dashboard/${sessionId}/conflict-hotspots`),
  getTopBottlenecks: (sessionId: string) => apiService.get(`/dashboard/${sessionId}/top-bottlenecks`),
  getAuditHistory: (page = 1, pageSize = 5) => apiService.get('/system/audit-history', { params: { page, page_size: pageSize } }),
  // --- END ---

  getLatestTimetableForActiveSession: () => apiService.get('/timetables/active/latest'),
  
  getJobStatus: (jobId: string) => apiService.get(`/jobs/${jobId}`),

  getPortalData: (userId: string) => apiService.get(`/portal/${userId}`),
  
  startScheduling: (data: { session_id: string, configuration_id: string }) => {
    return apiService.post('/scheduling/generate', data);
  },
  
  cancelScheduling: (jobId: string) => apiService.delete(`/jobs/${jobId}`),
  
  uploadFile: (formData: FormData, entityType: string, academicSessionId: string) => {
    return apiService.post(`/uploads/${academicSessionId}/${entityType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getAllReportsAndRequests: (params: {
    limit?: number;
    statuses?: string[];
    start_date?: string;
    end_date?: string;
  }) => apiService.get('/notifications/reports-and-requests', { params }),

  // --- NEW SESSION SETUP ENDPOINTS ---
  createExamSessionSetup: (setupData: SessionSetupCreate) => apiService.post('/setup/session', setupData),
  getSessionSummary: (sessionId: string) => apiService.get(`/setup/session/${sessionId}/summary`),
  getAllConstraintConfigurations: () => apiService.get<SystemConfiguration[]>('/system/constraint-configs'),
  getAllSystemConfigurations: () => apiService.get<SystemConfiguration[]>('/system/system-configs'),
  getConfigurationDetails: (configId: string) => apiService.get<SystemConfigurationDetails>(`/system/constraint-configs/${configId}`),
  updateConfigurationRules: (configId: string, payload: SystemConfigRulesUpdate) => apiService.put(`/system/constraint-configs/${configId}/rules`, payload),
  cloneConfiguration: (payload: { name: string; description?: string; source_config_id: string }) => apiService.post('/system/configs/clone', payload),
  setDefaultConfiguration: (configId: string) => apiService.post(`/system/configs/${configId}/set-default`),
  deleteConfiguration: (configId: string) => apiService.delete(`/system/configs/${configId}`),
};


export default apiService;