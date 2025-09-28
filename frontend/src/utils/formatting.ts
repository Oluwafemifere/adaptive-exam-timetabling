// Constants for the Adaptive Exam Timetabling System
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws';

// Time slots configuration
export const TIME_SLOTS = [
  { id: '09:00', label: '09:00 - 12:00', start: '09:00', end: '12:00' },
  { id: '12:00', label: '12:00 - 15:00', start: '12:00', end: '15:00' },
  { id: '15:00', label: '15:00 - 18:00', start: '15:00', end: '18:00' },
] as const;

// Days of the week
export const WEEKDAYS = [
  { id: 'monday', label: 'Monday', short: 'Mon' },
  { id: 'tuesday', label: 'Tuesday', short: 'Tue' },
  { id: 'wednesday', label: 'Wednesday', short: 'Wed' },
  { id: 'thursday', label: 'Thursday', short: 'Thu' },
  { id: 'friday', label: 'Friday', short: 'Fri' },
  { id: 'saturday', label: 'Saturday', short: 'Sat' },
] as const;

// System status types
export const SYSTEM_STATUS = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  PROCESSING: 'processing',
  ERROR: 'error',
} as const;

// Conflict severity levels
export const CONFLICT_SEVERITY = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
} as const;

// Constraint types
export const CONSTRAINT_TYPES = {
  HARD: 'hard',
  SOFT: 'soft',
} as const;

// File upload constants
export const UPLOAD_CONFIG = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  ACCEPTED_FORMATS: ['.csv', '.json'],
  REQUIRED_FILES: [
    'students.csv',
    'courses.csv',
    'registrations.csv',
    'rooms.csv',
  ],
  OPTIONAL_FILES: [
    'invigilators.csv',
    'constraints.json',
  ],
} as const;

// Exam status types
export const EXAM_STATUS = {
  SCHEDULED: 'scheduled',
  CONFLICTED: 'conflicted',
  PENDING: 'pending',
  CANCELLED: 'cancelled',
} as const;

// Room types
export const ROOM_TYPES = {
  LECTURE_HALL: 'lecture_hall',
  CLASSROOM: 'classroom',
  LAB: 'lab',
  AUDITORIUM: 'auditorium',
  SEMINAR_ROOM: 'seminar_room',
} as const;

// User roles
export const USER_ROLES = {
  ADMIN: 'admin',
  EXAM_OFFICER: 'exam_officer',
  HOD: 'hod',
  DEAN: 'dean',
  REGISTRY_STAFF: 'registry_staff',
} as const;

// Notification types
export const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
  INFO: 'info',
} as const;

// Report types
export const REPORT_TYPES = {
  STUDENT_SCHEDULES: 'student_schedules',
  ROOM_UTILIZATION: 'room_utilization',
  CONFLICT_SUMMARY: 'conflict_summary',
  INVIGILATOR_ASSIGNMENTS: 'invigilator_assignments',
  EXAM_STATISTICS: 'exam_statistics',
} as const;

// Export formats
export const EXPORT_FORMATS = {
  PDF: 'pdf',
  CSV: 'csv',
  EXCEL: 'excel',
  JSON: 'json',
} as const;

// Optimization phases
export const OPTIMIZATION_PHASES = {
  CP_SAT: 'cp_sat',
  GENETIC_ALGORITHM: 'genetic_algorithm',
  POST_PROCESSING: 'post_processing',
} as const;

// Layout constants
export const LAYOUT = {
  SIDEBAR_WIDTH: 280,
  HEADER_HEIGHT: 64,
  TIMETABLE_CELL_HEIGHT: 120,
  TIMETABLE_CELL_WIDTH: 200,
  CALENDAR_MIN_HEIGHT: 600,
} as const;

// Animation durations (in milliseconds)
export const ANIMATIONS = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
  VERY_SLOW: 1000,
} as const;

// Breakpoints for responsive design
export const BREAKPOINTS = {
  MOBILE: 640,
  TABLET: 1024,
  DESKTOP: 1440,
} as const;

// Color schemes for different themes
export const COLOR_SCHEMES = {
  DEFAULT: {
    primary: '#1e40af',
    secondary: '#059669',
    warning: '#d97706',
    error: '#dc2626',
    neutral: '#64748b',
  },
  HIGH_CONTRAST: {
    primary: '#000000',
    secondary: '#ffffff',
    warning: '#ff8c00',
    error: '#ff0000',
    neutral: '#333333',
  },
} as const;

// Validation patterns
export const VALIDATION_PATTERNS = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PHONE: /^[\+]?[1-9][\d]{0,15}$/,
  STUDENT_ID: /^[A-Z0-9]{6,12}$/,
  COURSE_CODE: /^[A-Z]{2,4}\s?\d{3}$/,
  ROOM_CODE: /^[A-Z0-9\-]{3,10}$/,
} as const;

// Default constraint weights
export const DEFAULT_CONSTRAINT_WEIGHTS = {
  studentConflicts: 1.0,
  roomCapacity: 1.0,
  staffAvailability: 1.0,
  examDistribution: 0.8,
  roomUtilization: 0.6,
  staffBalance: 0.4,
} as const;

// API endpoints
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    PROFILE: '/auth/profile',
  },
  DATA: {
    UPLOAD: '/data/upload',
    VALIDATE: '/data/validate',
    EXPORT: '/data/export',
  },
  SCHEDULING: {
    GENERATE: '/scheduling/generate',
    STATUS: '/scheduling/status',
    RESULTS: '/scheduling/results',
    CONSTRAINTS: '/scheduling/constraints',
  },
  REPORTS: {
    GENERATE: '/reports/generate',
    LIST: '/reports/list',
    DOWNLOAD: '/reports/download',
  },
} as const;