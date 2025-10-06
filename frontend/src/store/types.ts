// frontend/src/store/types.ts
export interface RenderableExam {
  id: string;
  examId: string;
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
  facultyName: string; 
  notes?: string;
  examType: string;
  instructor: string;
  conflicts?: string[];
  level: string;
  semester: string;
  academicYear: string;
}

// --- API Data Models ---

export interface TimetableAssignmentData {
  exam_id: string;
  course_code: string;
  course_title: string;
  duration_minutes: number;
  student_count: number;
  faculty_name: string; 
  department_name: string;
  is_practical: boolean;
  instructor_name: string;
  date: string;
  start_time: string;
  end_time: string;
  rooms: {
    id: string;
    code: string;
    exam_capacity: number;
    building_name: string;
  }[];
  invigilators: {
    id: string;
    name: string;
  }[];
  conflicts: { message: string }[];
}

export interface TimetableSolution {
  status: string;
  assignments: Record<string, TimetableAssignmentData>;
  conflicts: any[]; 
}

export interface TimetableDetails {
  solution: TimetableSolution;
  statistics: { [key: string]: any };
  is_enriched: boolean;
  objective_value: number;
  completion_percentage: number;
}

export interface TimetableResponseData {
  job_id: string;
  session_id: string;
  timetable: TimetableDetails;
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

export interface JobStatus {
  id: string;
  session_id: string;
  status: 'running' | 'queued' | 'completed' | 'failed' | 'cancelled';
  progress_percentage: number;
  solver_phase: string | null;
  error_message: string | null;
  [key: string]: any;
}

export interface SchedulingStatus {
  isRunning: boolean;
  jobId: string | null;
  phase: string;
  progress: number;
  canPause: boolean;
  canResume: boolean;
  canCancel: boolean;
  metrics: Partial<JobStatus>;
}

export interface UploadStatus {
  isUploading: boolean;
  progress: number;
}

export interface AppSettings {
  theme: 'light' | 'dark';
  constraintWeights: Record<string, number>;
  notifications: {
    emailNotifications: boolean;
    conflictAlerts: boolean;
    schedulingUpdates: boolean;
  };
}

export type UserRole = 'student' | 'staff' | 'admin' | 'superuser';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  department?: string;
  studentId?: string;
  staffId?: string;
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

export interface StaffSchedules {
  instructorSchedule: StaffAssignment[];
  invigilatorSchedule: StaffAssignment[];
  changeRequests: ChangeRequest[];
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
}

export interface Notification {
  id: string;
  type: 'conflict_report' | 'change_request' | 'system_alert' | 'job_completed' | 'job_failed';
  title: string;
  message: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  isRead: boolean;
  createdAt: string;
  relatedId?: string;
  actionRequired?: boolean;
}

export interface HistoryEntry {
  id: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  user_email: string;
  created_at: string;
  new_values: Record<string, any>;
  old_values: Record<string, any>;
}


export interface AcademicSession {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

// --- NEW DASHBOARD TYPES ---
export interface DashboardKpis {
  total_exams_scheduled: number;
  unresolved_hard_conflicts: number;
  total_soft_conflicts: number;
  overall_room_utilization: number;
}

export interface ConflictHotspot {
  timeslot: string;
  conflict_count: number;
}

export interface TopBottleneck {
  type: 'exam' | 'room';
  item: string;
  reason: string;
  issue_count: number;
}
// --- END NEW DASHBOARD TYPES ---


// --- NEW TYPES FOR ADMIN REPORTS & REQUESTS ---

export interface ReportSummaryCounts {
  total: number;
  unread: number;
  urgent_action_required: number;
}

export interface StudentInfo {
  id: string;
  matric_number: string;
  first_name: string;
  last_name: string;
  email?: string;
}

export interface StaffInfo {
  id: string;
  staff_number: string;
  first_name: string;
  last_name: string;
  email?: string;
  department_code?: string;
}

export interface ExamDetails {
  exam_id: string;
  course_code: string;
  course_title: string;
  session_name: string;
}

export interface AssignmentDetails {
  assignment_id: string;
  exam_date: string; // date string
  course_code: string;
  course_title: string;
  room_code: string;
  room_name: string;
}

export interface ReviewDetails {
  reviewed_by_user_id: string;
  reviewer_email?: string;
  reviewer_name?: string;
  resolver_notes?: string;
  review_notes?: string;
}

export interface AdminConflictReport {
  id: string;
  status: string;
  description?: string;
  submitted_at: string; // datetime string
  reviewed_at?: string;
  student: StudentInfo;
  exam_details: ExamDetails;
  review_details?: ReviewDetails;
}

export interface AdminChangeRequest {
  id: string;
  status: string;
  reason?: string;
  description?: string;
  submitted_at: string; // datetime string
  reviewed_at?: string;
  staff: StaffInfo;
  assignment_details: AssignmentDetails;
  review_details?: ReviewDetails;
}

export interface AllReportsResponse {
  summary_counts: ReportSummaryCounts;
  conflict_reports: AdminConflictReport[];
  assignment_change_requests: AdminChangeRequest[];
}

export interface AppState {
  currentPage: string;
  isAuthenticated: boolean;
  user: User | null;
  exams: RenderableExam[];
  conflicts: Conflict[];
  activeSessionId: string | null;
  currentJobId: string | null;
  studentExams: StudentExam[];
  instructorSchedule: StaffAssignment[];
  invigilatorSchedule: StaffAssignment[];
  conflictReports: ConflictReport[]; // User-specific reports
  changeRequests: ChangeRequest[]; // User-specific requests
  notifications: Notification[];
  history: HistoryEntry[];
  systemStatus: SystemStatus;
  schedulingStatus: SchedulingStatus;
  uploadStatus: UploadStatus;
  settings: AppSettings;
  // Admin-level reports
  reportSummaryCounts: ReportSummaryCounts | null;
  allConflictReports: AdminConflictReport[];
  allChangeRequests: AdminChangeRequest[];
  
  // NEW DASHBOARD STATE
  dashboardKpis: DashboardKpis | null;
  conflictHotspots: ConflictHotspot[];
  topBottlenecks: TopBottleneck[];
  recentActivity: HistoryEntry[];

  setCurrentPage: (page: string) => void;
  setAuthenticated: (isAuth: boolean, user?: User | null) => void;
  setTimetable: (timetableData: TimetableResponseData) => void;
  setConflicts: (conflicts: Conflict[]) => void;
  setSystemStatus: (status: Partial<SystemStatus>) => void;
  setSchedulingStatus: (status: Partial<SchedulingStatus>) => void;
  setUploadStatus: (status: Partial<UploadStatus>) => void;
  updateSettings: (settings: Partial<AppSettings>) => void;
  setStudentExams: (exams: StudentExam[]) => void;
  setConflictReports: (reports: ConflictReport[]) => void;
  setStaffSchedules: (schedules: StaffSchedules) => void;
  addConflictReport: (report: Omit<ConflictReport, 'id' | 'status' | 'submittedAt'>) => void;
  addChangeRequest: (request: Omit<ChangeRequest, 'id' | 'status' | 'submittedAt'>) => void;
  updateConflictReportStatus: (id: string, status: ConflictReport['status']) => void;
  updateChangeRequestStatus: (id: string, status: ChangeRequest['status']) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'createdAt'>) => void;
  markNotificationAsRead: (id: string) => void;
  clearNotifications: () => void;
  addHistoryEntry: (entry: Omit<HistoryEntry, 'id' | 'created_at'>) => void;
  startSchedulingJob: () => Promise<void>;
  cancelSchedulingJob: (jobId: string) => Promise<void>;
  pollJobStatus: (jobId: string) => void;
  initializeApp: () => Promise<void>;
  setAllReports: (data: AllReportsResponse) => void;
  
  // NEW DASHBOARD ACTIONS
  setDashboardKpis: (kpis: DashboardKpis) => void;
  setConflictHotspots: (hotspots: ConflictHotspot[]) => void;
  setTopBottlenecks: (bottlenecks: TopBottleneck[]) => void;
  setRecentActivity: (activity: HistoryEntry[]) => void;
}