import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../services/api';
import { useAppStore } from '../store';
import { toast } from 'sonner';
import { JobStatus, Conflict, StudentExam, StaffAssignment, HistoryEntry, PaginatedUserResponse,
UserManagementRecord } from '../store/types';
import { SessionSetupCreate, SessionSetupSummary } from '../pages/SessionSetup';
import { config } from '../config';
// import { SessionSetupCreate, SessionSetupSummary } from '../pages/SessionManagement'; 
import { StagingRecord } from '../store/types';
export function useDashboardData() {
const {
activeSessionId,
setDashboardKpis,
setConflictHotspots,
setTopBottlenecks,
setRecentActivity,
setHistory
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
// --- UPDATED: Fetch dashboard and activity data concurrently ---
const [analyticsRes, activityRes] = await Promise.all([
  api.getDashboardAnalytics(activeSessionId),
  api.getAuditHistory()
]);

// --- UPDATED: Populate store from single analytics response ---
if (analyticsRes.data) {
  setDashboardKpis(analyticsRes.data.kpis);
  setConflictHotspots(analyticsRes.data.conflict_hotspots);
  setTopBottlenecks(analyticsRes.data.top_bottlenecks);
}

if (activityRes.data?.logs) {
  const mappedLogs: HistoryEntry[] = activityRes.data.logs.map((log: any) => ({
      id: log.id,
      action: log.action,
      entityType: log.entity_type,
      entityId: log.entity_id,
      userName: log.user || 'System',
      timestamp: log.created_at,
      details: log.new_values || {},
      changes: (log.old_values || log.new_values) ? { before: log.old_values || {}, after: log.new_values || {} } : undefined,
  }));
  setRecentActivity(mappedLogs);
  setHistory(mappedLogs);
}

setError(null);

} catch (err) {
const error = err instanceof Error ? err : new Error('Failed to fetch dashboard data');
setError(error);
toast.error(error.message);
} finally {
setIsLoading(false);
}

}, [activeSessionId, setDashboardKpis, setConflictHotspots, setTopBottlenecks, setRecentActivity, setHistory]);

useEffect(() => {
fetchData();
// Optional: set an interval to refresh dashboard data periodically
const interval = setInterval(fetchData, 60000); // every 60 seconds
return () => clearInterval(interval);
}, [fetchData]);

return { isLoading, error, refetch: fetchData };
}
export function useSessionManager(sessionId: string | null) {
  const [dataGraph, setDataGraph] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!sessionId) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.getFullSessionDataGraph(sessionId);
      setDataGraph(response.data || {});
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to fetch session data graph.';
      setError(new Error(detail));
      toast.error(detail);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleMutation = async (
    action: Promise<any>,
    successMessage: string,
    errorMessage: string
  ) => {
    try {
      await action;
      toast.success(successMessage);
      await fetchData(); // Refetch data on success
      return true;
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || errorMessage;
      toast.error(detail);
      return false;
    }
  };

  const createEntity = (entityType: 'course' | 'building' | 'room', payload: any) => {
    if (!sessionId) return Promise.resolve(false);
    let action;
    switch (entityType) {
      case 'course': action = api.createCourseInSession(sessionId, payload); break;
      case 'building': action = api.createBuildingInSession(sessionId, payload); break;
      case 'room': action = api.createRoomInSession(sessionId, payload); break;
      default: return Promise.resolve(false);
    }
    return handleMutation(action, `${entityType} created successfully.`, `Failed to create ${entityType}.`);
  };

  const updateEntity = (entityType: 'course' | 'building' | 'room', entityId: string, payload: any) => {
    if (!sessionId) return Promise.resolve(false);
    let action;
    switch (entityType) {
      case 'course': action = api.updateCourseInSession(sessionId, entityId, payload); break;
      case 'building': action = api.updateBuildingInSession(sessionId, entityId, payload); break;
      case 'room': action = api.updateRoomInSession(sessionId, entityId, payload); break;
      default: return Promise.resolve(false);
    }
    return handleMutation(action, `${entityType} updated successfully.`, `Failed to update ${entityType}.`);
  };

  const deleteEntity = (entityType: 'course' | 'building' | 'room', entityId: string) => {
    if (!sessionId) return Promise.resolve(false);
    let action;
    switch (entityType) {
      case 'course': action = api.deleteCourseInSession(sessionId, entityId); break;
      case 'building': action = api.deleteBuildingInSession(sessionId, entityId); break;
      case 'room': action = api.deleteRoomInSession(sessionId, entityId); break;
      default: return Promise.resolve(false);
    }
    return handleMutation(action, `${entityType} deleted successfully.`, `Failed to delete ${entityType}.`);
  };

  return { dataGraph, isLoading, error, refetch: fetchData, createEntity, updateEntity, deleteEntity };
}
export function useUserManagementData() {
const { users, setUsers } = useAppStore(state => ({
users: state.users,
setUsers: state.setUsers,
}));

const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [pagination, setPagination] = useState({ total_items: 0, total_pages: 1, page: 1, page_size: 10 });

  const fetchData = useCallback(async (filters: { page?: number, page_size?: number, search_term?: string, role_filter?: string, status_filter?: string }) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.getUserManagementData(filters);
      const { items, ...paginationData } = response.data;
      setUsers(items);
      setPagination(paginationData);
    } catch (err) {
      const fetchError = err instanceof Error ? err : new Error('Failed to fetch user data');
      setError(fetchError);
      toast.error(fetchError.message);
    } finally {
      setIsLoading(false);
    }
  }, [setUsers]);

  return { users, pagination, isLoading, error, refetch: fetchData };

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
              instructor: exam.instructor_name || 'N/A',
              invigilator: (exam.invigilators || []).map((i: { name: string; }) => i.name).join(', ') || 'N/A',
              expectedStudents: exam.student_count || 0,
              roomCapacity: exam.rooms?.[0]?.exam_capacity || 0,
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
              expectedStudents: exam.student_count || 0,
              roomCapacity: exam.rooms?.[0]?.exam_capacity || 0,
              instructor: exam.instructor_name || 'N/A',
              invigilator: (exam.invigilators || []).map((i: { name: string; }) => i.name).join(', ') || 'N/A',
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

export function useSeedingStatus(sessionId: string | null) {
  const [data, setData] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!sessionId) return;
    setError(null);
    try {
      // The API endpoint for seeding status already exists, we just need to call it.
      const response = await api.getSeedingStatus(sessionId);
      if (response.data.success) {
        setData(response.data.data);
      } else {
         throw new Error(response.data.message || 'Failed to fetch seeding status.');
      }
    } catch (err: any) {
      // Don't show a toast on every poll failure, just log it.
      console.error("Polling for seeding status failed:", err.message);
      setError(err);
    }
  }, [sessionId]);

  return { data, isLoading, error, refetch: fetchStatus };
}
export function useFileUpload() {
  const [isPending, setIsPending] = useState(false);

  const mutateAsync = async ({ files, academicSessionId }: { files: File[]; academicSessionId: string }) => {
      setIsPending(true);
      try {
          const response = await api.uploadFilesBatch(files, academicSessionId);
          const resultData = response.data.data;
          
          const successCount = resultData.dispatched_tasks.length;
          const failedCount = resultData.failed_files.length;
          
          if (failedCount > 0) {
              toast.warning(`${successCount} files dispatched, ${failedCount} failed.`, {
                  description: "Check the upload list for details on failed files."
              });
          } else {
              toast.success("All files dispatched for processing!");
          }
          
          return resultData;
      } catch (error: any) {
          const detail = error.response?.data?.detail || 'Batch upload failed.';
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
          if (response.data && Object.keys(response.data).length > 0) {
            setData(response.data);
          } else {
            console.log("Summary data not ready yet, will refetch.");
          }
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

export function useAllStagedData(sessionId: string | null) {
const [data, setData] = useState<any | null>(null);
const [isLoading, setIsLoading] = useState(true);
const [error, setError] = useState<Error | null>(null);

const fetchData = useCallback(async () => {
if (!sessionId) {
setIsLoading(false);
return;
}
setIsLoading(true);
setError(null);
try {
const response = await api.getAllStagedData(sessionId);
setData(response.data.data || {});
} catch (err: any) {
const detail = err.response?.data?.detail || 'Failed to fetch staged data.';
setError(new Error(detail));
toast.error(detail);
} finally {
setIsLoading(false);
}
}, [sessionId]);

useEffect(() => {
fetchData();
}, [fetchData]);

return { data, isLoading, error, refetch: fetchData };
}

// This hook is now primarily for providing mutation functions
export function useStagedData(sessionId: string, entityType: string) {
const [isLoading, setIsLoading] = useState(false); // Only for mutation operations

// A generic refetch function to be passed from the parent component
const [refetcher, setRefetcher] = useState<() => Promise<void>>();
const setRefetch = (refetchFn: () => Promise<void>) => setRefetcher(() => refetchFn);

// --- FIX: Correctly generates singular, camelCased API function names ---
const getApiMethodName = (action: 'add' | 'update' | 'delete', entityType: string): string => {
    let singularBase = entityType;
    if (entityType === 'faculties') {
        singularBase = 'faculty';
    } else if (entityType.endsWith('s')) {
        // Handles 'courses' -> 'course', 'departments' -> 'department', etc.
        singularBase = entityType.slice(0, -1);
    }
    // 'staff' is already singular, no change needed.

    // Now camelCase it
    const camelCaseBase = singularBase.replace(/_([a-z])/g, g => g[1].toUpperCase());
    const capitalizedBase = camelCaseBase.charAt(0).toUpperCase() + camelCaseBase.slice(1);
    
    // The backend uses 'addStaged...', 'updateStaged...', 'deleteStaged...'
    return `${action}Staged${capitalizedBase}`;
};


// ADD a new record
const addRecord = async (payload: any): Promise<boolean> => {
setIsLoading(true);
try {
      const functionName = getApiMethodName('add', entityType);
      const apiFunction = (api as any)[functionName];
      if (!apiFunction) throw new Error(`API function '${functionName}' for adding ${entityType} not found.`);

      await apiFunction(sessionId, payload);
      toast.success("Record added successfully.");
      if (refetcher) await refetcher();
      return true;
  } catch (error: any) {
      const detail = error.response?.data?.detail || `Failed to add record: ${error.message}`;
      toast.error(detail);
      return false;
  } finally {
      setIsLoading(false);
  }

};

// UPDATE an existing record
const updateRecord = async (pks: (string|number)[], payload: any): Promise<boolean> => {
setIsLoading(true);
try {
      const functionName = getApiMethodName('update', entityType);
      const apiFunction = (api as any)[functionName];
      if (!apiFunction) throw new Error(`API function '${functionName}' for updating ${entityType} not found.`);

      await apiFunction(sessionId, ...pks, payload);
      toast.success("Record updated successfully.");
      if (refetcher) await refetcher();
      return true;
  } catch (error: any) {
      const detail = error.response?.data?.detail || `Failed to update record: ${error.message}`;
      toast.error(detail);
      return false;
  } finally {
      setIsLoading(false);
  }

};

// DELETE a record
const deleteRecord = async (pks: (string|number)[]): Promise<boolean> => {
setIsLoading(true);
try {
      const functionName = getApiMethodName('delete', entityType);
      const apiFunction = (api as any)[functionName];
      if (!apiFunction) throw new Error(`API function '${functionName}' for deleting ${entityType} not found.`);

      await apiFunction(sessionId, ...pks);
      toast.success("Record deleted successfully.");
      if (refetcher) await refetcher();
      return true;
  } catch (error: any) {
      const detail = error.response?.data?.detail || `Failed to delete record: ${error.message}`;
      toast.error(detail);
      return false;
  } finally {
      setIsLoading(false);
  }

};

return { isLoading, addRecord, updateRecord, deleteRecord, setRefetch };
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
    
    if (response.data?.logs) {
      const mappedLogs: HistoryEntry[] = response.data.logs.map((log: any) => ({
        id: log.id,
        action: log.action,
        entityType: log.entity_type,
        entityId: log.entity_id,
        userName: log.user || 'System',
        timestamp: log.created_at,
        details: log.new_values || {},
        changes: (log.old_values || log.new_values) ? {
          before: log.old_values || {}, after: log.new_values || {},
        } : undefined,
      }));
      setHistory(mappedLogs);
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

export function useJobHistoryData() {
  const { activeSessionId, sessionJobs, fetchSessionJobs } = useAppStore(state => ({
    activeSessionId: state.activeSessionId,
    sessionJobs: state.sessionJobs,
    fetchSessionJobs: state.fetchSessionJobs,
  }));

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    if (!activeSessionId) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await fetchSessionJobs(activeSessionId);
    } catch (err) {
      const fetchError = err instanceof Error ? err : new Error('Failed to fetch job history');
      setError(fetchError);
    } finally {
      setIsLoading(false);
    }
  }, [activeSessionId, fetchSessionJobs]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { jobs: sessionJobs, isLoading, error, refetch: fetchData };
}