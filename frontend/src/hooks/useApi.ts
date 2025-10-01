import { useState, useEffect, useRef } from 'react';
import { api, MockWebSocket, KPIData, AcademicSession } from '../services/api';
import { useAppStore } from '../store';
import { toast } from 'sonner';

// KPI Data Hook
export function useKPIData() {
  const [data, setData] = useState<KPIData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const response = await api.getKPIData();
        setData(response.data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch KPI data'));
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    // Refetch every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  return { data, isLoading, error };
}

// Academic Sessions Hook
export function useAcademicSessions() {
  const [data, setData] = useState<AcademicSession[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const response = await api.getAcademicSessions();
        setData(response.data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch academic sessions'));
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  return { data, isLoading, error };
}

// File Upload Hook
export function useFileUpload() {
  const [isPending, setIsPending] = useState(false);

  const mutateAsync = async ({ formData, entityType }: { formData: FormData; entityType: string }) => {
    try {
      setIsPending(true);
      const response = await api.uploadFile(formData, entityType);
      toast.success(response.data.message);
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

// Scheduling Hooks
export function useScheduling() {
  const { setSchedulingStatus } = useAppStore();
  const [isPending, setIsPending] = useState(false);

  const startScheduling = {
    mutate: async (request: {
      session_id: string;
      start_date: string;
      end_date: string;
      options: {
        timeLimit: number;
        populationSize: number;
        constraints: Record<string, number>;
      };
    }) => {
      try {
        setIsPending(true);
        const response = await api.startScheduling(request);
        setSchedulingStatus({
          isRunning: true,
          jobId: response.data.job_id,
          phase: 'cp-sat',
          progress: 0,
        });
        toast.success('Scheduling job started successfully!');
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Failed to start scheduling');
        toast.error(`Failed to start scheduling: ${err.message}`);
      } finally {
        setIsPending(false);
      }
    },
    isPending
  };

  const cancelScheduling = {
    mutate: async (jobId: string) => {
      try {
        setIsPending(true);
        const response = await api.cancelScheduling(jobId);
        setSchedulingStatus({
          isRunning: false,
          phase: 'cancelled',
          jobId: null,
        });
        toast.success(response.data.message);
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Failed to cancel scheduling');
        toast.error(`Failed to cancel scheduling: ${err.message}`);
      } finally {
        setIsPending(false);
      }
    },
    isPending
  };

  return {
    startScheduling,
    cancelScheduling,
  };
}

// WebSocket Hook for Job Updates
export function useJobSocket(jobId: string | null) {
  const { setSchedulingStatus } = useAppStore();
  const socketRef = useRef<MockWebSocket | null>(null);

  useEffect(() => {
    if (!jobId) {
      return;
    }

    // Create mock WebSocket connection
    socketRef.current = new MockWebSocket(jobId);
    
    socketRef.current.on('job_update', (update) => {
      setSchedulingStatus({
        phase: update.phase,
        progress: update.progress,
        metrics: update.metrics,
        isRunning: !['completed', 'failed', 'cancelled'].includes(update.phase),
      });

      if (update.phase === 'completed') {
        toast.success('Scheduling completed successfully!');
      } else if (update.phase === 'failed') {
        toast.error('Scheduling failed: ' + (update.metrics.error_message || 'Unknown error'));
      }
    });

    socketRef.current.connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [jobId, setSchedulingStatus]);
}

// Reports Hook
export function useGenerateReport() {
  const [isPending, setIsPending] = useState(false);

  const mutateAsync = async ({ report_type, options }: { report_type: string; options: Record<string, any> }) => {
    try {
      setIsPending(true);
      const response = await api.generateReport(report_type, options);
      toast.success('Report generated successfully!');
      return response.data;
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to generate report');
      toast.error(`Failed to generate report: ${err.message}`);
      throw err;
    } finally {
      setIsPending(false);
    }
  };

  return { mutateAsync, isPending };
}