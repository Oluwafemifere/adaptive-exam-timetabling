// frontend/src/hooks/useApi.ts

import { useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as api from '../services/api';
import { useAppStore } from '../store';
import axios from 'axios';
import type {
  TimetableGenerationRequest,
  Conflict,
  KPIData,
  ExamUpdatePayload,
  AcademicSession,
  Course,
  Room,
  TimetableResponse,
  RenderableExam,
  TimetableResult,
  ActiveTimetableResponse,
  Assignment,
  TimeSlot,
} from '../store/types';
import { useAuthStore } from './useAuth';
import { config, timetable } from '../config';

const apiClient = axios.create({
  baseURL: '/api/v1',
});

// --- Real-time Job Status Hook --- (unchanged)
export const useJobSocket = (jobId: string | null) => {
  const queryClient = useQueryClient();
  const { setSchedulingStatus, setCurrentPage } = useAppStore();
  const { token } = useAuthStore();

  useEffect(() => {
    if (!jobId || !token) return;

    const wsUrl = `${config.websocket.url}/jobs/${jobId}?token=${token}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log(`WebSocket connected for job ${jobId}`);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WS Message:", data);

        setSchedulingStatus({
          phase: data.solver_phase || useAppStore.getState().schedulingStatus.phase,
          progress: data.progress_percentage || 0,
          metrics: { ...useAppStore.getState().schedulingStatus.metrics, ...(data.result_data || {}) }
        });

        if (['completed', 'failed', 'cancelled'].includes(data.status)) {
          setSchedulingStatus({ isRunning: false, phase: data.status, progress: data.status === 'completed' ? 100 : data.progress_percentage });

          if (data.status === 'completed') {
            toast.success("Scheduling completed!", {
              description: "Loading the generated timetable...",
            });
            queryClient.invalidateQueries({ queryKey: ['timetable', 'latest'] });
            queryClient.invalidateQueries({ queryKey: ['conflicts', 'latest'] });
            setCurrentPage('timetable');
          } else {
            toast.error(`Scheduling ${data.status}`, {
              description: data.error_message || 'An unexpected error occurred.'
            });
          }
          socket.close();
        }
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
        toast.error("Received an invalid message from the server.");
      }
    };

    socket.onclose = () => console.log(`WebSocket disconnected for job ${jobId}`);
    socket.onerror = (error) => {
      console.error("WebSocket Error:", error);
      toast.error("Real-time update connection failed.");
      setSchedulingStatus({ isRunning: false, phase: 'error', metrics: { error_message: 'Could not connect to the real-time update service.' } });
    };

    return () => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [jobId, setSchedulingStatus, token, queryClient, setCurrentPage]);
};

// --- API Hooks ---
export const useAcademicSessions = () => {
  const { isAuthenticated } = useAuthStore();
  return useQuery<AcademicSession[], Error>({
    queryKey: ['academicSessions'],
    queryFn: () => api.fetchAcademicSessions().then(res => res.data),
    enabled: isAuthenticated,
  });
};

// Generic fetch-all hook
export const useAllEntities = <T,>(entityType: string) => {
  const { isAuthenticated } = useAuthStore();
  return useQuery<T[], Error>({
    queryKey: ['allEntities', entityType],
    queryFn: async () => {
      // fetchAllEntities returns the raw data array (services/api.ts updated)
      return api.fetchAllEntities(entityType);
    },
    enabled: isAuthenticated,
  });
};

// Timetable and Exam Hooks
export function useTimetable(versionId: string | 'latest' = 'latest') {
  return useQuery<TimetableResult, Error, RenderableExam[]>({
    queryKey: ['timetable', versionId],
    queryFn: async () => {
      const response = await apiClient.get<TimetableResponse>(`/timetables/versions/${versionId}`);
      return response.data.data;
    },
    select: (data): RenderableExam[] => {
        if (!data || !data.solution?.assignments) return [];
        return Object.values(data.solution.assignments).map((a: Assignment) => ({
            id: a.exam_id,
            date: a.date,
            startTime: a.start_time,
            endTime: a.end_time,
            courseCode: a.course_code,
            courseName: a.course_title,
            departments: [a.department_name],
            room: a.rooms.map(r => r.code).join(', ') || 'N/A',
            building: a.rooms.map(r => r.building_name).join(', ') || 'N/A',
            instructor: a.instructor_name || 'N/A',
            invigilator: a.invigilators.map(i => i.name).join(', ') || 'N/A',
            expectedStudents: a.capacity_metrics.expected_students,
            roomCapacity: a.capacity_metrics.total_assigned_capacity,
            examType: a.is_practical ? 'Practical' : 'Theory',
            conflicts: a.conflicts,
            originalAssignment: a,
        }));
    },
  });
}


export const useActiveTimetable = () => {
  const { isAuthenticated } = useAuthStore();
  const activeTimetableQuery = useQuery({
    queryKey: ['activeTimetable'],
    queryFn: () => api.fetchActiveTimetable().then(res => res.data as ActiveTimetableResponse),
    enabled: isAuthenticated,
  });

  // Fetch lookup data
  const coursesQuery = useAllEntities<Course>('courses');
  const roomsQuery = useAllEntities<Room>('rooms');

  const isDataLoading = activeTimetableQuery.isLoading || coursesQuery.isLoading || roomsQuery.isLoading;

  type ProcessedActiveTimetable = {
    renderableExams: RenderableExam[];
    conflicts: Conflict[];
    uniqueRooms: string[];
    uniqueDepartments: string[];
    dateRange: string[];
    timeSlots: TimeSlot[];
    originalData: ActiveTimetableResponse | null;
  };

  const processedData = useMemo<ProcessedActiveTimetable>(() => {
    if (isDataLoading || !activeTimetableQuery.data?.data.timetable.solution?.assignments) {
      return {
        renderableExams: [],
        conflicts: [],
        uniqueRooms: [],
        uniqueDepartments: [],
        dateRange: [],
        timeSlots: [],
        originalData: null,
      };
    }
      
    const assignmentsArray = Object.values(activeTimetableQuery.data.data.timetable.solution.assignments);

    const renderableExams = assignmentsArray.map((a: Assignment): RenderableExam => {
      return {
          id: a.exam_id,
          date: a.date,
          startTime: a.start_time,
          endTime: a.end_time,
          courseCode: a.course_code,
          courseName: a.course_title,
          departments: [a.department_name],
          room: a.rooms.map(r => r.code).join(', ') || 'N/A',
          building: a.rooms.map(r => r.building_name).join(', ') || 'N/A',
          instructor: a.instructor_name || 'N/A',
          invigilator: a.invigilators.map(i => i.name).join(', ') || 'N/A',
          expectedStudents: a.capacity_metrics.expected_students,
          roomCapacity: a.capacity_metrics.total_assigned_capacity,
          examType: a.is_practical ? 'Practical' : 'Theory',
          conflicts: a.conflicts,
          originalAssignment: a,
      };
    });

    const uniqueRooms = Array.from(new Set(renderableExams.flatMap(e => e.room))).sort();
    const uniqueDepartments = Array.from(new Set(renderableExams.flatMap(e => e.departments))).sort();


    const allDates = assignmentsArray
        .map(a => a.date)
        .filter(Boolean) as string[];
    const uniqueDates = [...new Set(allDates)].sort();
    
    // UPDATED: Generate hourly time slots based on config
    const timeSlots: TimeSlot[] = [];
    for (let hour = timetable.dayStartHour; hour < timetable.dayEndHour; hour++) {
      const nextHour = hour + 1;
      timeSlots.push({
        id: `${hour}:00`,
        label: `${hour.toString().padStart(2, '0')}:00 - ${nextHour.toString().padStart(2, '0')}:00`,
        start_hour: hour,
      });
    }

    return {
      renderableExams,
      conflicts: activeTimetableQuery.data.data.timetable.solution.conflicts || [],
      uniqueRooms,
      uniqueDepartments,
      dateRange: uniqueDates,
      timeSlots: timeSlots,
      originalData: activeTimetableQuery.data,
    };
  }, [activeTimetableQuery.data, isDataLoading]);

  return {
    ...activeTimetableQuery,
    isLoading: isDataLoading,
    data: processedData
  };
};

export const useUpdateExam = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ examId, data }: { examId: string; data: ExamUpdatePayload }) => api.updateExam(examId, data),
    onSuccess: (_, variables) => {
      toast.success(`Exam ${variables.examId} updated successfully!`);
      queryClient.invalidateQueries({ queryKey: ['timetable'] });
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to update exam: ${error.message}`);
    },
  });
};

// Conflict Hooks
export const useConflicts = (versionId = 'latest') => {
  const { setConflicts } = useAppStore.getState();
  const { isAuthenticated } = useAuthStore();
  return useQuery<Conflict[], Error>({
    queryKey: ['conflicts', versionId],
    queryFn: () => api.fetchConflicts(versionId).then(res => {
      const conflictsData = (res.data.data.conflicts || []) as Conflict[];
      setConflicts(conflictsData);
      return conflictsData;
    }),
    enabled: isAuthenticated && !!versionId,
  });
};

export const useResolveConflict = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables: { conflictId: string; resolution: Record<string, unknown> }) => api.resolveConflict(variables),
    onSuccess: () => {
      toast.success('Conflict resolution submitted!');
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['timetable'] });
    },
    onError: (error: Error) => {
      toast.error(`Conflict resolution failed: ${error.message}`);
    },
  });
};

// Scheduling Hooks
export const useScheduling = () => {
  const { setSchedulingStatus } = useAppStore();

  const startScheduling = useMutation({
    mutationFn: (data: TimetableGenerationRequest) => api.startScheduling(data),
    onSuccess: (response) => {
      const jobId = response.data.job_id;
      toast.success(`Scheduling process initiated with Job ID: ${jobId}`);
      setSchedulingStatus({ isRunning: true, phase: 'pending', progress: 0, jobId });
    },
    onError: (error: Error) => {
      toast.error(`Scheduling failed to start: ${error.message}`);
      setSchedulingStatus({ isRunning: false, phase: 'error', jobId: null });
    }
  });

  const cancelScheduling = useMutation({
    mutationFn: (jobId: string) => api.cancelJob(jobId),
    onSuccess: (_, jobId) => {
      toast.warning(`Request to cancel job ${jobId} sent.`);
      setSchedulingStatus({ isRunning: false, phase: 'cancelled' });
    },
    onError: (error: Error) => {
      toast.error(`Failed to cancel job: ${error.message}`);
    }
  });

  return { startScheduling, cancelScheduling };
};

// File Upload Hook
export const useFileUpload = () => {
  const { setUploadStatus } = useAppStore();
  return useMutation({
    mutationFn: ({ formData, entityType }: { formData: FormData, entityType: string }) => {
      setUploadStatus({ isUploading: true, progress: 0 });
      return api.uploadFiles(formData, entityType);
    },
    onSuccess: (_, variables) => {
      toast.success(`'${variables.entityType}' file uploaded and validation started.`);
      setUploadStatus({ isUploading: false, progress: 100 });
    },
    onError: (error: Error, variables) => {
      toast.error(`'${variables.entityType}' upload failed: ${error.message}`);
      setUploadStatus({ isUploading: false });
    },
  });
};

// Report Generation Hook
export const useGenerateReport = () => {
  const { activeSessionId } = useAppStore();
  return useMutation({
    mutationFn: (variables: { report_type: string; options: Record<string, unknown> }) => {
      if (!activeSessionId) throw new Error("No active session selected.");
      return api.generateReport(activeSessionId, variables);
    },
    onSuccess: (response) => {
      toast.success('Report generation started!', { description: response.data.message });
    },
    onError: (error: Error) => {
      toast.error(`Failed to generate report: ${error.message}`);
    },
  });
};

// KPI Data Hook
export const useKPIData = () => {
  const { setKpiData } = useAppStore.getState();
  const { isAuthenticated } = useAuthStore();
  const { activeSessionId } = useAppStore();

  return useQuery<KPIData, Error>({
    queryKey: ['kpiData', activeSessionId],
    queryFn: () => {
      if (!activeSessionId) throw new Error("No active session selected.");
      return api.fetchKPIData(activeSessionId).then(res => {
        const kpi = res.data.data as KPIData;
        setKpiData(kpi);
        return kpi;
      });
    },
    enabled: isAuthenticated && !!activeSessionId,
  });
};