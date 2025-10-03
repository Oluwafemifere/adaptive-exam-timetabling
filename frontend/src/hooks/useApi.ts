// frontend/src/hooks/useApi.ts
import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { useAppStore } from '../store';
import { toast } from 'sonner';
import { JobStatus, DashboardKPIs, Conflict, StudentExam, StaffAssignment } from '../store/types';

export function useKPIData() {
  const { activeSessionId } = useAppStore();
  const [data, setData] = useState<DashboardKPIs | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!activeSessionId) {
      setIsLoading(false);
      return;
    };

    const fetchData = async () => {
      try {
        const response = await api.getDashboardKpis(activeSessionId);
        setData(response.data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch KPI data'));
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [activeSessionId]);

  return { data, isLoading, error };
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

  const mutateAsync = async ({ formData, entityType }: { formData: FormData; entityType: string }) => {
    try {
      setIsPending(true);
      const response = await api.uploadFile(formData, entityType);
      toast.success('File uploaded successfully');
      return response.data;
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Upload failed');
      toast.error(`Upload failed: ${err.message}`);
      throw err;
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
        // Pass the entire data object which contains the nested 'timetable' property
        setTimetable(apiPayload.data);
        
        // Correctly path to conflicts array inside the nested timetable object
        const conflicts = apiPayload.data.timetable?.solution?.conflicts || [];
        setConflicts(conflicts as Conflict[]);
      } else {
        const errorMessage = apiPayload.message || 'No successful timetable found.';
        setTimetable({} as any); // Clear timetable on failure
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
                const portalData = response.data.data;
                // Map API response to the StudentExam type expected by the store
                const schedule = (portalData.schedule?.schedule || []).map((exam: any, index: number) => ({
                    id: `${exam.course_code}-${exam.exam_date}-${index}`, // Create a stable ID
                    courseCode: exam.course_code,
                    courseName: exam.course_title,
                    date: exam.exam_date,
                    startTime: exam.start_time,
                    endTime: exam.end_time,
                    room: exam.room_codes?.[0] || 'N/A',
                    building: exam.building_name || 'N/A',
                    duration: exam.duration_minutes,
                }));
                setStudentExams(schedule);
                setConflictReports(portalData.conflictReports || []);
            } else {
                throw new Error(response.data.message || 'Failed to fetch portal data');
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
                const portalData = response.data.data;
                const mapToAssignment = (exam: any, role: StaffAssignment['role']): StaffAssignment => ({
                    id: `${exam.course_code}-${exam.exam_date}-${role}`, // Create a stable ID
                    examId: `${exam.course_code}-${exam.exam_date}`,
                    courseCode: exam.course_code,
                    courseName: exam.course_title,
                    date: exam.exam_date,
                    startTime: exam.start_time,
                    endTime: exam.end_time,
                    room: exam.room_codes?.[0] || 'N/A',
                    building: exam.building_name,
                    role,
                    status: 'assigned', // Default status
                });

                const instructorSchedule = (portalData.schedule?.instructor?.schedule || []).map((exam: any) => mapToAssignment(exam, 'instructor'));
                const invigilatorSchedule = (portalData.schedule?.invigilation?.schedule || []).map((exam: any) => mapToAssignment(exam, 'invigilator'));

                setStaffSchedules({
                    instructorSchedule,
                    invigilatorSchedule,
                    changeRequests: portalData.changeRequests || [],
                });
            } else {
                throw new Error(response.data.message || 'Failed to fetch portal data');
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