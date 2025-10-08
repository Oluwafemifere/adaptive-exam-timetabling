// frontend/src/store/index.ts
import { create } from 'zustand';
import {
  AppState,
  TimetableResponseData,
  RenderableExam,
  TimetableAssignmentData,
  Conflict,
  StaffSchedules,
  ConflictReport,
  StudentExam,
  ChangeRequest,
  Notification,
  HistoryEntry,
  AllReportsResponse,
  DashboardKpis,
  ConflictHotspot,
  TopBottleneck,
  SystemConfiguration,
  Constraint,
  JobStatus,
  SystemConfigurationDetails,
} from './types';
import { api, SystemConfigRulesUpdate } from '../services/api';
import { toast } from 'sonner';

export const useAppStore = create<AppState>()((set, get) => ({
  // State
  currentPage: 'dashboard',
  isAuthenticated: !!localStorage.getItem('authToken'),
  user: null,
  exams: [],
  conflicts: [],
  activeSessionId: null,
  currentJobId: null,
  studentExams: [],
  instructorSchedule: [],
  invigilatorSchedule: [],
  conflictReports: [],
  changeRequests: [],
  notifications: [],
  history: [],
  systemStatus: {
    constraintEngine: 'idle',
    autoResolution: false,
    dataSyncProgress: 0,
  },
  schedulingStatus: {
    isRunning: false,
    phase: 'idle',
    progress: 0,
    jobId: null,
    canPause: false,
    canResume: false,
    canCancel: false,
    metrics: {},
  },
  uploadStatus: {
    isUploading: false,
    progress: 0,
  },
  settings: {
    theme: 'light',
    constraintWeights: {},
    notifications: { emailNotifications: true, conflictAlerts: true, schedulingUpdates: true },
  },
  reportSummaryCounts: null,
  allConflictReports: [],
  allChangeRequests: [],

  // Dashboard
  dashboardKpis: null,
  conflictHotspots: [],
  topBottlenecks: [],
  recentActivity: [],
  configurations: [],
  activeConfigurationId: null,
  activeConfigurationDetails: null,

  // Actions
  setCurrentPage: (page: string) => set({ currentPage: page }),
  setAuthenticated: (isAuth: boolean, user: any = null) => set({ isAuthenticated: isAuth, user }),

  // Configuration related
  setConfigurations: (configs: SystemConfiguration[]) => set({ configurations: configs }),

  fetchAndSetActiveConfiguration: async (configId: string) => {
    try {
      set({ activeConfigurationId: configId, activeConfigurationDetails: null });
      const response = await api.getConfigurationDetails(configId);
      const details = response.data as any; // Treat as any to inspect it first

      // --- START OF FIX ---
      // The API is inconsistent, sometimes sending 'constraints', but the app uses 'rules'.
      // This normalizes the data structure before setting it in the store.
      if (details && details.constraints && !details.rules) {
        details.rules = details.constraints;
        delete details.constraints;
      }
      // --- END OF FIX ---
      set({ activeConfigurationDetails: details as SystemConfigurationDetails });
    } catch (error) {
      toast.error('Failed to load configuration details.');
      set({ activeConfigurationDetails: null });
    }
  },

  updateAndSaveActiveConfiguration: async (payload: { constraints: Constraint[] }) => {
    const activeId = get().activeConfigurationId;
    if (!activeId) {
      toast.error("No active configuration selected.");
      return;
    }
    try {
      // Transform the frontend state shape back to the payload the API expects for an update
      const apiPayload: SystemConfigRulesUpdate = {
        constraints: payload.constraints.map(c => ({
          rule_id: c.rule_id, 
          is_enabled: c.is_enabled,
          weight: c.weight,
          parameter_overrides: c.parameters || {},
        })),
      };

      await api.updateConfigurationRules(activeId, apiPayload);
      toast.success("Configuration saved successfully!");
      // Refetch to get the source of truth from the server
      await get().fetchAndSetActiveConfiguration(activeId); 
    } catch (error) {
      toast.error("Failed to save configuration.");
      // On failure, it's good practice to refetch to discard user's broken changes
      await get().fetchAndSetActiveConfiguration(activeId); 
    }
  },

  addHistoryEntry: (entry: Omit<HistoryEntry, 'id' | 'created_at'>) => {
    const newEntry: HistoryEntry = {
      ...entry,
      id: `hist-${Date.now()}`,
      created_at: new Date().toISOString(),
    };
    set((state) => ({ history: [newEntry, ...state.history] }));
  },

  setHistory: (history: HistoryEntry[]) => set({ history }),

  setTimetable: (data: TimetableResponseData) => {
    const timetableData = data?.timetable;
    const jobId = data?.job_id;

    if (!timetableData?.solution?.assignments) {
      console.error("[Store] Incomplete timetable data received. Clearing exams.", { receivedData: data });
      set({ exams: [], conflicts: [], currentJobId: jobId || null });
      return;
    }

    const { assignments } = timetableData.solution;

    const mappedExams: RenderableExam[] = Object.values(assignments)
      .map((assignment: TimetableAssignmentData): RenderableExam | null => {
        const room = assignment.rooms?.[0];
        if (!assignment.date || !assignment.start_time || !assignment.end_time || typeof assignment.duration_minutes !== 'number' || !room) {
          return null;
        }

        return {
          id: assignment.exam_id,
          examId: assignment.exam_id,
          courseCode: assignment.course_code || 'N/A',
          courseName: assignment.course_title || 'Unknown Course',
          date: assignment.date,
          startTime: assignment.start_time,
          endTime: assignment.end_time,
          duration: assignment.duration_minutes,
          expectedStudents: assignment.student_count || 0,
          room: room.code || 'N/A',
          roomCapacity: room.exam_capacity || 0,
          building: room.building_name || 'N/A',
          invigilator: (assignment.invigilators || []).map(i => i.name).join(', ') || 'N/A',
          departments: assignment.department_name ? [assignment.department_name.replace('Dept of ', '')] : ['Unknown'],
          facultyName: assignment.faculty_name || 'Unknown Faculty',
          instructor: assignment.instructor_name || 'N/A',
          examType: assignment.is_practical ? 'Practical' : 'Theory',
          conflicts: (assignment.conflicts || []).map((c: any) => c.message) || [],
          level: 'undergraduate',
          semester: 'Fall 2025',
          academicYear: '2025-2026',
        };
      })
      .filter((exam): exam is RenderableExam => exam !== null);

    set({ exams: mappedExams, currentJobId: jobId });
  },

  setConflicts: (conflicts: Conflict[]) => set({ conflicts }),
  setStudentExams: (exams: StudentExam[]) => set({ studentExams: exams }),
  setConflictReports: (reports: ConflictReport[]) => set({ conflictReports: reports }),
  setStaffSchedules: (schedules: StaffSchedules) => set({
    instructorSchedule: schedules.instructorSchedule,
    invigilatorSchedule: schedules.invigilatorSchedule,
    changeRequests: schedules.changeRequests,
  }),

  setSystemStatus: (status) => set((state) => ({ systemStatus: { ...state.systemStatus, ...status } })),
  setSchedulingStatus: (status) => set((state) => ({ schedulingStatus: { ...state.schedulingStatus, ...status } })),
  setUploadStatus: (status) => set((state) => ({ uploadStatus: { ...state.uploadStatus, ...status } })),
  updateSettings: (newSettings) => set((state) => ({ settings: { ...state.settings, ...newSettings } })),

  // Conflict reports and change requests
  addConflictReport: (report) => {
    const newReport: ConflictReport = {
      ...report,
      id: `cr-${Date.now()}`,
      status: 'pending', // Corrected from 'open'
      submittedAt: new Date().toISOString(),
    };
    set((state) => ({
      conflictReports: [newReport, ...state.conflictReports],
    }));
    toast.success('Conflict report submitted.');
  },

  addChangeRequest: (request) => {
    const newRequest: ChangeRequest = {
      ...request,
      id: `crq-${Date.now()}`,
      status: 'pending',
      submittedAt: new Date().toISOString(),
    };
    set((state) => ({
      changeRequests: [newRequest, ...state.changeRequests],
    }));
    toast.success('Change request submitted.');
  },

  updateConflictReportStatus: (id, status) => {
    set((state) => ({
      conflictReports: state.conflictReports.map(r => r.id === id ? { ...r, status } : r),
      allConflictReports: state.allConflictReports.map(r => r.id === id ? { ...r, status } : r),
    }));
  },

  updateChangeRequestStatus: (id, status) => {
    set((state) => ({
      changeRequests: state.changeRequests.map(r => r.id === id ? { ...r, status } : r),
      allChangeRequests: state.allChangeRequests.map(r => r.id === id ? { ...r, status } : r),
    }));
  },

  addNotification: (notification) => set((state) => ({
    notifications: [{ ...notification, id: `notif-${Date.now()}`, createdAt: new Date().toISOString(), isRead: false }, ...state.notifications]
  })),

  markNotificationAsRead: (id) => set((state) => ({ notifications: state.notifications.map(n => n.id === id ? { ...n, isRead: true } : n) })),
  clearNotifications: () => set({ notifications: [] }),

  setAllReports: (data: AllReportsResponse) => set({
    reportSummaryCounts: data.summary_counts,
    allConflictReports: data.conflict_reports,
    allChangeRequests: data.assignment_change_requests,
  }),

  // Dashboard actions
  setDashboardKpis: (kpis) => set({ dashboardKpis: kpis }),
  setConflictHotspots: (hotspots) => set({ conflictHotspots: hotspots }),
  setTopBottlenecks: (bottlenecks) => set({ topBottlenecks: bottlenecks }),
  setRecentActivity: (activity) => set({ recentActivity: activity }),

  // Scheduling controls
  startSchedulingJob: async (configuration_id) => {
    set((state) => ({
      schedulingStatus: { ...state.schedulingStatus, isRunning: true, phase: 'initiating', progress: 0 }
    }));
    try {
      const activeSessionId = get().activeSessionId;
      if (!activeSessionId) {
        throw new Error("No active session is selected.");
      }

      const response = await api.startScheduling({
        session_id: activeSessionId,
        configuration_id,
      });

      const { job_id } = response.data;
      set((state) => ({
        schedulingStatus: { ...state.schedulingStatus, jobId: job_id, phase: 'queued', isRunning: true }
      }));
      toast.success("Scheduling job has been started.");
      get().pollJobStatus(job_id);
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || "Failed to start scheduling job.";
      toast.error(errorMessage);
      set((state) => ({
        schedulingStatus: { ...state.schedulingStatus, isRunning: false, phase: 'failed' }
      }));
    }
  },

  cancelSchedulingJob: async (jobId) => {
    const { pollJobStatus } = get();
    if (typeof (pollJobStatus as any).stop === 'function') {
      (pollJobStatus as any).stop(); // Stop polling if the poller supports it
    }
    try {
      await api.cancelScheduling(jobId); // Corrected API call
      set((state) => ({
        schedulingStatus: { ...state.schedulingStatus, isRunning: false, phase: 'cancelled', jobId: null }
      }));
      toast.success('Scheduling job cancelled.');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || 'Failed to cancel job.');
    }
  },

  pollJobStatus: (() => {
    let intervalId: number | null = null;

    const poller = (jobId: string) => {
      if (intervalId) clearInterval(intervalId);

      intervalId = window.setInterval(async () => {
        try {
          const statusResp = await api.getJobStatus(jobId);
          const status: JobStatus = statusResp.data;

          set((state) => ({
            schedulingStatus: {
              ...state.schedulingStatus,
              phase: status.solver_phase || status.status,
              progress: status.progress_percentage || state.schedulingStatus.progress,
              metrics: { ...status },
            }
          }));

          const isFinished = status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled';
          if (isFinished) {
            if (intervalId) clearInterval(intervalId);
            intervalId = null;

            set((state) => ({ schedulingStatus: { ...state.schedulingStatus, isRunning: false, jobId: null, phase: status.status } }));

            if (status.status === 'completed') {
              toast.success('Scheduling job completed! Reloading timetable...');
              try {
                // Fetch the new timetable instead of non-existent job results
                const timetableResponse = await api.getLatestTimetableForActiveSession();
                if (timetableResponse.data?.success && timetableResponse.data.data) {
                  get().setTimetable(timetableResponse.data.data);
                  const conflicts = timetableResponse.data.data.timetable?.solution?.conflicts || [];
                  get().setConflicts(conflicts as Conflict[]);
                  toast.success('Timetable loaded successfully.');
                }
              } catch (err) {
                toast.error('Failed to reload the timetable after job completion.');
              }
            } else {
              toast.error(`Scheduling job ${status.status}: ${status.error_message || 'No details'}`);
            }
          }
        } catch (err) {
          console.error('Error polling job status', err);
          // Optional: Stop polling after a few failed attempts
        }
      }, 3000);
    };

    (poller as any).stop = () => {
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
    };
    
    return poller;
  })(),

  // Initialization
  initializeApp: async () => {
    const token = localStorage.getItem('authToken');
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    try {
      const userResponse = await api.getCurrentUser();
      const userData = userResponse.data;
      const user = {
        id: userData.id,
        name: `${userData.first_name} ${userData.last_name}`,
        email: userData.email,
        role: userData.role,
      };
      set({ user, isAuthenticated: true });

      const sessionResponse = await api.getActiveSession();
      if (sessionResponse.data) {
        const sessionId = sessionResponse.data.id;
        set({ activeSessionId: sessionId });

        if (user && (user.role === 'admin' || user.role === 'superuser')) {
          const configsResponse = await api.getAllSystemConfigurations();
          const configs = configsResponse.data || [];
          set({ configurations: configs });

          const defaultConfig = configs.find((c: SystemConfiguration) => c.is_default);
          const initialConfigId = get().activeConfigurationId || (defaultConfig ? defaultConfig.id : configs[0]?.id);

          if (initialConfigId) {
            await get().fetchAndSetActiveConfiguration(initialConfigId);
          }
        }

        if (user.role === 'admin' || user.role === 'superuser') {
          try {
            const timetableResponse = await api.getLatestTimetableForActiveSession();
            if (timetableResponse.data?.success && timetableResponse.data.data) {
              get().setTimetable(timetableResponse.data.data);
              const conflicts = timetableResponse.data.data.timetable?.solution?.conflicts || [];
              get().setConflicts(conflicts as Conflict[]);
            } else {
              set({ exams: [], conflicts: [] });
            }
          } catch (error: any) {
            if (error.response && error.response.status === 404) {
              set({ exams: [], conflicts: [] });
            } else {
              throw error;
            }
          }
        }
      } else {
        toast.warning('No active academic session found. Please set one up.');
        set({ activeSessionId: null });
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || (error instanceof Error ? error.message : 'An unknown error occurred.');
      toast.error(`Initialization failed: ${errorMessage}`);
      get().setAuthenticated(false, null);
      localStorage.removeItem('authToken');
    }
  },
}));