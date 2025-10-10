// frontend/src/hooks/useApi.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../services/api';
import { useAppStore } from '../store';
import { toast } from 'sonner';
import { JobStatus, Conflict, StudentExam, StaffAssignment, HistoryEntry } from '../store/types';
import { SessionSetupCreate, SessionSetupSummary } from '../pages/SessionSetup';
import { config } from '../config';

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
  if (activityRes.data?.logs) setRecentActivity(activityRes.data.logs);
  
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

export function useJobStatusSocket(jobId: string | null) {
  const { 
    setSchedulingStatus, 
    addSchedulingLog, 
    clearSchedulingLogs,
    setCurrentPage,
    initializeApp
  } = useAppStore();
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId) {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      return;
    }

    if (socketRef.current) {
      socketRef.current.close();
    }

    clearSchedulingLogs();

    const wsUrl = `${config.websocket.url}/jobs/${jobId}`;
    
    addSchedulingLog(`[INFO] Connecting to job monitor at ${wsUrl}...`);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      addSchedulingLog('[INFO] Connection established. Waiting for job updates...');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const messageType = data.type || (data.status ? 'job_update' : 'unknown');

        if (messageType === 'job_update') {
          const { status, progress, phase, message } = data;
          
          if (message) {
            addSchedulingLog(`[${phase || status}] ${message}`);
          }

          setSchedulingStatus({
            jobId: data.job_id || jobId,
            phase: phase || status,
            progress: progress || 0,
            isRunning: status === 'running' || status === 'queued' || status === 'post_processing',
            metrics: { ...data },
          });

          const isFinished = status === 'completed' || status === 'failed' || status === 'cancelled';
          if (isFinished) {
            socket.close();
            if (status === 'completed') {
              addSchedulingLog('[SUCCESS] Job completed successfully!');
              toast.success('Scheduling Complete!', {
                description: 'The timetable has been generated.',
                action: {
                  label: 'View Timetable',
                  onClick: async () => {
                    await initializeApp();
                    setCurrentPage('timetable');
                  },
                },
              });
            } else {
              const errorMessage = data.message || 'An error occurred.';
              addSchedulingLog(`[ERROR] Job ${status}: ${errorMessage}`);
              toast.error(`Scheduling ${status}`, {
                description: errorMessage,
              });
            }
          }
        } else if (data.status === 'connected') {
            addSchedulingLog(`[INFO] ${data.message}`);
        } else {
            addSchedulingLog(`[LOG] ${JSON.stringify(data)}`);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        addSchedulingLog('[ERROR] Received an unreadable message from the server.');
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      addSchedulingLog('[ERROR] A connection error occurred.');
      toast.error('WebSocket Connection Error', {
        description: 'Could not maintain a live connection to the job monitor.',
      });
      setSchedulingStatus({ isRunning: false, phase: 'error' });
    };

    socket.onclose = (event) => {
      addSchedulingLog(`[INFO] Connection closed. Code: ${event.code}.`);
      socketRef.current = null;
      const finalStatus = useAppStore.getState().schedulingStatus.phase;
      if (!['completed', 'failed', 'cancelled'].includes(finalStatus)) {
        setSchedulingStatus({ isRunning: false, phase: 'disconnected' });
      }
    };

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [jobId, setSchedulingStatus, addSchedulingLog, clearSchedulingLogs, setCurrentPage, initializeApp]);
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
                const relatedExam = schedule.find((e: { id: any; }) => e.id === report.exam_id);
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
}, [fetchData, JSON.stringify(initialFilters)]);


return { isLoading, error, refetch: fetchData };
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

// --- SESSION SETUP HOOKS ---
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
            // --- FIX START ---
            // The API response is the summary object itself, which is correct.
            // However, the `api.getSessionSummary` returns an Axios response object.
            // The actual data from the API is in the `data` property of the response.
            // The original code was already correct, but this explicit check ensures robustness.
            if (response.data) {
              setData(response.data);
            } else {
              // Handle cases where the response might be unexpectedly empty
              throw new Error("Received an empty summary response from the server.");
            }
            // --- FIX END ---
        } catch (err: any) {
            const detail = err.response?.data?.detail || 'Failed to fetch session summary.';
            toast.error(detail);
            setError(new Error(detail));
        } finally {
            setIsLoading(false);
        }
    }, [sessionId]);

    return { data, isLoading, error, refetch: fetchSummary };
}

export function useProcessStagedData() {
    const [isPending, setIsPending] = useState(false);
    const mutateAsync = async ({ sessionId }: { sessionId: string }) => {
        try {
            setIsPending(true);
            const response = await api.processStagedData(sessionId);
            return response.data;
        } catch (error: any) {
            const detail = error.response?.data?.detail || 'Failed to process session data.';
            toast.error(`Processing Failed: ${detail}`);
            throw new Error(detail);
        } finally {
            setIsPending(false);
        }
    };
    return { mutateAsync, isPending };
}

export function useStagedData(sessionId: string, entityType: string) {
    const [data, setData] = useState<any[] | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);
  
    const fetchData = useCallback(async () => {
      if (!sessionId || !entityType) {
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.getStagedData(sessionId, entityType);
        setData(response.data.data || []);
      } catch (err: any) {
        const detail = err.response?.data?.detail || `Failed to fetch staged data for ${entityType}.`;
        setError(new Error(detail));
      } finally {
        setIsLoading(false);
      }
    }, [sessionId, entityType]);
  
    useEffect(() => {
      fetchData();
    }, [fetchData]);
  
    const updateRecord = async (recordPk: string, payload: any) => {
        try {
            const response = await api.updateStagedRecord(entityType, recordPk, payload);
            if (response.data.success) {
                setData(currentData => 
                    (currentData || []).map(row => 
                        row.code === recordPk ? { ...row, ...payload } : row // Assuming 'code' is the PK for simplicity
                    )
                );
                toast.success("Record updated successfully.");
                return true;
            }
        } catch (error: any) {
            const detail = error.response?.data?.detail || "Failed to update record.";
            toast.error(detail);
            return false;
        }
    };

    return { data, isLoading, error, refetch: fetchData, updateRecord };
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
      
      if (response.data && response.data.logs) {
        setHistory(response.data.logs);
        const totalCount = response.data.total_count || 0;
        setPagination({
          total: totalCount,
          pages: Math.ceil(totalCount / ps) || 1,
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