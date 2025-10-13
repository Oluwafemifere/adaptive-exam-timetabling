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
logs: string[];
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

export interface UserManagementRecord {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_superuser: boolean;
  role: UserRole;
  last_login?: string;
}

export interface PaginatedUserResponse {
  total_items: number;
  total_pages: number;
  page: number;
  page_size: number;
  items: UserManagementRecord[];
  total_active?: number;
  total_admins?: number;
}
export interface StudentSelfRegisterPayload {
  matric_number: string;
  email: string;
  password: string;
}

export interface StaffSelfRegisterPayload {
  staff_number: string;
  email: string;
  password: string;
}
export interface AdminUserCreatePayload {
    user_type: 'student' | 'admin';
    email: string;
    first_name: string;
    last_name: string;
    password: string;
    session_id?: string;
    matric_number?: string;
    programme_code?: string;
    entry_year?: number;
}

export interface UserUpdatePayload {
  email?: string;
  first_name?: string;
  last_name?: string;
  is_active?: boolean;
  role?: UserRole;
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
instructor: string;
invigilator: string;
expectedStudents: number;
roomCapacity: number;
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
expectedStudents: number;
roomCapacity: number;
instructor: string;
invigilator: string;
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
  entityType: string;
  entityId?: string;
  userName: string;
  timestamp: string;
  details: Record<string, any>;
  changes?: {
    before: Record<string, any>;
    after: Record<string, any>;
  };
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
export interface ConstraintParameter {
  key: string;
  type?: string; 
  value: any;
}

export interface Constraint {
  rule_id: string; 
  code: string;
  name: string;
  description: string;
  type: 'hard' | 'soft';
  category: string; 
  is_enabled: boolean;
  weight: number;
  parameters: Record<string, any>;
}

export interface ConstraintCategory {
id: string;
name: string;
constraints: Constraint[];
}

// --- REVISED AND NEW CONFIGURATION TYPES ---

/**
 * Represents a single configurable rule as received from the API for display.
 * Corresponds to the `RuleSettingRead` Pydantic model.
 */
export interface RuleSettingRead {
  rule_id: string;
  code: string;
  name: string;
  description: string | null;
  type: 'hard' | 'soft';
  category: string;
  is_enabled: boolean;
  weight: number;
  parameters: Record<string, any>;
}

/**
 * Represents the detailed structure of a system configuration, including all its rules.
 * Corresponds to the `SystemConfigDetails` Pydantic model.
 */
export interface SystemConfigurationDetails {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  solver_parameters: Record<string, any>;
  constraint_config_id: string;
  rules: RuleSettingRead[];
}

/**
 * Represents the lean structure of a system configuration for listing.
 * Corresponds to the `SystemConfigListItem` Pydantic model.
 */
export interface SystemConfiguration {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
}

/**
 * Represents the payload for saving a rule's settings.
 * Corresponds to the `RuleSetting` Pydantic model.
 */
export interface RuleSetting {
  rule_id: string;
  is_enabled: boolean;
  weight: number;
  parameters: Record<string, any>;
}

/**
 * Represents the complete payload for creating or updating a system configuration.
 * Corresponds to the `SystemConfigSave` Pydantic model.
 */
export interface SystemConfigSavePayload {
  id?: string;
  name: string;
  description?: string | null;
  is_default: boolean;
  solver_parameters: Record<string, any>;
  rules: RuleSetting[];
}

export interface JobSummary {
  id: string;
  created_at: string;
  status: string;
  version_id: string | null;
  is_published: boolean;
}
export type StagingRecord = {
  id?: string;
  session_id: string;
  [key: string]: any; // Allows for other properties like 'code', 'matric_number', etc.
};

// Buildings
export interface StagingBuildingCreate {
  code: string;
  name: string;
  faculty_code: string;
}
export interface StagingBuildingUpdate {
  name?: string;
  faculty_code?: string;
}

// CourseDepartments
export interface StagingCourseDepartmentCreate {
  course_code: string;
  department_code: string;
}
// --- FIX: Added missing type ---
export interface StagingCourseDepartmentUpdate {
  department_code?: string;
}

// CourseFaculties
export interface StagingCourseFacultyCreate {
  course_code: string;
  faculty_code: string;
}
// --- FIX: Added missing type ---
export interface StagingCourseFacultyUpdate {
  faculty_code?: string;
}


// CourseInstructors
export interface StagingCourseInstructorCreate {
  staff_number: string;
  course_code: string;
}

// CourseRegistrations
export interface StagingCourseRegistrationCreate {
  student_matric_number: string;
  course_code: string;
  registration_type?: string;
}
export interface StagingCourseRegistrationUpdate {
  registration_type: string;
}

// Courses
export interface StagingCourseCreate {
  code: string;
  title: string;
  credit_units: number;
  exam_duration_minutes: number;
  course_level: number;
  semester: number;
  is_practical: boolean;
  morning_only: boolean;
}
export interface StagingCourseUpdate {
  title?: string;
  credit_units?: number;
  exam_duration_minutes?: number;
  course_level?: number;
  semester?: number;
  is_practical?: boolean;
  morning_only?: boolean;
}

// Departments
export interface StagingDepartmentCreate {
  code: string;
  name: string;
  faculty_code: string;
}
export interface StagingDepartmentUpdate {
  name?: string;
  faculty_code?: string;
}

// Faculties
export interface StagingFacultyCreate {
  code: string;
  name: string;
}
export interface StagingFacultyUpdate {
  name?: string;
}

// Programmes
export interface StagingProgrammeCreate {
  code: string;
  name: string;
  department_code: string;
  degree_type: string;
  duration_years: number;
}
export interface StagingProgrammeUpdate {
  name?: string;
  department_code?: string;
  degree_type?: string;
  duration_years?: number;
}

// Rooms
export interface StagingRoomCreate {
  code: string;
  name: string;
  building_code: string;
  capacity: number;
  exam_capacity: number;
  has_ac: boolean;
  has_projector: boolean;
  has_computers: boolean;
  max_inv_per_room: number;
  room_type_code: string;
  floor_number: number;
  accessibility_features: string[];
  notes?: string;
}
export interface StagingRoomUpdate {
  name?: string;
  building_code?: string;
  capacity?: number;
  exam_capacity?: number;
  has_ac?: boolean;
  has_projector?: boolean;
  has_computers?: boolean;
  max_inv_per_room?: number;
  room_type_code?: string;
  floor_number?: number;
  accessibility_features?: string[];
  notes?: string;
}

// Staff
export interface StagingStaffCreate {
  staff_number: string;
  first_name: string;
  last_name: string;
  email: string;
  department_code: string;
  staff_type: string;
  can_invigilate: boolean;
  is_instructor: boolean;
  max_daily_sessions: number;
  max_consecutive_sessions: number;
  max_concurrent_exams: number;
  max_students_per_invigilator: number;
  user_email?: string;
}
export interface StagingStaffUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  department_code?: string;
  staff_type?: string;
  can_invigilate?: boolean;
  is_instructor?: boolean;
  max_daily_sessions?: number;
  max_consecutive_sessions?: number;
  max_concurrent_exams?: number;
  max_students_per_invigilator?: number;
  user_email?: string;
}

// StaffUnavailability
export interface StagingStaffUnavailabilityCreate {
  staff_number: string;
  unavailable_date: string; // YYYY-MM-DD
  period_name: string;
  reason?: string;
}
export interface StagingStaffUnavailabilityUpdate {
  reason?: string;
}

// Students
export interface StagingStudentCreate {
  matric_number: string;
  first_name: string;
  last_name: string;
  entry_year: number;
  programme_code: string;
  user_email?: string;
}
export interface StagingStudentUpdate {
  first_name?: string;
  last_name?: string;
  entry_year?: number;
  programme_code?: string;
  user_email?: string;
}
export interface AppState {
currentPage: string;
isAuthenticated: boolean;
user: User | null;
users: UserManagementRecord[];
exams: RenderableExam[];
conflicts: Conflict[];
activeSessionId: string | null;
activeSessionName: string | null;
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
sessionJobs: JobSummary[];
// Configuration State
  configurations: SystemConfiguration[]; // For the dropdown list
  activeConfigurationId: string | null;
  activeConfigurationDetails: SystemConfigurationDetails | null;


setUsers: (users: UserManagementRecord[]) => void;
addUser: (user: UserManagementRecord) => void;
updateUserInList: (user: UserManagementRecord) => void;
removeUserFromList: (userId: string) => void;  
setCurrentPage: (page: string) => void;
setAuthenticated: (isAuth: boolean, user?: User | null) => void;
setTimetable: (timetableData: TimetableResponseData) => void;
setConflicts: (conflicts: Conflict[]) => void;
setSystemStatus: (status: Partial<SystemStatus>) => void;
setSchedulingStatus: (status: Partial<SchedulingStatus>) => void;
addSchedulingLog: (log: string) => void;
clearSchedulingLogs: () => void;
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
setHistory: (history: HistoryEntry[]) => void;
startSchedulingJob: (configuration_id: string) => Promise<void>;
fetchAndSetJobResult: (jobId: string) => Promise<void>;
fetchSessionJobs: (sessionId: string) => Promise<void>;
cancelSchedulingJob: (jobId: string) => Promise<void>;
initializeApp: () => Promise<void>;
setAllReports: (data: AllReportsResponse) => void;
setConfigurations: (configs: SystemConfiguration[]) => void;
  fetchAndSetActiveConfiguration: (configId: string) => Promise<void>;
  saveActiveConfiguration: (updatedConfig: SystemConfigurationDetails) => Promise<void>;
// NEW DASHBOARD ACTIONS
setDashboardKpis: (kpis: DashboardKpis) => void;
setConflictHotspots: (hotspots: ConflictHotspot[]) => void;
setTopBottlenecks: (bottlenecks: TopBottleneck[]) => void;
setRecentActivity: (activity: HistoryEntry[]) => void;  
}