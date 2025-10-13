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
  JobStatus,
  SystemConfigurationDetails,
  SchedulingJob,
  SystemConfigSavePayload,
  RuleSettingRead,
  RuleSetting,
  UserManagementRecord,
} from './types';
import { api } from '../services/api';
import { toast } from 'sonner';

export const useAppStore = create<AppState>()((set, get) => ({
  // State
  currentPage: 'dashboard',
  isAuthenticated: !!localStorage.getItem('authToken'),
  user: null,
  exams: [],
  conflicts: [],
  activeSessionId: null,
  activeSessionName: null,
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
    logs: [],
  },
  users: [],

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
  sessionJobs: [],
  recentActivity: [],
  configurations: [],
  activeConfigurationId: null,
  activeConfigurationDetails: null,

  // Actions
  setUsers: (users) => set({ users }),
  addUser: (user) => set((state) => ({ users: [user, ...state.users] })),
  updateUserInList: (updatedUser) => set((state) => ({
    users: state.users.map(u => u.id === updatedUser.id ? updatedUser : u)
  })),
  removeUserFromList: (userId) => set((state) => ({
    users: state.users.filter(u => u.id !== userId)
  })),
  setCurrentPage: (page: string) => set({ currentPage: page }),
  setAuthenticated: (isAuth: boolean, user: any = null) => set({ isAuthenticated: isAuth, user }),

  // Configuration related
  setConfigurations: (configs: SystemConfiguration[]) => set({ configurations: configs }),

  fetchAndSetActiveConfiguration: async (configId: string) => {
    try {
      set({ activeConfigurationId: configId, activeConfigurationDetails: null });
      const response = await api.getSystemConfigurationDetails(configId);
      const details = response.data;

      if (!details || !details.rules) {
        throw new Error("Invalid configuration data received from server.");
      }
      
      set({ activeConfigurationDetails: details });
    } catch (error) {
      toast.error('Failed to load configuration details.');
      console.error(error);
      set({ activeConfigurationDetails: null });
    }
  },
  
  saveActiveConfiguration: async (updatedConfig: SystemConfigurationDetails) => {
    const activeId = get().activeConfigurationId;
    if (!activeId || !updatedConfig) {
      toast.error("No active configuration selected or data is missing.");
      return;
    }
    
    try {
      // **TARGETED CHANGE**: This payload transformation is crucial. It maps the
      // detailed `RuleSettingRead` objects to the leaner `RuleSetting` format
      // expected by the backend for saving.
      const payload: SystemConfigSavePayload = {
        id: updatedConfig.id,
        name: updatedConfig.name,
        description: updatedConfig.description,
        is_default: updatedConfig.is_default,
        solver_parameters: updatedConfig.solver_parameters,
        rules: updatedConfig.rules.map((rule: RuleSettingRead): RuleSetting => ({
          rule_id: rule.rule_id,
          is_enabled: rule.is_enabled,
          weight: rule.weight,
          parameters: rule.parameters,
        })),
      };

      await api.saveSystemConfiguration(payload);
      toast.success(`Configuration "${payload.name}" saved successfully!`);

      // Refresh state from the server to ensure UI is in sync with the database
      await get().fetchAndSetActiveConfiguration(activeId); 
      const listResponse = await api.getSystemConfigurationList();
      set({ configurations: listResponse.data || [] });

    } catch (error) {
      toast.error("Failed to save configuration.");
      console.error(error);
      // On failure, refresh the data to discard the user's failed changes
      await get().fetchAndSetActiveConfiguration(activeId); 
    }
  },

  addHistoryEntry: (entry: Omit<HistoryEntry, 'id' | 'timestamp'>) => {
    const newEntry: HistoryEntry = {
      ...entry,
      id: `hist-${Date.now()}`,
      timestamp: new Date().toISOString(),
      // Use the provided userName, but fall back to the current user's name or a default
      userName: entry.userName || get().user?.name || 'System',
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

  fetchSessionJobs: async (sessionId) => {
    try {
      const response = await api.getJobsList(sessionId);
      set({ sessionJobs: response.data || [] });
    } catch (error) {
      console.error("Failed to fetch session jobs:", error);
      toast.error("Could not load job history for this session.");
    }
  },

  fetchAndSetJobResult: async (jobId) => {
    try {
      const response = await api.getJobResult(jobId);
      if (response.data.success) {
        get().setTimetable({ timetable: response.data.data, job_id: jobId, session_id: get().activeSessionId! });
      }
    } catch (error) {
      toast.error("Failed to load data for the selected timetable version.");
    }
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
  setSchedulingStatus: (status) => set((state) => ({ 
    schedulingStatus: { 
      ...state.schedulingStatus, 
      ...status,
      logs: status.logs || state.schedulingStatus.logs,
    } 
  })),
  addSchedulingLog: (log: string) => set((state) => ({
    schedulingStatus: {
      ...state.schedulingStatus,
      logs: [...state.schedulingStatus.logs.slice(-100), log],
    }
  })),
  clearSchedulingLogs: () => set((state) => ({
    schedulingStatus: {
      ...state.schedulingStatus,
      logs: [],
    }
  })),
  setUploadStatus: (status) => set((state) => ({ uploadStatus: { ...state.uploadStatus, ...status } })),
  updateSettings: (newSettings) => set((state) => ({ settings: { ...state.settings, ...newSettings } })),

  addConflictReport: (report) => {
    const newReport: ConflictReport = {
      ...report,
      id: `cr-${Date.now()}`,
      status: 'pending',
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
    get().clearSchedulingLogs();
    set((state) => ({
      schedulingStatus: { ...state.schedulingStatus, isRunning: true, phase: 'initiating', progress: 0 }
    }));
    try {
      const activeSessionId = get().activeSessionId;
      if (!activeSessionId) {
        throw new Error("No active session is selected.");
      }

      const response = await api.startScheduling({
        configuration_id,
      });

      const { job_id, status } = response.data;
      set((state) => ({
        schedulingStatus: { ...state.schedulingStatus, jobId: job_id, phase: status, isRunning: true }
      }));
      toast.success("Scheduling job has been started.");
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || "Failed to start scheduling job.";
      toast.error(errorMessage);
      set((state) => ({
        schedulingStatus: { ...state.schedulingStatus, isRunning: false, phase: 'failed' }
      }));
    }
  },
  createNewConfiguration: async (payload: SystemConfigSavePayload) => {
    try {
      // The API service correctly uses POST for creation when ID is absent
      const response = await api.saveSystemConfiguration(payload);
      toast.success(`Configuration "${payload.name}" created successfully.`);
      
      // Refresh the list of configurations
      const listResponse = await api.getSystemConfigurationList();
      const newConfigs = listResponse.data || [];
      set({ configurations: newConfigs });

      // Find the new config's ID from the response and set it as active
      const newConfigId = response.data?.data?.configuration_id;
      if (newConfigId) {
        await get().fetchAndSetActiveConfiguration(newConfigId);
      }
      return true; // Indicate success
    } catch (error) {
      toast.error("Failed to create new configuration.");
      console.error(error);
      return false; // Indicate failure
    }
  },

  setDefaultConfiguration: async (configId: string) => {
    try {
      await api.setDefaultSystemConfiguration(configId);
      toast.success("Default configuration has been updated.");

      // Refresh the entire list to update the 'is_default' flag everywhere
      const listResponse = await api.getSystemConfigurationList();
      const configs = listResponse.data || [];
      set({ configurations: configs });

      // Also refresh the currently viewed details to update the badge
      await get().fetchAndSetActiveConfiguration(configId);

    } catch (error) {
      toast.error("Failed to set the default configuration.");
      console.error(error);
    }
  },
  cancelSchedulingJob: async (jobId) => {
    try {
      await api.cancelScheduling(jobId);
      set((state) => ({
        schedulingStatus: { ...state.schedulingStatus, isRunning: false, phase: 'cancelled', jobId: null }
      }));
      toast.success('Scheduling job cancelled.');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || error?.message || 'Failed to cancel job.');
    }
  },

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
        const sessionName = sessionResponse.data.name;
        set({ activeSessionId: sessionId, activeSessionName: sessionName });

        if (user && (user.role === 'admin' || user.role === 'superuser')) {
          const configsResponse = await api.getSystemConfigurationList();
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
        set({ activeSessionId: null, activeSessionName: null });
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || (error instanceof Error ? error.message : 'An unknown error occurred.');
      toast.error(`Initialization failed: ${errorMessage}`);
      get().setAuthenticated(false, null);
      localStorage.removeItem('authToken');
    }
  },
}));