// frontend/src/services/api.ts
import axios from 'axios';
import { config } from '../config';
import { useAppStore } from '../store';
import { toast } from 'sonner';
import { SessionSetupCreate } from '../pages/SessionManagement';
import {
  SystemConfiguration,
  SystemConfigurationDetails,
  SystemConfigSavePayload,
  AdminUserCreatePayload,
  UserUpdatePayload,
  PaginatedUserResponse,
  StudentSelfRegisterPayload,
  StaffSelfRegisterPayload,
  StagingBuildingCreate, StagingBuildingUpdate, StagingCourseDepartmentCreate, StagingCourseFacultyCreate,
  StagingCourseInstructorCreate, StagingCourseRegistrationCreate, StagingCourseRegistrationUpdate,
  StagingCourseCreate, StagingCourseUpdate, StagingDepartmentCreate, StagingDepartmentUpdate,
  StagingFacultyCreate, StagingFacultyUpdate, StagingProgrammeCreate, StagingProgrammeUpdate,
  StagingRoomCreate, StagingRoomUpdate, StagingStaffCreate, StagingStaffUpdate,
  StagingStaffUnavailabilityCreate, StagingStaffUnavailabilityUpdate, StagingStudentCreate, StagingStudentUpdate,
  StagingCourseDepartmentUpdate, StagingCourseFacultyUpdate,
  SchedulingJob
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

  getDashboardAnalytics: (sessionId: string) => apiService.get(`/dashboard/${sessionId}/analytics`),
  getAuditHistory: (page = 1, pageSize = 5) => apiService.get('/system/audit-history', { params: { page, page_size: pageSize } }),
  
  getAllEntityData: (sessionId: string, entityType: string) => apiService.get(`/admin/data/${sessionId}/${entityType}`),

  getLatestTimetableForActiveSession: () => apiService.get('/timetables/active/latest'),
  getJobStatus: (jobId: string) => apiService.get(`/jobs/${jobId}`),
  getPortalData: (userId: string) => apiService.get(`/portal/${userId}`),

  startScheduling: (data: {configuration_id: string }) => apiService.post('/scheduling/generate', data),
  cancelScheduling: (jobId: string) => apiService.delete(`/jobs/${jobId}`),

  uploadFilesBatch: (files: File[], academicSessionId: string) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    return apiService.post(`/uploads/upload/${academicSessionId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getAllReportsAndRequests: (params: { limit?: number; statuses?: string[]; start_date?: string; end_date?: string; }) =>
    apiService.get('/notifications/reports-and-requests', { params }),

  createExamSessionSetup: (setupData: SessionSetupCreate) => apiService.post('/setup/session', setupData),
  getSessionSummary: (sessionId: string) => apiService.get(`/setup/session/${sessionId}/summary`),
  processStagedData: (sessionId: string) => apiService.post(`/setup/session/${sessionId}/process-data`),
  getAllStagedData: (sessionId: string) => apiService.get(`/staging-records/${sessionId}`),
  updateStagedRecord: (entityType: string, recordPk: string, payload: any) => apiService.put(`/setup/staging-data/${entityType}/${recordPk}`, payload),
  getSeedingStatus: (academicSessionId: string) => apiService.get(`/seeding/${academicSessionId}/status`),
  
  // --- START: LIVE SESSION MANAGEMENT API ---
  getFullSessionDataGraph: (sessionId: string) => apiService.get(`/session-management/${sessionId}/data-graph`),
  
  getPaginatedCoursesInSession: (sessionId: string, params: { page?: number, page_size?: number }) => apiService.get(`/session-management/${sessionId}/courses`, { params }),
  createCourseInSession: (sessionId: string, payload: any) => apiService.post(`/session-management/${sessionId}/courses`, payload),
  updateCourseInSession: (sessionId: string, courseId: string, payload: any) => apiService.put(`/session-management/${sessionId}/courses/${courseId}`, payload),
  deleteCourseInSession: (sessionId: string, courseId: string) => apiService.delete(`/session-management/${sessionId}/courses/${courseId}`),
  
  createBuildingInSession: (sessionId: string, payload: any) => apiService.post(`/session-management/${sessionId}/buildings`, payload),
  updateBuildingInSession: (sessionId: string, buildingId: string, payload: any) => apiService.put(`/session-management/${sessionId}/buildings/${buildingId}`, payload),
  deleteBuildingInSession: (sessionId: string, buildingId: string) => apiService.delete(`/session-management/${sessionId}/buildings/${buildingId}`),
  
  createRoomInSession: (sessionId: string, payload: any) => apiService.post(`/session-management/${sessionId}/rooms`, payload),
  updateRoomInSession: (sessionId: string, roomId: string, payload: any) => apiService.put(`/session-management/${sessionId}/rooms/${roomId}`, payload),
  deleteRoomInSession: (sessionId: string, roomId: string) => apiService.delete(`/session-management/${sessionId}/rooms/${roomId}`),
  
  getPaginatedDepartmentsInSession: (sessionId: string, params: { page?: number, page_size?: number }) => apiService.get(`/session-management/${sessionId}/departments`, { params }),
  createDepartmentInSession: (sessionId: string, payload: any) => apiService.post(`/session-management/${sessionId}/departments`, payload),
  updateDepartmentInSession: (sessionId: string, departmentId: string, payload: any) => apiService.put(`/session-management/${sessionId}/departments/${departmentId}`, payload),
  deleteDepartmentInSession: (sessionId: string, departmentId: string) => apiService.delete(`/session-management/${sessionId}/departments/${departmentId}`),

  getPaginatedStaffInSession: (sessionId: string, params: { page?: number, page_size?: number }) => apiService.get(`/session-management/${sessionId}/staff`, { params }),
  createStaffInSession: (sessionId: string, payload: any) => apiService.post(`/session-management/${sessionId}/staff`, payload),
  updateStaffInSession: (sessionId: string, staffId: string, payload: any) => apiService.put(`/session-management/${sessionId}/staff/${staffId}`, payload),
  deleteStaffInSession: (sessionId: string, staffId: string) => apiService.delete(`/session-management/${sessionId}/staff/${staffId}`),

  getPaginatedExamsInSession: (sessionId: string, params: { page?: number, page_size?: number }) => apiService.get(`/session-management/${sessionId}/exams`, { params }),
  createExamInSession: (sessionId: string, payload: any) => apiService.post(`/session-management/${sessionId}/exams`, payload),
  updateExamInSession: (sessionId: string, examId: string, payload: any) => apiService.put(`/session-management/${sessionId}/exams/${examId}`, payload),
  deleteExamInSession: (sessionId: string, examId: string) => apiService.delete(`/session-management/${sessionId}/exams/${examId}`),
  
  getPaginatedStudentsInSession: (sessionId: string, params: { page?: number, page_size?: number }) => apiService.get(`/session-management/${sessionId}/students`, { params }),

  createStaffUnavailabilityInSession: (sessionId: string, payload: any) => apiService.post(`/session-management/${sessionId}/staff-unavailability`, payload),
  getStaffUnavailabilityInSession: (sessionId: string, staffId: string) => apiService.get(`/session-management/${sessionId}/staff/${staffId}/unavailability`),
  deleteStaffUnavailabilityInSession: (sessionId: string, unavailabilityId: string) => apiService.delete(`/session-management/${sessionId}/staff-unavailability/${unavailabilityId}`),
  // --- END: LIVE SESSION MANAGEMENT API ---

  addStagedBuilding: (sessionId: string, data: StagingBuildingCreate) => apiService.post(`/staging-records/${sessionId}/buildings`, data),
  updateStagedBuilding: (sessionId: string, code: string, data: StagingBuildingUpdate) => apiService.put(`/staging-records/${sessionId}/buildings/${code}`, data),
  deleteStagedBuilding: (sessionId: string, code: string) => apiService.delete(`/staging-records/${sessionId}/buildings/${code}`),
  
  addStagedCourseDepartment: (sessionId: string, data: StagingCourseDepartmentCreate) => apiService.post(`/staging-records/${sessionId}/course-departments`, data),
  updateStagedCourseDepartment: (sessionId: string, courseCode: string, oldDepartmentCode: string, data: StagingCourseDepartmentUpdate) => apiService.put(`/staging-records/${sessionId}/course-departments/${courseCode}/${oldDepartmentCode}`, data),
  deleteStagedCourseDepartment: (sessionId: string, courseCode: string, departmentCode: string) => apiService.delete(`/staging-records/${sessionId}/course-departments/${courseCode}/${departmentCode}`),

  addStagedCourseFaculty: (sessionId: string, data: StagingCourseFacultyCreate) => apiService.post(`/staging-records/${sessionId}/course-faculties`, data),
  updateStagedCourseFaculty: (sessionId: string, courseCode: string, oldFacultyCode: string, data: StagingCourseFacultyUpdate) => apiService.put(`/staging-records/${sessionId}/course-faculties/${courseCode}/${oldFacultyCode}`, data),
  deleteStagedCourseFaculty: (sessionId: string, courseCode: string, facultyCode: string) => apiService.delete(`/staging-records/${sessionId}/course-faculties/${courseCode}/${facultyCode}`),

  addStagedCourseInstructor: (sessionId: string, data: StagingCourseInstructorCreate) => apiService.post(`/staging-records/${sessionId}/course-instructors`, data),
  deleteStagedCourseInstructor: (sessionId: string, staffNumber: string, courseCode: string) => apiService.delete(`/staging-records/${sessionId}/course-instructors/${staffNumber}/${courseCode}`),

  addStagedCourseRegistration: (sessionId: string, data: StagingCourseRegistrationCreate) => apiService.post(`/staging-records/${sessionId}/course-registrations`, data),
  updateStagedCourseRegistration: (sessionId: string, matric: string, courseCode: string, data: StagingCourseRegistrationUpdate) => apiService.put(`/staging-records/${sessionId}/course-registrations/${matric}/${courseCode}`, data),
  deleteStagedCourseRegistration: (sessionId: string, matric: string, courseCode: string) => apiService.delete(`/staging-records/${sessionId}/course-registrations/${matric}/${courseCode}`),

  addStagedCourse: (sessionId: string, data: StagingCourseCreate) => apiService.post(`/staging-records/${sessionId}/courses`, data),
  updateStagedCourse: (sessionId: string, code: string, data: StagingCourseUpdate) => apiService.put(`/staging-records/${sessionId}/courses/${code}`, data),
  deleteStagedCourse: (sessionId: string, code: string) => apiService.delete(`/staging-records/${sessionId}/courses/${code}`),

  addStagedDepartment: (sessionId: string, data: StagingDepartmentCreate) => apiService.post(`/staging-records/${sessionId}/departments`, data),
  updateStagedDepartment: (sessionId: string, code: string, data: StagingDepartmentUpdate) => apiService.put(`/staging-records/${sessionId}/departments/${code}`, data),
  deleteStagedDepartment: (sessionId: string, code: string) => apiService.delete(`/staging-records/${sessionId}/departments/${code}`),

  addStagedFaculty: (sessionId: string, data: StagingFacultyCreate) => apiService.post(`/staging-records/${sessionId}/faculties`, data),
  updateStagedFaculty: (sessionId: string, code: string, data: StagingFacultyUpdate) => apiService.put(`/staging-records/${sessionId}/faculties/${code}`, data),
  deleteStagedFaculty: (sessionId: string, code: string) => apiService.delete(`/staging-records/${sessionId}/faculties/${code}`),

  addStagedProgramme: (sessionId: string, data: StagingProgrammeCreate) => apiService.post(`/staging-records/${sessionId}/programmes`, data),
  updateStagedProgramme: (sessionId: string, code: string, data: StagingProgrammeUpdate) => apiService.put(`/staging-records/${sessionId}/programmes/${code}`, data),
  deleteStagedProgramme: (sessionId: string, code: string) => apiService.delete(`/staging-records/${sessionId}/programmes/${code}`),

  addStagedRoom: (sessionId: string, data: StagingRoomCreate) => apiService.post(`/staging-records/${sessionId}/rooms`, data),
  updateStagedRoom: (sessionId: string, code: string, data: StagingRoomUpdate) => apiService.put(`/staging-records/${sessionId}/rooms/${code}`, data),
  deleteStagedRoom: (sessionId: string, code: string) => apiService.delete(`/staging-records/${sessionId}/rooms/${code}`),

  addStagedStaff: (sessionId: string, data: StagingStaffCreate) => apiService.post(`/staging-records/${sessionId}/staff`, data),
  updateStagedStaff: (sessionId: string, staffNumber: string, data: StagingStaffUpdate) => apiService.put(`/staging-records/${sessionId}/staff/${staffNumber}`, data),
  deleteStagedStaff: (sessionId: string, staffNumber: string) => apiService.delete(`/staging-records/${sessionId}/staff/${staffNumber}`),

  addStagedStaffUnavailability: (sessionId: string, data: StagingStaffUnavailabilityCreate) => apiService.post(`/staging-records/${sessionId}/staff-unavailability`, data),
  updateStagedStaffUnavailability: (sessionId: string, staffNumber: string, date: string, period: string, data: StagingStaffUnavailabilityUpdate) => apiService.put(`/staging-records/${sessionId}/staff-unavailability/${staffNumber}/${date}/${period}`, data),
  deleteStagedStaffUnavailability: (sessionId: string, staffNumber: string, date: string, period: string) => apiService.delete(`/staging-records/${sessionId}/staff-unavailability/${staffNumber}/${date}/${period}`),

  addStagedStudent: (sessionId: string, data: StagingStudentCreate) => apiService.post(`/staging-records/${sessionId}/students`, data),
  updateStagedStudent: (sessionId: string, matricNumber: string, data: StagingStudentUpdate) => apiService.put(`/staging-records/${sessionId}/students/${matricNumber}`, data),
  deleteStagedStudent: (sessionId: string, matricNumber: string) => apiService.delete(`/staging-records/${sessionId}/students/${matricNumber}`),
  
  getSystemConfigurationList: () => apiService.get<SystemConfiguration[]>('/configurations/'),
  getSystemConfigurationDetails: (configId: string) => apiService.get<SystemConfigurationDetails>(`/configurations/${configId}`),
  saveSystemConfiguration: (payload: SystemConfigSavePayload) => {
    return payload.id
      ? apiService.put(`/configurations/${payload.id}`, payload)
      : apiService.post('/configurations/', payload);
  },
  deleteSystemConfiguration: (configId: string) => apiService.delete(`/configurations/${configId}`),
  setDefaultSystemConfiguration: (configId: string) => apiService.post(`/configurations/${configId}/set-default`),

  getJobsList: (sessionId: string) => apiService.get<SchedulingJob[]>(`/jobs/`, { params: { session_id: sessionId, limit: 50 } }),
  getJobResult: (jobId: string) => apiService.get(`/jobs/${jobId}/result`),
  publishVersion: (versionId: string) => apiService.post(`/timetables/versions/${versionId}/publish`),

};

export default apiService;