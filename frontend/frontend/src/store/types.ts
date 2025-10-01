// frontend/src/store/types.ts

// Matches the 'ExamRead' schema from the OpenAPI spec
export interface AcademicSession {
  id: string;
  name: string;
  start_date: string; // format: date
  end_date: string; // format: date
  is_active: boolean;
}

// --- NEW: Interface for Course entity ---
export interface Course {
  id: string;
  code: string;
  name: string;
  department: string;
  instructor_id?: string | null;
  duration_minutes: number;
  expected_students: number;
}

// --- NEW: Interface for User entity ---
export interface User {
  id: string;
  name: string;
  email: string;
  role?: string; 
}


// Matches the 'ExamRead' schema from the OpenAPI spec
export interface Exam {
  id: string;
  course_id: string;
  session_id: string;
  duration_minutes: number;
  expected_students: number;
  status: string;
  instructor_id?: string | null;
}

// Matches the 'ExamUpdate' schema for mutation payloads
export type ExamUpdatePayload = Partial<Omit<Exam, 'id'>> & {
    date?: string;
    start_time?: string;
    end_time?: string;
    room_codes?: string[];
};

export interface Statistics {
  total_exams: number;
  assigned_exams: number;
  unassigned_exams: number;
  room_conflicts: number;
  time_conflicts: number;
  student_conflicts: number;
  room_utilization_percentage: number;
  timeslot_utilization_percentage: number;
}
// ADDED: Capacity Metrics to match the API response
export interface CapacityMetrics {
  expected_students: number;
  total_assigned_capacity: number;
  utilization_percentage: number;
  has_sufficient_capacity: boolean;
}

// --- UPDATED: Assignment interface to match the API response JSON ---
export interface Assignment {
  date: string;
  exam_id: string;
  course_id: string;
  room_codes: string[];
  course_code: string;
  course_title: string;
  department_name: string;
  start_time: string;
  end_time: string;
  student_count: number;
  duration_minutes: number;
  invigilators: { id: string; name: string; email: string | null }[];
  conflicts: string[];
  capacity_metrics: CapacityMetrics;
  instructor_name: string; // Added from JSON
  is_practical: boolean; // Added from JSON
  rooms: { id: string; code: string; building_name: string }[]; // Added from JSON
}


export interface Solution {
  status: 'feasible' | 'infeasible' | 'partial';
  solution_id: string; 
  problem_id: string; 
  created_at: string; 
  last_modified: string;
  statistics: Statistics;
  assignments: Record<string, Assignment>; 
  conflicts?: Conflict[];
}

export interface TimetableResult {
  solution: Solution;
  statistics: Statistics;
  conflicts?: Conflict[];
  meta?: {
    source: string;
    generated_by: string;
    generation_time: string;
  };
}

export interface TimetableResponse {
    success: boolean;
    message: string;
    data: TimetableResult;
    version_id: string;
    last_modified: string;
}


// Represents a conflict within the system
export interface Conflict {
  id: string;
  type: 'hard' | 'soft';
  severity: 'high' | 'medium' | 'low';
  message: string;
  examIds: string[]; 
  autoResolvable: boolean;
  resolution_suggestion?: string;
}

// Matches the 'RoomRead' schema
export interface Room {
  id: string;
  code: string;
  name: string;
  capacity: number;
  exam_capacity?: number | null;
  building_id: string;
  room_type_id: string;
  is_active: boolean;
}

// Matches the expected data structure for the dashboard KPI endpoint
export interface KPIData {
  total_exams: number;
  total_courses: number;
  total_students_registered: number;
  total_departments: number;
  total_faculties: number;
  total_rooms_used: number;
  total_invigilators_assigned: number;
  scheduling_status: {
    completed_jobs: number;
    pending_jobs: number;
    failed_jobs: number;
    running_jobs: number;
  };
  latest_timetable_version: number | null;
}


export interface UploadStatus {
  isUploading: boolean;
  progress: number;
  files: {
    [key: string]: File | null;
  };
  validation: {
    [key:string]: { valid: boolean; errors: string[] };
  };
}

// Derived from 'TimetableJobRead' schema and WebSocket updates
export interface SchedulingStatus {
  jobId?: string | null;
  isRunning: boolean;
  phase: string;
  progress: number;
  metrics: {
    constraintsSatisfied?: number;
    totalConstraints?: number;
    iterationsCompleted?: number;
    bestSolution?: number;
    solver_phase?: string | null;
    error_message?: string | null;
  };
  canPause: boolean;
  canCancel: boolean;
}

export interface SystemStatus {
  constraintEngine: 'idle' | 'active' | 'error';
  autoResolution: boolean;
  dataSyncProgress: number;
}

export interface SettingsState {
  theme: 'light' | 'dark';
  constraintWeights: {
    noOverlap: number;
    roomCapacity: number;
    instructorAvailability: number;
    studentConflicts: number;
  };
  notifications: {
    email: boolean;
    sms: boolean;
  };
}

// Matches the 'TimetableGenerationRequest' schema from OpenAPI
export interface TimetableGenerationRequest {
  session_id: string;
  options?: Record<string, unknown> | null;
  start_date: string;
  end_date: string; 
}

export interface ActiveTimetableResponse {
  success: boolean;
  message: string;
  data: {
    timetable: TimetableResult;
    session_id: string;
    job_id: string;
  };
  error: string | null;
}
// UPDATED: TimeSlot now represents a single hour for the grid
export interface TimeSlot {
  id: string; // e.g., "9:00"
  label: string; // e.g., "9:00 - 10:00"
  start_hour: number;
}

// This is the flattened object we'll use for rendering.
// It combines API data into a structure the UI components can easily use.
export type RenderableExam = { 
  id: string;
  date: string;
  startTime: string;
  endTime: string;
  courseCode: string;
  courseName: string;
  departments: string[];
  room: string;
  building: string;
  instructor: string;
  invigilator: string;
  expectedStudents: number;
  roomCapacity: number;
  notes?: string;
  examType: string;
  conflicts: string[];
  // Keep original assignment for reference if needed
  originalAssignment: Assignment;
};


export interface TimetableCalendarProps {
  exams: RenderableExam[];
  conflicts: Conflict[];
  dateRange: string[];
  timeSlots: TimeSlot[];
  viewType: 'general' | 'department'; // Add viewType to props
}