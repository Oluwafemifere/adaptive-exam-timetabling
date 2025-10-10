  // frontend/src/services/api.ts
  import axios from 'axios';
  import { config } from '../config';
  import { useAppStore } from '../store';
  import { toast } from 'sonner';
  import { SessionSetupCreate } from '../pages/SessionSetup';
  import { 
    SystemConfiguration,
    SystemConfigurationDetails,
    SystemConfigSavePayload,
    AdminUserCreatePayload,
    UserUpdatePayload,
    PaginatedUserResponse,
    StudentSelfRegisterPayload,
    StaffSelfRegisterPayload 
  } from '../store/types';

  const apiService = axios.create({
    baseURL: config.api.baseUrl,
    timeout: config.api.timeout,
  });

  apiService.interceptors.request.use(
    (axiosConfig) => {
      const token = localStorage.getItem('authToken');
      if (token) {
        axiosConfig.headers.Authorization = `Bearer ${token}`;
      }
      return axiosConfig;
    },
    (error) => Promise.reject(error)
  );

  apiService.interceptors.response.use(
    (response) => response,
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

    selfRegisterStudent: (payload: StudentSelfRegisterPayload) => apiService.post('/auth/register/student', payload),
    selfRegisterStaff: (payload: StaffSelfRegisterPayload) => apiService.post('/auth/register/staff', payload),
    adminCreateUser: (userData: AdminUserCreatePayload) => apiService.post('/users/admin', userData),
    getUserManagementData: (params: { page?: number, page_size?: number, search_term?: string, role_filter?: string, status_filter?: string }) => 
      apiService.get<PaginatedUserResponse>('/users/', { params }),
    updateUser: (userId: string, userData: UserUpdatePayload) => apiService.put(`/users/${userId}`, userData),
    deleteUser: (userId: string) => apiService.delete(`/users/${userId}`),

    getActiveSession: () => apiService.get('/sessions/active'),
    getCurrentUser: () => apiService.get('/users/me'),
    
    getDashboardKpis: (sessionId: string) => apiService.get(`/dashboard/${sessionId}/kpis`),
    getConflictHotspots: (sessionId: string) => apiService.get(`/dashboard/${sessionId}/conflict-hotspots`),
    getTopBottlenecks: (sessionId: string) => apiService.get(`/dashboard/${sessionId}/top-bottlenecks`),
    getAuditHistory: (page = 1, pageSize = 5) => apiService.get('/system/audit-history', { params: { page, page_size: pageSize } }),

    getLatestTimetableForActiveSession: () => apiService.get('/timetables/active/latest'),
    getJobStatus: (jobId: string) => apiService.get(`/jobs/${jobId}`),
    getPortalData: (userId: string) => apiService.get(`/portal/${userId}`),
    
    startScheduling: (data: {configuration_id: string }) => apiService.post('/scheduling/generate', data),
    cancelScheduling: (jobId: string) => apiService.post(`/jobs/${jobId}/cancel`),
    
    uploadFile: (formData: FormData, entityType: string, academicSessionId: string) => {
      return apiService.post(`/uploads/${academicSessionId}/${entityType}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },

    getAllReportsAndRequests: (params: { limit?: number; statuses?: string[]; start_date?: string; end_date?: string; }) => 
      apiService.get('/notifications/reports-and-requests', { params }),

    // --- SESSION SETUP ENDPOINTS ---
    createExamSessionSetup: (setupData: SessionSetupCreate) => apiService.post('/setup/session', setupData),
    getSessionSummary: (sessionId: string) => apiService.get(`/setup/session/${sessionId}/summary`),
    processStagedData: (sessionId: string) => apiService.post(`/setup/session/${sessionId}/process-data`),
    getStagedData: (sessionId: string, entityType: string) => apiService.get(`/setup/staging-data/${sessionId}/${entityType}`),
    updateStagedRecord: (entityType: string, recordPk: string, payload: any) => apiService.put(`/setup/staging-data/${entityType}/${recordPk}`, payload),
    
    // --- CONFIGURATION API CALLS ---
    getSystemConfigurationList: () => apiService.get<SystemConfiguration[]>('/configurations/'),
    getSystemConfigurationDetails: (configId: string) => apiService.get<SystemConfigurationDetails>(`/configurations/${configId}`),
    saveSystemConfiguration: (payload: SystemConfigSavePayload) => {
      return payload.id
        ? apiService.put(`/configurations/${payload.id}`, payload)
        : apiService.post('/configurations/', payload);
    },
    deleteSystemConfiguration: (configId: string) => apiService.delete(`/configurations/${configId}`),
    setDefaultSystemConfiguration: (configId: string) => apiService.post(`/configurations/${configId}/set-default`),
    
    getSuccessfulJobsForSession: (sessionId: string) => apiService.get(`/jobs/sessions/${sessionId}/successful`),
    getJobResult: (jobId: string) => apiService.get(`/jobs/${jobId}/result`),
    publishVersion: (versionId: string) => apiService.post(`/timetables/versions/${versionId}/publish`),
  };

  export default apiService;