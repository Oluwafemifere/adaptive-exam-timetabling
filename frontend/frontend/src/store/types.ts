// All of your type and interface definitions go here.

export interface Exam {
  id: string;
  courseCode: string;
  courseName: string;
  date: string;
  timeSlot: string;
  room: string;
  instructor: string;
  capacity: number;
  studentsCount: number;
  duration: number;
}

export interface Conflict {
  id: string;
  type: 'hard' | 'soft';
  severity: 'high' | 'medium' | 'low';
  message: string;
  examIds: string[];
  autoResolvable: boolean;
}

export interface Room {
  id: string;
  name: string;
  capacity: number;
  type: string;
  facilities: string[];
  available: boolean;
}

export interface KPIData {
  scheduledExams: number;
  activeConflicts: number;
  constraintSatisfactionRate: number;
  roomUtilization: number;
  studentsAffected: number;
  processingTime: number;
}

export interface UploadStatus {
  isUploading: boolean;
  progress: number;
  files: {
    students: File | null;
    courses: File | null;
    registrations: File | null;
    rooms: File | null;
    invigilators: File | null;
    constraints: File | null;
  };
  validation: {
    students: { valid: boolean; errors: string[] };
    courses: { valid: boolean; errors: string[] };
    registrations: { valid: boolean; errors: string[] };
    rooms: { valid: boolean; errors: string[] };
    invigilators: { valid: boolean; errors: string[] };
    constraints: { valid: boolean; errors: string[] };
  };
}

export interface SchedulingStatus {
  isRunning: boolean;
  phase: 'idle' | 'cp-sat' | 'genetic-algorithm' | 'completed' | 'error';
  progress: number;
  metrics: {
    constraintsSatisfied: number;
    totalConstraints: number;
    iterationsCompleted: number;
    bestSolution: number;
  };
  canPause: boolean;
  canCancel: boolean;
}