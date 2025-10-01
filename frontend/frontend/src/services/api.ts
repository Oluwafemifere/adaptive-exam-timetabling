// frontend/src/services/api.ts

import axios, { AxiosError } from 'axios';
import { config } from '../config';
import type { TimetableGenerationRequest } from '../store/types';
import { useAuthStore } from '../hooks/useAuth';

const api = axios.create({
  baseURL: config.api.baseUrl,
  timeout: config.api.timeout,
});

// Request interceptor to include the auth token
api.interceptors.request.use(
  (axiosConfig) => {
    const token = useAuthStore.getState().token;
    if (token) {
      axiosConfig.headers.Authorization = `Bearer ${token}`;
    }
    return axiosConfig;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle expired tokens
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

// --- API Endpoint Functions ---
// Authentication
export interface LoginCredentials {
  username: string;
  password: string;
}
export const login = (credentials: URLSearchParams) =>
  api.post('/auth/token', credentials);

// File Uploads
export const uploadFiles = (formData: FormData, entityType: string) =>
  api.post(`/uploads/?entity_type=${entityType}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

// Timetable and Exams
export const fetchTimetable = (versionId: string) =>
  api.get(`/timetables/versions/${versionId}`);
export const fetchActiveTimetable = () =>
  api.get('/timetables/active/latest');

export const updateExam = (
  examId: string,
  data: { date?: string; timeSlot?: string; [key: string]: unknown }
) => api.put(`/exams/${examId}`, data);

// Scheduling Engine
export const startScheduling = (data: TimetableGenerationRequest) =>
  api.post('/scheduling/generate', data);
export const getJobStatus = (jobId: string) => api.get(`/jobs/${jobId}`);
export const cancelJob = (jobId: string) => api.delete(`/jobs/${jobId}`);

// Conflicts
export const fetchConflicts = (versionId: string) =>
  api.get(`/scheduling/conflicts/${versionId}`);
export const resolveConflict = ({
  conflictId,
  resolution,
}: {
  conflictId: string;
  resolution: Record<string, unknown>;
}) => api.post(`/conflicts/${conflictId}/resolve`, resolution);

// Reports
export const generateReport = (
  sessionId: string,
  {
    report_type,
    options,
  }: { report_type: string; options: Record<string, unknown> }
) => api.post(`/system/reports/${sessionId}`, { report_type, options });

// Dashboard / KPIs
export const fetchKPIData = (sessionId: string) =>
  api.get(`/system/dashboard/${sessionId}`);

// User Management
export const fetchUsers = () => api.get('/users/');

// Academic Sessions
export const fetchAcademicSessions = () => api.get('/sessions/');

// Generic admin data fetcher.
// This returns the data array directly. The hook expecting T[] uses this.
export const fetchAllEntities = async (entityType: string) => {
  const response = await api.get(`/admin/data/${entityType}`);
  // assume backend returns { data: [...] } or plain array; normalize both cases
  // prefer response.data.data when present.
  // this avoids breaking change if backend wraps results.
  if (response.data && typeof response.data === 'object' && 'data' in response.data) {
    return response.data.data;
  }
  return response.data;
};