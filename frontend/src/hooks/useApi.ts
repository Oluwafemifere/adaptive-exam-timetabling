// frontend/src/hooks/useApi.ts
import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { useAppStore } from '../store';
import { toast } from 'sonner';
import { JobStatus, Conflict, StudentExam, StaffAssignment, HistoryEntry } from '../store/types';
import { SessionSetupCreate, SessionSetupSummary } from '../pages/SessionSetup';

export function useDashboardData() {
const {
activeSessionId,
setDashboardKpis,
setConflictHotspots,
setTopBottlenecks,
setRecentActivity
} = useAppStore();

const [isLoading, setIsLoading] = useState(true);
const [error, setError] = useState<Error | null>(null);

const fetchData = useCallback(async () => {
if (!activeSessionId) {
setIsLoading(false);
return;
}

setIsLoading(true);
try {
  // Fetch all dashboard data concurrently
  const [kpisRes, hotspotsRes, bottlenecksRes, activityRes] = await Promise.all([
    api.getDashboardKpis(activeSessionId),
    api.getConflictHotspots(activeSessionId),
    api.getTopBottlenecks(activeSessionId),
    api.getAuditHistory() 
  ]);

  if (kpisRes.data) setDashboardKpis(kpisRes.data);
  if (hotspotsRes.data) setConflictHotspots(hotspotsRes.data);
  if (bottlenecksRes.data) setTopBottlenecks(bottlenecksRes.data);
  if (activityRes.data?.items) setRecentActivity(activityRes.data.items);
  
  setError(null);
} catch (err) {
  const error = err instanceof Error ? err : new Error('Failed to fetch dashboard data');
  setError(error);
  toast.error(error.message);
} finally {
  setIsLoading(false);
}

}, [activeSessionId, setDashboardKpis, setConflictHotspots, setTopBottlenecks, setRecentActivity]);

useEffect(() => {
fetchData();
// Optional: set an interval to refresh dashboard data periodically
const interval = setInterval(fetchData, 60000); // every 60 seconds
return () => clearInterval(interval);
}, [fetchData]);

return { isLoading, error, refetch: fetchData };
}

export function useJobStatusPoller(jobId: string | null) {
const { setSchedulingStatus } = useAppStore();

useEffect(() => {
if (!jobId) {
return;
}

const poll = async () => {
  try {
    const response = await api.getJobStatus(jobId);
    const job: JobStatus = response.data;
    
    setSchedulingStatus({
      jobId: job.id,
      phase: job.solver_phase || job.status,
      progress: job.progress_percentage,
      isRunning: job.status === 'running' || job.status === 'queued',
      metrics: { ...job },
    });

    if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
      clearInterval(intervalId);
      if (job.status === 'completed') toast.success('Scheduling job completed!');
      if (job.status === 'failed') toast.error(`Scheduling failed: ${job.error_message}`);
    }
  } catch (error) {
    toast.error('Could not retrieve job status.');
    clearInterval(intervalId);
  }
};

const intervalId = setInterval(poll, 3000);
poll(); 

return () => clearInterval(intervalId);

}, [jobId, setSchedulingStatus]);
}

export function useFileUpload() {
const [isPending, setIsPending] = useState(false);

const mutateAsync = async ({ formData, entityType, academicSessionId }: { formData: FormData; entityType: string; academicSessionId: string }) => {
try {
setIsPending(true);
const response = await api.uploadFile(formData, entityType, academicSessionId);
toast.success(`${entityType} file upload accepted for background processing.`);
return response.data;
} catch (error: any) {
const detail = error.response?.data?.detail || 'Upload failed.';
toast.error(`Upload failed: ${detail}`);
throw new Error(detail);
} finally {
setIsPending(false);
}
};

return { mutateAsync, isPending };
}

export function useLatestTimetable() {
const { setTimetable, setConflicts } = useAppStore();
const [isLoading, setIsLoading] = useState(true);
const [error, setError] = useState<Error | null>(null);

const fetchTimetable = useCallback(async () => {
setIsLoading(true);
setError(null);
try {
const response = await api.getLatestTimetableForActiveSession();
const apiPayload = response.data;

if (apiPayload.success && apiPayload.data) {
    setTimetable(apiPayload.data);
    const conflicts = apiPayload.data.timetable?.solution?.conflicts || [];
    setConflicts(conflicts as Conflict[]);
  } else {
    const errorMessage = apiPayload.message || 'No successful timetable found.';
    setTimetable({} as any);
    setConflicts([]);
    throw new Error(errorMessage);
  }
} catch (err) {
  const errorMessage = err instanceof Error ? err : new Error('Failed to fetch timetable');
  setError(errorMessage);
} finally {
  setIsLoading(false);
}

}, [setTimetable, setConflicts]);

return { isLoading, error, fetchTimetable };
}

// Custom hook to fetch and manage student portal data
export function useStudentPortalData() {
const { user, setStudentExams, setConflictReports } = useAppStore();
const [isLoading, setIsLoading] = useState(true);
const [error, setError] = useState<Error | null>(null);

const fetchData = useCallback(async () => {
    if (!user?.id) {
        setIsLoading(false);
        return;
    }
    setIsLoading(true);
    try {
        const response = await api.getPortalData(user.id);
        if (response.data.success) {
            const portalData = response.data.data.data;

            const schedule = (portalData.schedule || []).map((exam: any): StudentExam => ({
                id: exam.exam_id,
                courseCode: exam.course_code,
                courseName: exam.course_title,
                date: exam.date,
                startTime: exam.start_time,
                endTime: exam.end_time,
                room: exam.rooms?.[0]?.code || 'N/A',
                building: exam.rooms?.[0]?.building_name || 'N/A',
                duration: exam.duration_minutes,
            }));
            
            const conflictReports = (portalData.conflict_reports || []).map((report: any) => {
                const relatedExam = schedule.find(e => e.id === report.exam_id);
                return {
                    id: report.id,
                    studentId: report.student_id,
                    examId: report.exam_id,
                    courseCode: relatedExam?.courseCode || 'Unknown',
                    description: report.description,
                    status: report.status,
                    submittedAt: report.submitted_at,
                };
            });
            
            setStudentExams(schedule);
            setConflictReports(conflictReports);
        } else {
            throw new Error(response.data.data?.error || 'Failed to fetch portal data');
        }
    } catch (err) {
        setError(err instanceof Error ? err : new Error('An unknown error occurred'));
    } finally {
        setIsLoading(false);
    }
}, [user, setStudentExams, setConflictReports]);

useEffect(() => {
    fetchData();
}, [fetchData]);

return { isLoading, error, refetch: fetchData };

}

// Custom hook to fetch and manage staff portal data
export function useStaffPortalData() {
const { user, setStaffSchedules } = useAppStore();
const [isLoading, setIsLoading] = useState(true);
const [error, setError] = useState<Error | null>(null);

const fetchData = useCallback(async () => {
    if (!user?.id) {
        setIsLoading(false);
        return;
    }
    setIsLoading(true);
    try {
        const response = await api.getPortalData(user.id);
        if (response.data.success) {
            const portalData = response.data.data.data; 
            
            const mapToAssignment = (exam: any, role: StaffAssignment['role']): StaffAssignment => ({
                id: `${exam.exam_id}-${role}`,
                examId: exam.exam_id,
                courseCode: exam.course_code,
                courseName: exam.course_title,
                date: exam.date,
                startTime: exam.start_time,
                endTime: exam.end_time,
                room: exam.rooms?.[0]?.code || 'N/A',
                building: exam.rooms?.[0]?.building_name || 'N/A',
                role,
                status: 'assigned',
            });

            const instructorSchedule = (portalData.instructor_schedule || []).map((exam: any) => mapToAssignment(exam, 'instructor'));
            const invigilatorSchedule = (portalData.invigilator_schedule || []).map((exam: any) => mapToAssignment(exam, 'invigilator'));
            const allAssignments = [...instructorSchedule, ...invigilatorSchedule];

            const changeRequests = (portalData.change_requests || []).map((req: any) => {
                const relatedAssignment = allAssignments.find(a => a.examId === req.timetable_assignment_id);
                return {
                    id: req.id,
                    staffId: req.staff_id,
                    assignmentId: req.timetable_assignment_id,
                    courseCode: relatedAssignment?.courseCode || 'Unknown Course',
                    reason: req.reason,
                    description: req.description,
                    status: req.status,
                    submittedAt: req.submitted_at,
                };
            });

            setStaffSchedules({
                instructorSchedule,
                invigilatorSchedule,
                changeRequests,
            });
        } else {
            throw new Error(response.data.data?.error || 'Failed to fetch portal data');
        }
    } catch (err) {
        setError(err instanceof Error ? err : new Error('An unknown error occurred'));
    } finally {
        setIsLoading(false);
    }
}, [user, setStaffSchedules]);

useEffect(() => {
    fetchData();
}, [fetchData]);

return { isLoading, error, refetch: fetchData };

}

export function useAllReportsData(initialFilters: { limit?: number; statuses?: string[] } = {}) {
const { setAllReports } = useAppStore();
const [isLoading, setIsLoading] = useState(true);
const [error, setError] = useState<Error | null>(null);

const fetchData = useCallback(async (filters: { limit?: number; statuses?: string[], start_date?: string, end_date?: string } = {}) => {
setIsLoading(true);
try {
const response = await api.getAllReportsAndRequests(filters);
setAllReports(response.data);
} catch (err) {
const error = err instanceof Error ? err : new Error('Failed to fetch reports');
setError(error);
toast.error(error.message);
} finally {
setIsLoading(false);
}
}, [setAllReports]);

useEffect(() => {
fetchData(initialFilters);
}, [fetchData, initialFilters]);

return { isLoading, error, refetch: fetchData };
}

// --- NEW SESSION SETUP HOOKS ---

// Hook for session creation
export function useCreateSession() {
const [isPending, setIsPending] = useState(false);

const mutateAsync = async (data: SessionSetupCreate) => {
try {
setIsPending(true);
const response = await api.createExamSessionSetup(data);
toast.success(response.data.message);
return response.data;
} catch (error: any) {
const detail = error.response?.data?.detail || 'Failed to create session.';
toast.error(detail);
throw new Error(detail);
} finally {
setIsPending(false);
}
};

return { mutateAsync, isPending };
}

// Hook for fetching session summary
export function useSessionSummary(sessionId: string | null) {
const [data, setData] = useState<SessionSetupSummary | null>(null);
const [isLoading, setIsLoading] = useState(false);
const [error, setError] = useState<Error | null>(null);

const fetchSummary = useCallback(async () => {
if (!sessionId) return;

setIsLoading(true);
setError(null);
try {
  const response = await api.getSessionSummary(sessionId);
  setData(response.data);
} catch (err: any) {
  const detail = err.response?.data?.detail || 'Failed to fetch session summary.';
  const error = new Error(detail);
  setError(error);
  toast.error(error.message);
} finally {
  setIsLoading(false);
}

}, [sessionId]);

useEffect(() => {
if (sessionId) {
// Automatically fetch when sessionId becomes available,
// but refetch allows manual trigger.
}
}, [sessionId]);

return { data, isLoading, error, refetch: fetchSummary };
}

export function useHistoryData(page = 1, pageSize = 25) {
  const { history, setHistory } = useAppStore(state => ({
    history: state.history,
    setHistory: state.setHistory,
  }));
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [pagination, setPagination] = useState({ total: 0, pages: 1 });

  const fetchData = useCallback(async (p: number, ps: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.getAuditHistory(p, ps);
      
      if (response.data && response.data.items) {
        setHistory(response.data.items);
        setPagination({
          total: response.data.total || 0,
          pages: response.data.pages || 1,
        });
      } else {
        setHistory([]);
        setPagination({ total: 0, pages: 1 });
      }
    } catch (err) {
      const fetchError = err instanceof Error ? err : new Error('Failed to fetch audit history');
      setError(fetchError);
      toast.error(fetchError.message);
    } finally {
      setIsLoading(false);
    }
  }, [setHistory]);

  useEffect(() => {
    fetchData(page, pageSize);
  }, [fetchData, page, pageSize]);

  return { history, pagination, isLoading, error, refetch: () => fetchData(page, pageSize) };
}