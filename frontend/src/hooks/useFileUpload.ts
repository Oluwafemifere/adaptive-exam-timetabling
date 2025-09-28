import { api, uploadFile, uploadMultipleFiles, downloadFile } from './api';
import { 
  Constraint, 
  ExamSlot, 
  Conflict, 
  OptimizationProgress 
} from '../store/schedulingSlice';

// Data upload types
export interface FileValidationResult {
  fileName: string;
  isValid: boolean;
  errors: string[];
  warnings: string[];
  recordCount: number;
}

export interface UploadResult {
  uploadId: string;
  files: FileValidationResult[];
  overallValid: boolean;
  message: string;
}

// Optimization types
export interface OptimizationRequest {
  constraints: Constraint[];
  parameters?: {
    maxTimeMinutes?: number;
    populationSize?: number;
    maxGenerations?: number;
    mutationRate?: number;
    crossoverRate?: number;
  };
}

export interface OptimizationResult {
  scheduleId: string;
  schedule: ExamSlot[];
  conflicts: Conflict[];
  statistics: {
    totalExams: number;
    totalConflicts: number;
    roomUtilization: number;
    processingTime: number;
    objectiveValue: number;
  };
}

// Schedule manipulation types
export interface ExamMoveRequest {
  examId: string;
  newDate: string;
  newTimeSlot: string;
  newRoomCode?: string;
}

export interface BulkExamUpdate {
  updates: Array<{
    examId: string;
    changes: Partial<ExamSlot>;
  }>;
}

// Scheduling API functions
export const schedulingApi = {
  // File upload and validation
  uploadFiles: async (
    files: File[], 
    onProgress?: (fileIndex: number, progress: number) => void
  ): Promise<UploadResult> => {
    return await uploadMultipleFiles('/data/upload', files, {}, onProgress);
  },

  uploadSingleFile: async (
    file: File,
    fileType: string,
    onProgress?: (progress: number) => void
  ): Promise<FileValidationResult> => {
    return await uploadFile('/data/upload', file, { fileType }, onProgress);
  },

  // Validate uploaded data
  validateData: (uploadId: string) =>
    api.post<FileValidationResult[]>('/data/validate', { uploadId }),

  // Get validation results
  getValidationResults: (uploadId: string) =>
    api.get<FileValidationResult[]>(`/data/validation/${uploadId}`),

  // Data export
  exportData: (
    dataType: string,
    format: 'csv' | 'json' | 'excel',
    filters?: any
  ) =>
    downloadFile(
      `/data/export/${dataType}`,
      `${dataType}.${format}`,
      { params: { format, ...filters } }
    ),

  // Constraint management
  getConstraints: () => api.get<Constraint[]>('/scheduling/constraints'),

  updateConstraints: (constraints: Constraint[]) =>
    api.put<Constraint[]>('/scheduling/constraints', constraints),

  resetConstraints: () =>
    api.post<Constraint[]>('/scheduling/constraints/reset'),

  getConstraintTemplates: () =>
    api.get<Constraint[]>('/scheduling/constraints/templates'),

  saveConstraintTemplate: (name: string, constraints: Constraint[]) =>
    api.post('/scheduling/constraints/templates', { name, constraints }),

  // Optimization
  startOptimization: (request: OptimizationRequest) =>
    api.post<{ jobId: string }>('/scheduling/optimize', request),

  stopOptimization: (jobId: string) =>
    api.post(`/scheduling/optimize/${jobId}/stop`),

  getOptimizationStatus: (jobId: string) =>
    api.get<OptimizationProgress>(`/scheduling/optimize/${jobId}/status`),

  getOptimizationResult: (jobId: string) =>
    api.get<OptimizationResult>(`/scheduling/optimize/${jobId}/result`),

  // Schedule management
  getSchedules: (params?: {
    startDate?: string;
    endDate?: string;
    roomIds?: string[];
    courseIds?: string[];
    includeConflicts?: boolean;
  }) =>
    api.get<ExamSlot[]>('/scheduling/schedules', { params }),

  getSchedule: (scheduleId: string) =>
    api.get<{
      schedule: ExamSlot[];
      conflicts: Conflict[];
      metadata: any;
    }>(`/scheduling/schedules/${scheduleId}`),

  createSchedule: (schedule: Omit<ExamSlot, 'id'>[]) =>
    api.post<{ scheduleId: string; schedule: ExamSlot[] }>('/scheduling/schedules', {
      schedule,
    }),

  updateSchedule: (scheduleId: string, schedule: ExamSlot[]) =>
    api.put<ExamSlot[]>(`/scheduling/schedules/${scheduleId}`, { schedule }),

  deleteSchedule: (scheduleId: string) =>
    api.delete(`/scheduling/schedules/${scheduleId}`),

  // Individual exam management
  updateExam: (examId: string, updates: Partial<ExamSlot>) =>
    api.patch<ExamSlot>(`/scheduling/exams/${examId}`, updates),

  moveExam: (examId: string, moveRequest: Omit<ExamMoveRequest, 'examId'>) =>
    api.patch<ExamSlot>(`/scheduling/exams/${examId}/move`, moveRequest),

  bulkUpdateExams: (updates: BulkExamUpdate) =>
    api.patch<ExamSlot[]>('/scheduling/exams/bulk', updates),

  // Conflict management
  getConflicts: (scheduleId?: string) =>
    api.get<Conflict[]>('/scheduling/conflicts', {
      params: scheduleId ? { scheduleId } : undefined,
    }),

  resolveConflict: (conflictId: string, resolution?: any) =>
    api.post<Conflict>(`/scheduling/conflicts/${conflictId}/resolve`, resolution),

  getConflictSuggestions: (conflictId: string) =>
    api.get<Array<{
      type: string;
      description: string;
      impact: number;
      autoApplicable: boolean;
      parameters: any;
    }>>(`/scheduling/conflicts/${conflictId}/suggestions`),

  autoResolveConflicts: (
    conflictIds: string[],
    strategy: 'minimal_change' | 'optimal_solution' | 'greedy'
  ) =>
    api.post<{
      resolved: string[];
      failed: Array<{ conflictId: string; reason: string }>;
      newConflicts: string[];
    }>('/scheduling/conflicts/auto-resolve', { conflictIds, strategy }),

  // Room and resource management
  getRooms: () =>
    api.get<Array<{
      id: string;
      code: string;
      name: string;
      building: string;
      capacity: number;
      type: string;
      facilities: string[];
      availability: any;
    }>>('/resources/rooms'),

  updateRoomAvailability: (roomId: string, availability: any) =>
    api.patch(`/resources/rooms/${roomId}/availability`, availability),

  getRoomUtilization: (
    startDate?: string,
    endDate?: string,
    roomIds?: string[]
  ) =>
    api.get<Array<{
      roomId: string;
      roomCode: string;
      utilization: number;
      totalSlots: number;
      occupiedSlots: number;
      peakUtilization: number;
    }>>('/analytics/room-utilization', {
      params: { startDate, endDate, roomIds: roomIds?.join(',') },
    }),

  // Invigilator management
  getInvigilators: () =>
    api.get<Array<{
      id: string;
      name: string;
      email: string;
      department: string;
      maxExamsPerDay: number;
      availability: any;
      assignedExams: string[];
    }>>('/resources/invigilators'),

  assignInvigilator: (examId: string, invigilatorId: string) =>
    api.post(`/scheduling/exams/${examId}/assign-invigilator`, {
      invigilatorId,
    }),

  autoAssignInvigilators: (scheduleId: string) =>
    api.post<{
      assignments: Array<{ examId: string; invigilatorId: string }>;
      unassigned: string[];
    }>(`/scheduling/schedules/${scheduleId}/auto-assign-invigilators`),

  // Analytics and reporting
  getScheduleStatistics: (scheduleId: string) =>
    api.get<{
      totalExams: number;
      totalStudents: number;
      totalConflicts: number;
      roomUtilization: number;
      timeDistribution: any;
      departmentStats: any;
    }>(`/analytics/schedule/${scheduleId}/statistics`),

  getConflictAnalysis: (scheduleId: string) =>
    api.get<{
      byType: Record<string, number>;
      bySeverity: Record<string, number>;
      byTimeSlot: any;
      byRoom: any;
      trends: any;
    }>(`/analytics/schedule/${scheduleId}/conflicts`),

  generateReport: (
    type: 'student_schedule' | 'room_schedule' | 'conflict_summary' | 'statistics',
    format: 'pdf' | 'csv' | 'excel',
    parameters: any
  ) =>
    api.post<{ reportId: string; downloadUrl: string }>('/reports/generate', {
      type,
      format,
      parameters,
    }),

  downloadReport: (reportId: string, fileName?: string) =>
    downloadFile(`/reports/${reportId}/download`, fileName),

  // Schedule templates
  getScheduleTemplates: () =>
    api.get<Array<{
      id: string;
      name: string;
      description: string;
      constraints: Constraint[];
      parameters: any;
      createdBy: string;
      createdAt: string;
    }>>('/scheduling/templates'),

  saveScheduleTemplate: (
    name: string,
    description: string,
    constraints: Constraint[],
    parameters: any
  ) =>
    api.post('/scheduling/templates', {
      name,
      description,
      constraints,
      parameters,
    }),

  applyScheduleTemplate: (templateId: string, scheduleId: string) =>
    api.post(`/scheduling/templates/${templateId}/apply`, { scheduleId }),

  // Historical data and comparison
  getScheduleHistory: (limit: number = 10) =>
    api.get<Array<{
      id: string;
      name: string;
      createdAt: string;
      createdBy: string;
      examCount: number;
      conflictCount: number;
      objectiveValue: number;
    }>>('/scheduling/history', { params: { limit } }),

  compareSchedules: (scheduleIds: string[]) =>
    api.post<{
      comparison: Array<{
        scheduleId: string;
        metrics: any;
        ranking: number;
      }>;
      recommendations: string[];
    }>('/analytics/compare-schedules', { scheduleIds }),

  // System preferences and settings
  getSystemSettings: () =>
    api.get<{
      optimization: any;
      constraints: any;
      notifications: any;
      display: any;
    }>('/system/settings'),

  updateSystemSettings: (settings: any) =>
    api.patch('/system/settings', settings),

  // Backup and restore
  createBackup: (includeData: boolean = true) =>
    api.post<{ backupId: string; downloadUrl: string }>('/system/backup', {
      includeData,
    }),

  restoreFromBackup: (backupFile: File) =>
    uploadFile('/system/restore', backupFile),

  // WebSocket connection info
  getWebSocketToken: () =>
    api.get<{ token: string; endpoint: string }>('/ws/token'),
};