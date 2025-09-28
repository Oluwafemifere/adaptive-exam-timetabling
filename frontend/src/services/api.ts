import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { OPTIMIZATION_PHASES, CONSTRAINT_TYPES, DEFAULT_CONSTRAINT_WEIGHTS } from '../utils/constants';

// Types
export interface Constraint {
  id: string;
  name: string;
  type: 'hard' | 'soft';
  weight: number;
  enabled: boolean;
  description: string;
  parameters?: Record<string, any>;
}

export interface ExamSlot {
  id: string;
  courseCode: string;
  courseName: string;
  roomCode: string;
  roomName: string;
  date: string;
  timeSlot: string;
  duration: number;
  studentsCount: number;
  invigilator?: string;
  capacity?: number;
  utilization?: number;
  conflicts?: string[];
}

export interface Conflict {
  id: string;
  type: 'student' | 'room' | 'instructor' | 'capacity';
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  affectedExams: string[];
  affectedStudents?: string[];
  suggestedActions: string[];
  isResolved: boolean;
  createdAt: string;
}

export interface OptimizationProgress {
  phase: string;
  progress: number;
  eta: number;
  currentBest?: number;
  variables?: number;
  constraints?: number;
  message?: string;
}

export interface SchedulingState {
  // Data state
  uploadedFiles: Record<string, File>;
  validationResults: Record<string, any>;
  
  // Constraints
  constraints: Constraint[];
  
  // Schedule state
  schedule: ExamSlot[];
  conflicts: Conflict[];
  
  // Optimization state
  isOptimizing: boolean;
  optimizationProgress: OptimizationProgress | null;
  optimizationHistory: OptimizationProgress[];
  
  // UI state
  selectedExam: string | null;
  selectedConflicts: string[];
  viewMode: 'calendar' | 'list' | 'conflicts';
  dateRange: { start: string; end: string };
  filters: {
    rooms: string[];
    courses: string[];
    timeSlots: string[];
    conflictTypes: string[];
  };
  
  // Status
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
  
  // Actions
  setUploadedFiles: (files: Record<string, File>) => void;
  setValidationResults: (results: Record<string, any>) => void;
  updateConstraint: (id: string, updates: Partial<Constraint>) => void;
  resetConstraints: () => void;
  startOptimization: () => Promise<void>;
  stopOptimization: () => void;
  updateOptimizationProgress: (progress: OptimizationProgress) => void;
  setSchedule: (schedule: ExamSlot[]) => void;
  updateExam: (examId: string, updates: Partial<ExamSlot>) => void;
  moveExam: (examId: string, newDate: string, newTimeSlot: string, newRoom?: string) => void;
  setConflicts: (conflicts: Conflict[]) => void;
  resolveConflict: (conflictId: string) => void;
  selectExam: (examId: string | null) => void;
  setViewMode: (mode: 'calendar' | 'list' | 'conflicts') => void;
  setDateRange: (range: { start: string; end: string }) => void;
  updateFilters: (filters: Partial<typeof initialState.filters>) => void;
  clearError: () => void;
  exportSchedule: (format: string) => Promise<void>;
}

// Initial state
const initialState = {
  uploadedFiles: {},
  validationResults: {},
  constraints: [
    {
      id: 'student-conflicts',
      name: 'Student Conflicts',
      type: 'hard' as const,
      weight: 1.0,
      enabled: true,
      description: 'Prevent students from having multiple exams at the same time',
    },
    {
      id: 'room-capacity',
      name: 'Room Capacity',
      type: 'hard' as const,
      weight: 1.0,
      enabled: true,
      description: 'Ensure room capacity is not exceeded',
    },
    {
      id: 'staff-availability',
      name: 'Staff Availability',
      type: 'hard' as const,
      weight: 1.0,
      enabled: true,
      description: 'Respect staff availability constraints',
    },
    {
      id: 'exam-distribution',
      name: 'Exam Distribution',
      type: 'soft' as const,
      weight: 0.8,
      enabled: true,
      description: 'Distribute exams evenly across time slots',
    },
    {
      id: 'room-utilization',
      name: 'Room Utilization',
      type: 'soft' as const,
      weight: 0.6,
      enabled: true,
      description: 'Maximize room utilization efficiency',
    },
    {
      id: 'staff-balance',
      name: 'Staff Workload Balance',
      type: 'soft' as const,
      weight: 0.4,
      enabled: true,
      description: 'Balance workload across staff members',
    },
  ],
  schedule: [],
  conflicts: [],
  isOptimizing: false,
  optimizationProgress: null,
  optimizationHistory: [],
  selectedExam: null,
  selectedConflicts: [],
  viewMode: 'calendar' as const,
  dateRange: {
    start: new Date().toISOString().split('T')[0],
    end: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  },
  filters: {
    rooms: [],
    courses: [],
    timeSlots: [],
    conflictTypes: [],
  },
  isLoading: false,
  error: null,
  lastUpdated: null,
};

// Create the scheduling store
export const useSchedulingStore = create<SchedulingState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      setUploadedFiles: (files) => {
        set({ uploadedFiles: files }, false, 'setUploadedFiles');
      },

      setValidationResults: (results) => {
        set({ validationResults: results }, false, 'setValidationResults');
      },

      updateConstraint: (id, updates) => {
        const { constraints } = get();
        const updatedConstraints = constraints.map(constraint =>
          constraint.id === id ? { ...constraint, ...updates } : constraint
        );
        set({ constraints: updatedConstraints }, false, 'updateConstraint');
      },

      resetConstraints: () => {
        set({ constraints: initialState.constraints }, false, 'resetConstraints');
      },

      startOptimization: async () => {
        const { constraints, uploadedFiles } = get();
        
        set({ 
          isOptimizing: true, 
          error: null, 
          optimizationProgress: null,
          optimizationHistory: []
        }, false, 'startOptimization:start');

        try {
          const response = await fetch('/api/scheduling/generate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              constraints: constraints.filter(c => c.enabled),
              files: Object.keys(uploadedFiles),
            }),
          });

          if (!response.ok) {
            throw new Error('Failed to start optimization');
          }

          // WebSocket connection for real-time updates would be handled elsewhere
          
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Optimization failed';
          set({
            isOptimizing: false,
            error: errorMessage,
          }, false, 'startOptimization:error');
          throw error;
        }
      },

      stopOptimization: () => {
        set({
          isOptimizing: false,
          optimizationProgress: null,
        }, false, 'stopOptimization');

        // Call stop endpoint
        fetch('/api/scheduling/stop', { method: 'POST' }).catch(() => {
          // Ignore errors
        });
      },

      updateOptimizationProgress: (progress) => {
        const { optimizationHistory } = get();
        set({
          optimizationProgress: progress,
          optimizationHistory: [...optimizationHistory, progress],
        }, false, 'updateOptimizationProgress');
      },

      setSchedule: (schedule) => {
        set({
          schedule,
          lastUpdated: new Date().toISOString(),
        }, false, 'setSchedule');
      },

      updateExam: (examId, updates) => {
        const { schedule } = get();
        const updatedSchedule = schedule.map(exam =>
          exam.id === examId ? { ...exam, ...updates } : exam
        );
        set({
          schedule: updatedSchedule,
          lastUpdated: new Date().toISOString(),
        }, false, 'updateExam');
      },

      moveExam: async (examId, newDate, newTimeSlot, newRoom) => {
        const { schedule } = get();
        const exam = schedule.find(e => e.id === examId);
        
        if (!exam) return;

        // Optimistically update the UI
        const updates: Partial<ExamSlot> = {
          date: newDate,
          timeSlot: newTimeSlot,
        };

        if (newRoom) {
          updates.roomCode = newRoom;
        }

        get().updateExam(examId, updates);

        try {
          const response = await fetch(`/api/scheduling/exams/${examId}/move`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              date: newDate,
              timeSlot: newTimeSlot,
              roomCode: newRoom,
            }),
          });

          if (!response.ok) {
            // Revert the change
            get().updateExam(examId, exam);
            throw new Error('Failed to move exam');
          }

          // Refresh conflicts after move
          const conflictsResponse = await fetch('/api/scheduling/conflicts');
          if (conflictsResponse.ok) {
            const conflicts = await conflictsResponse.json();
            get().setConflicts(conflicts);
          }

        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to move exam';
          set({ error: errorMessage }, false, 'moveExam:error');
          throw error;
        }
      },

      setConflicts: (conflicts) => {
        set({ conflicts }, false, 'setConflicts');
      },

      resolveConflict: async (conflictId) => {
        try {
          const response = await fetch(`/api/scheduling/conflicts/${conflictId}/resolve`, {
            method: 'POST',
          });

          if (!response.ok) {
            throw new Error('Failed to resolve conflict');
          }

          const { conflicts } = get();
          const updatedConflicts = conflicts.map(conflict =>
            conflict.id === conflictId
              ? { ...conflict, isResolved: true }
              : conflict
          );

          set({ conflicts: updatedConflicts }, false, 'resolveConflict');

        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to resolve conflict';
          set({ error: errorMessage }, false, 'resolveConflict:error');
          throw error;
        }
      },

      selectExam: (examId) => {
        set({ selectedExam: examId }, false, 'selectExam');
      },

      setViewMode: (mode) => {
        set({ viewMode: mode }, false, 'setViewMode');
      },

      setDateRange: (range) => {
        set({ dateRange: range }, false, 'setDateRange');
      },

      updateFilters: (filterUpdates) => {
        const { filters } = get();
        set({
          filters: { ...filters, ...filterUpdates }
        }, false, 'updateFilters');
      },

      clearError: () => {
        set({ error: null }, false, 'clearError');
      },

      exportSchedule: async (format) => {
        const { schedule } = get();
        
        try {
          const response = await fetch('/api/scheduling/export', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              format,
              data: schedule,
            }),
          });

          if (!response.ok) {
            throw new Error('Export failed');
          }

          // Handle file download
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `schedule.${format}`;
          link.click();
          window.URL.revokeObjectURL(url);

        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Export failed';
          set({ error: errorMessage }, false, 'exportSchedule:error');
          throw error;
        }
      },
    }),
    {
      name: 'scheduling-store',
    }
  )
);

// Selectors
export const useScheduling = () => {
  const {
    schedule,
    conflicts,
    isOptimizing,
    optimizationProgress,
    constraints,
    selectedExam,
    viewMode,
    dateRange,
    filters,
    error,
    isLoading,
    startOptimization,
    stopOptimization,
    updateConstraint,
    moveExam,
    selectExam,
    setViewMode,
    clearError,
  } = useSchedulingStore();

  return {
    schedule,
    conflicts,
    isOptimizing,
    optimizationProgress,
    constraints,
    selectedExam,
    viewMode,
    dateRange,
    filters,
    error,
    isLoading,
    startOptimization,
    stopOptimization,
    updateConstraint,
    moveExam,
    selectExam,
    setViewMode,
    clearError,
  };
};

export const useScheduleStats = () => {
  return useSchedulingStore((state) => {
    const totalExams = state.schedule.length;
    const totalConflicts = state.conflicts.filter(c => !c.isResolved).length;
    const criticalConflicts = state.conflicts.filter(
      c => !c.isResolved && c.severity === 'critical'
    ).length;
    
    const roomUtilization = state.schedule.reduce((acc, exam) => {
      if (exam.capacity && exam.studentsCount) {
        return acc + (exam.studentsCount / exam.capacity);
      }
      return acc;
    }, 0) / totalExams || 0;

    return {
      totalExams,
      totalConflicts,
      criticalConflicts,
      roomUtilization,
    };
  });
};

export const useConstraints = () => {
  return useSchedulingStore((state) => ({
    constraints: state.constraints,
    updateConstraint: state.updateConstraint,
    resetConstraints: state.resetConstraints,
  }));
};