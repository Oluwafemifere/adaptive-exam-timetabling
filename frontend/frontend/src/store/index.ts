import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// Import all the types from the new types.ts file
import type {
  Exam,
  Conflict,
  Room,
  KPIData,
  UploadStatus,
  SchedulingStatus,
  AppState
} from './types';

// The interface definitions have been moved to types.ts

// Main App Store
interface AppState {
  // Navigation
  currentPage: string;
  setCurrentPage: (page: string) => void;
  
  // KPI Data
  kpiData: KPIData;
  setKpiData: (data: KPIData) => void;
  
  // Exams
  exams: Exam[];
  setExams: (exams: Exam[]) => void;
  addExam: (exam: Exam) => void;
  updateExam: (id: string, exam: Partial<Exam>) => void;
  deleteExam: (id: string) => void;
  
  // Conflicts
  conflicts: Conflict[];
  setConflicts: (conflicts: Conflict[]) => void;
  resolveConflict: (id: string) => void;
  
  // Rooms
  rooms: Room[];
  setRooms: (rooms: Room[]) => void;
  
  // Upload State
  uploadStatus: UploadStatus;
  setUploadStatus: (status: Partial<UploadStatus>) => void;
  
  // Scheduling State
  schedulingStatus: SchedulingStatus;
  setSchedulingStatus: (status: Partial<SchedulingStatus>) => void;
  
  // System Status
  systemStatus: {
    constraintEngine: 'active' | 'idle' | 'error';
    autoResolution: boolean;
    dataSyncProgress: number;
  };
  setSystemStatus: (status: Partial<AppState['systemStatus']>) => void;
  
  // Settings
  settings: {
    theme: 'light' | 'dark';
    notifications: boolean;
    autoSave: boolean;
    constraintWeights: {
      noOverlap: number;
      roomCapacity: number;
      instructorAvailability: number;
      studentConflicts: number;
    };
  };
  updateSettings: (settings: Partial<AppState['settings']>) => void;
}

// The rest of your useAppStore implementation remains exactly the same...
export const useAppStore = create<AppState>()(
  devtools(
    (set) => ({
      // Initial State
      currentPage: 'Dashboard',
      kpiData: { scheduledExams: 0, activeConflicts: 0, constraintSatisfactionRate: 100, roomUtilization: 0, studentsAffected: 0, processingTime: 0 },
      exams: [],
      conflicts: [],
      rooms: [],
      uploadStatus: { isUploading: false, progress: 0, files: { students: null, courses: null, registrations: null, rooms: null, invigilators: null, constraints: null }, validation: { /* ... initial validation state ... */ } },
      schedulingStatus: { isRunning: false, phase: 'idle', progress: 0, metrics: { /* ... initial metrics ... */ }, canPause: false, canCancel: false },
      systemStatus: { constraintEngine: 'idle', autoResolution: true, dataSyncProgress: 100 },
      settings: { theme: 'light', notifications: true, autoSave: true, constraintWeights: { noOverlap: 1, roomCapacity: 1, instructorAvailability: 1, studentConflicts: 1 } },
      
      // Actions
      setCurrentPage: (page) => set({ currentPage: page }),
      setKpiData: (data) => set({ kpiData: data }),
      setExams: (exams) => set({ exams }),
      addExam: (exam) => set((state) => ({ exams: [...state.exams, exam] })),
      updateExam: (id, updatedExam) => set((state) => ({
        exams: state.exams.map((exam) => exam.id === id ? { ...exam, ...updatedExam } : exam)
      })),
      deleteExam: (id) => set((state) => ({ exams: state.exams.filter((exam) => exam.id !== id) })),
      setConflicts: (conflicts) => set({ conflicts }),
      resolveConflict: (id) => set((state) => ({ 
        conflicts: state.conflicts.filter(c => c.id !== id) 
      })),
      setRooms: (rooms) => set({ rooms }),
      setUploadStatus: (status) => set((state) => ({ uploadStatus: { ...state.uploadStatus, ...status } })),
      setSchedulingStatus: (status) => set((state) => ({ schedulingStatus: { ...state.schedulingStatus, ...status } })),
      setSystemStatus: (status) => set((state) => ({ systemStatus: { ...state.systemStatus, ...status } })),
      updateSettings: (settings) => set((state) => ({ settings: { ...state.settings, ...settings } })),
    }),
    {
      name: 'exam-timetabling-store',
    }
  )
);