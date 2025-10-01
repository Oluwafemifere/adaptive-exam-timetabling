export interface Exam {
  id: string;
  courseCode: string;
  courseName: string;
  date: string;
  startTime: string;
  endTime: string;
  duration: number;
  expectedStudents: number;
  room: string;
  roomCapacity: number;
  building: string;
  invigilator: string;
  departments: string[];
  level: string;
  semester: string;
  academicYear: string;
}

export interface RenderableExam {
  id: string;
  courseCode: string;
  courseName: string;
  date: string;
  startTime: string;
  endTime: string;
  duration: number;
  expectedStudents: number;
  room: string;
  roomCapacity: number;
  building: string;
  invigilator: string;
  departments: string[];
  level: string;
  semester: string;
  academicYear: string;
}

export interface Conflict {
  id: string;
  type: 'hard' | 'soft';
  severity: 'high' | 'medium' | 'low';
  message: string;
  examIds: string[];
  autoResolvable: boolean;
}

export interface SystemStatus {
  constraintEngine: 'active' | 'idle' | 'error';
  autoResolution: boolean;
  dataSyncProgress: number;
}

export interface SchedulingStatus {
  isRunning: boolean;
  phase: 'cp-sat' | 'genetic-algorithm' | 'completed' | 'failed' | 'cancelled' | 'idle';
  progress: number;
  jobId: string | null;
  startTime?: string;
  estimatedEndTime?: string;
  canPause: boolean;
  canResume: boolean;
  canCancel: boolean;
  metrics: {
    hard_constraints_violations?: number;
    soft_constraints_violations?: number;
    fitness_score?: number;
    generation?: number;
    error_message?: string;
    processed_exams?: number;
    total_exams?: number;
  };
}

export interface UploadStatus {
  isUploading: boolean;
  progress: number;
}

export interface AppSettings {
  theme: 'light' | 'dark';
  constraintWeights: {
    noOverlap: number;
    roomCapacity: number;
    instructorAvailability: number;
    studentConflicts: number;
  };
  notifications: {
    emailNotifications: boolean;
    conflictAlerts: boolean;
    schedulingUpdates: boolean;
  };
}

export interface AcademicSession {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

export type UserRole = 'student' | 'staff' | 'administrator';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  department?: string;
  studentId?: string; // For students
  staffId?: string; // For staff
}

export interface StudentExam {
  id: string;
  courseCode: string;
  courseName: string;
  date: string;
  startTime: string;
  endTime: string;
  room: string;
  building: string;
  duration: number;
}

export interface StaffAssignment {
  id: string;
  examId: string;
  courseCode: string;
  courseName: string;
  date: string;
  startTime: string;
  endTime: string;
  room: string;
  building: string;
  role: 'instructor' | 'invigilator' | 'lead-invigilator';
  status: 'assigned' | 'change-requested' | 'confirmed';
}

export interface ConflictReport {
  id: string;
  studentId: string;
  examId: string;
  courseCode: string;
  description: string;
  status: 'pending' | 'reviewed' | 'resolved';
  submittedAt: string;
}

export interface ChangeRequest {
  id: string;
  staffId: string;
  assignmentId: string;
  courseCode: string;
  reason: string;
  description?: string;
  status: 'pending' | 'approved' | 'denied';
  submittedAt: string;
  reviewedAt?: string;
  reviewedBy?: string;
  reviewNotes?: string;
}

export interface Notification {
  id: string;
  type: 'conflict_report' | 'change_request' | 'system_alert' | 'job_completed' | 'job_failed';
  title: string;
  message: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  isRead: boolean;
  createdAt: string;
  relatedId?: string; // ID of related entity (conflict report, change request, etc.)
  actionRequired?: boolean;
}

export interface HistoryEntry {
  id: string;
  action: string;
  entityType: 'exam' | 'constraint' | 'user' | 'session' | 'schedule' | 'system';
  entityId?: string;
  userId: string;
  userName: string;
  timestamp: string;
  details: Record<string, any>;
  changes?: {
    before: Record<string, any>;
    after: Record<string, any>;
  };
}

export interface JobResult {
  id: string;
  jobId: string;
  name: string;
  status: 'success' | 'failed' | 'cancelled';
  startTime: string;
  endTime: string;
  exams: Exam[];
  metrics: {
    totalExams: number;
    hardConstraintViolations: number;
    softConstraintViolations: number;
    fitnessScore: number;
    roomUtilization: number;
    timeSlotUtilization: number;
  };
  constraints: Record<string, any>;
  sessionId: string;
}

export interface FilterOptions {
  departments: string[];
  faculties: string[];
  rooms: string[];
  students: string[];
  staff: string[];
  dateRange: {
    start: string;
    end: string;
  };
  timeSlots: string[];
  examTypes: string[];
}

export interface AppState {
  // Navigation
  currentPage: string;
  
  // Authentication
  isAuthenticated: boolean;
  user: User | null;
  
  // Data
  exams: Exam[];
  conflicts: Conflict[];
  activeSessionId: string | null;
  
  // Role-specific data
  studentExams: StudentExam[];
  staffAssignments: StaffAssignment[];
  conflictReports: ConflictReport[];
  changeRequests: ChangeRequest[];
  
  // Admin features
  notifications: Notification[];
  history: HistoryEntry[];
  jobResults: JobResult[];
  filterOptions: FilterOptions;
  
  // Status
  systemStatus: SystemStatus;
  schedulingStatus: SchedulingStatus;
  uploadStatus: UploadStatus;
  
  // Settings
  settings: AppSettings;
  
  // Actions
  setCurrentPage: (page: string) => void;
  setAuthenticated: (isAuth: boolean, user?: User | null) => void;
  setExams: (exams: Exam[]) => void;
  setConflicts: (conflicts: Conflict[]) => void;
  setSystemStatus: (status: Partial<SystemStatus>) => void;
  setSchedulingStatus: (status: Partial<SchedulingStatus>) => void;
  setUploadStatus: (status: Partial<UploadStatus>) => void;
  updateSettings: (settings: Partial<AppSettings>) => void;
  setStudentExams: (exams: StudentExam[]) => void;
  setStaffAssignments: (assignments: StaffAssignment[]) => void;
  addConflictReport: (report: Omit<ConflictReport, 'id' | 'submittedAt'>) => void;
  addChangeRequest: (request: Omit<ChangeRequest, 'id' | 'submittedAt'>) => void;
  updateConflictReportStatus: (id: string, status: ConflictReport['status']) => void;
  updateChangeRequestStatus: (id: string, status: ChangeRequest['status']) => void;
  
  // Admin actions
  addNotification: (notification: Omit<Notification, 'id' | 'createdAt'>) => void;
  markNotificationAsRead: (id: string) => void;
  clearNotifications: () => void;
  addHistoryEntry: (entry: Omit<HistoryEntry, 'id' | 'timestamp'>) => void;
  addJobResult: (result: JobResult) => void;
  updateFilterOptions: (options: Partial<FilterOptions>) => void;
  
  // Scheduling actions
  startSchedulingJob: (sessionId: string) => Promise<void>;
  pauseSchedulingJob: () => void;
  resumeSchedulingJob: () => void;
  cancelSchedulingJob: () => void;
  
  initializeApp: () => Promise<void>;
}