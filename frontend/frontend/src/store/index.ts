// frontend/src/store/index.ts

import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';
import type {
  Exam,
  Conflict,
  Room,
  KPIData,
  UploadStatus,
  SchedulingStatus,
  SystemStatus,
  SettingsState,
  AcademicSession
} from './types';
import * as api from '../services/api';

interface AppState {
  currentPage: string;
  setCurrentPage: (page: string) => void;
  
  activeSessionId: string | null;
  setActiveSessionId: (sessionId: string | null) => void;
  initializeApp: () => Promise<void>;
  
  kpiData: KPIData;
  setKpiData: (data: KPIData) => void;
  
  exams: Exam[];
  setExams: (exams: Exam[]) => void;
  
  conflicts: Conflict[];
  setConflicts: (conflicts: Conflict[]) => void;
  resolveConflict: (id: string) => void;
  
  rooms: Room[];
  setRooms: (rooms: Room[]) => void;
  
  uploadStatus: UploadStatus;
  setUploadStatus: (status: Partial<UploadStatus>) => void;
  
  schedulingStatus: SchedulingStatus;
  setSchedulingStatus: (status: Partial<SchedulingStatus>) => void;
  
  systemStatus: SystemStatus;
  setSystemStatus: (status: Partial<SystemStatus>) => void;
  
  settings: SettingsState;
  updateSettings: (settings: Partial<SettingsState>) => void;
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial State
        currentPage: 'dashboard',
        activeSessionId: null,
        kpiData: { 
            total_exams: 0,
            total_courses: 0,
            total_students_registered: 0,
            total_departments: 0,
            total_faculties: 0,
            total_rooms_used: 0,
            total_invigilators_assigned: 0,
            scheduling_status: {
                completed_jobs: 0,
                pending_jobs: 0,
                failed_jobs: 0,
                running_jobs: 0,
            },
            latest_timetable_version: null
        },
        exams: [],
        conflicts: [],
        rooms: [],
        uploadStatus: { 
          isUploading: false, 
          progress: 0, 
          files: {}, 
          validation: {} 
        },
        schedulingStatus: { 
          jobId: null, 
          isRunning: false, 
          phase: 'idle', 
          progress: 0, 
          metrics: {}, 
          canPause: false, 
          canCancel: false 
        },
        systemStatus: { 
          constraintEngine: 'idle', 
          autoResolution: true, 
          dataSyncProgress: 100 
        },
        settings: { 
          theme: 'light',
          constraintWeights: {
            noOverlap: 1.0,
            roomCapacity: 0.9,
            instructorAvailability: 0.8,
            studentConflicts: 0.95,
          },
          notifications: {
            email: true,
            sms: false
          }
        },
        
        // Actions
        setCurrentPage: (page) => set({ currentPage: page }),
        setActiveSessionId: (sessionId) => set({ activeSessionId: sessionId }),
        
        initializeApp: async () => {
          try {
            const response = await api.fetchAcademicSessions();
            const sessions = response.data as AcademicSession[];
            
            const activeSessions = sessions
              .filter(s => s.is_active)
              .sort((a, b) => new Date(b.start_date).getTime() - new Date(a.start_date).getTime());
              
            if (activeSessions.length > 0) {
              get().setActiveSessionId(activeSessions[0].id);
            } else {
              console.warn("No active academic session found.");
              get().setActiveSessionId(null);
            }
          } catch (error) {
            console.error("Failed to fetch academic sessions:", error);
            get().setActiveSessionId(null);
          }
        },

        setKpiData: (data) => set({ kpiData: data }),
        setExams: (exams) => set({ exams }),
        setConflicts: (conflicts) => set({ conflicts }),
        resolveConflict: (id) => set((state) => ({ 
          conflicts: state.conflicts.filter(c => c.id !== id) 
        })),
        setRooms: (rooms) => set({ rooms }),
        setUploadStatus: (status) => set((state) => ({ 
          uploadStatus: { ...state.uploadStatus, ...status } 
        })),
        setSchedulingStatus: (status) => set((state) => ({ 
          schedulingStatus: { ...state.schedulingStatus, ...status } 
        })),
        setSystemStatus: (status) => set((state) => ({ 
          systemStatus: { ...state.systemStatus, ...status } 
        })),
        updateSettings: (settings) => set((state) => ({ 
          settings: { ...state.settings, ...settings } 
        })),
      }),
      {
        name: 'exam-timetabling-store',
      }
    ),
    {
      name: 'exam-timetabling-store',
    }
  )
);