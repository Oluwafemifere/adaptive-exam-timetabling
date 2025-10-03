// frontend/src/store/index.ts
import { create } from 'zustand';
import { AppState, TimetableResponseData, RenderableExam, JobStatus, TimetableAssignmentData, Conflict, StaffSchedules, ConflictReport, StudentExam, ChangeRequest, Notification, HistoryEntry } from './types';
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

  // Actions
  setCurrentPage: (page) => set({ currentPage: page }),
  setAuthenticated: (isAuth, user = null) => set({ isAuthenticated: isAuth, user }),

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
        if (!assignment.date || !assignment.start_time || typeof assignment.duration_minutes !== 'number' || !room) {
          return null;
        }
        
        const startDate = new Date(`1970-01-01T${assignment.start_time}Z`);
        const endDate = new Date(startDate.getTime() + (assignment.duration_minutes * 60 * 1000));
        
        const endHours = String(endDate.getUTCHours()).padStart(2, '0');
        const endMinutes = String(endDate.getUTCMinutes()).padStart(2, '0');
        const endSeconds = String(endDate.getUTCSeconds()).padStart(2, '0');
        const calculatedEndTime = `${endHours}:${endMinutes}:${endSeconds}`;

        return {
          id: assignment.exam_id,
          examId: assignment.exam_id,
          courseCode: assignment.course_code || 'N/A',
          courseName: assignment.course_title || 'Unknown Course',
          date: assignment.date,
          startTime: assignment.start_time,
          endTime: calculatedEndTime,
          duration: assignment.duration_minutes,
          expectedStudents: assignment.student_count || 0,
          room: room.code || 'N/A',
          roomCapacity: room.exam_capacity || 0,
          building: room.building_name || 'N/A',
          invigilator: assignment.invigilators.map(i => i.name).join(', ') || 'N/A',
          departments: assignment.department_name ? [assignment.department_name.replace('Dept of ', '')] : ['Unknown'],
          facultyName: assignment.faculty_name || 'Unknown Faculty',
          instructor: assignment.instructor_name || 'N/A',
          examType: assignment.is_practical ? 'Practical' : 'Theory',
          conflicts: assignment.conflicts?.map(c => c.message) || [],
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

  addConflictReport: (report: Omit<ConflictReport, 'id' | 'status' | 'submittedAt'>) => { /* ... */ },
  addChangeRequest: (request: Omit<ChangeRequest, 'id' | 'status' | 'submittedAt'>) => { /* ... */ },
  updateConflictReportStatus: (id: string, status: ConflictReport['status']) => { /* ... */ },
  updateChangeRequestStatus: (id: string, status: ChangeRequest['status']) => { /* ... */ },
  
  addNotification: (notification: Omit<Notification, 'id' | 'createdAt'>) => set((state) => ({ notifications: [{ ...notification, id: `notif-${Date.now()}`, createdAt: new Date().toISOString(), isRead: false }, ...state.notifications] })),
  markNotificationAsRead: (id: string) => set((state) => ({ notifications: state.notifications.map(n => n.id === id ? { ...n, isRead: true } : n) })),
  clearNotifications: () => set({ notifications: [] }),
  addHistoryEntry: (entry: Omit<HistoryEntry, 'id' | 'timestamp'>) => set((state) => ({ history: [{ ...entry, id: `hist-${Date.now()}`, timestamp: new Date().toISOString() }, ...state.history] })),

  startSchedulingJob: async () => { /* ... */ },
  cancelSchedulingJob: async (jobId: string) => { /* ... */ },
  pollJobStatus: (jobId: string) => { /* This function is now handled by the hook */ },
  
  initializeApp: async () => {
    const token = localStorage.getItem('authToken');
    if (!token) {
      set({ isAuthenticated: false });
      return;
    }
    
    try {
      // Fetch user data first to ensure user object is populated
      const userResponse = await api.getCurrentUser();
      const userData = userResponse.data;
      const user = {
        id: userData.id,
        name: `${userData.first_name} ${userData.last_name}`,
        email: userData.email,
        role: userData.role,
      };
      set({ user });

      const sessionResponse = await api.getActiveSession();
      if (sessionResponse.data) {
        const sessionId = sessionResponse.data.id;
        set({ activeSessionId: sessionId, isAuthenticated: true });
        
        // Fetch main timetable only for admins, portals fetch their own data
        if (user.role === 'admin') {
            const timetableResponse = await api.getLatestTimetableForActiveSession();
            if (timetableResponse.data?.success && timetableResponse.data.data) {
              get().setTimetable(timetableResponse.data.data);
              const conflicts = timetableResponse.data.data.timetable?.solution?.conflicts || [];
              get().setConflicts(conflicts as Conflict[]);
            } else {
               toast.info('No timetable found for the active session.');
            }
        }
      } else {
        throw new Error('No active session found.');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred.';
      toast.error(`Initialization failed: ${errorMessage}`);
      get().setAuthenticated(false, null);
      localStorage.removeItem('authToken');
    }
  },
}));