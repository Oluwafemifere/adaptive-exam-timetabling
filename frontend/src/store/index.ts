import { create } from 'zustand';
import { AppState } from './types';

export const useAppStore = create<AppState>()((set, get) => ({
      // Navigation
      currentPage: 'dashboard',
      
      // Authentication
      isAuthenticated: false,
      user: null,
      
      // Data
      exams: [],
      conflicts: [],
      activeSessionId: null,
      
      // Role-specific data
      studentExams: [],
      staffAssignments: [],
      conflictReports: [],
      changeRequests: [],
      
      // Admin features
      notifications: [],
      history: [],
      jobResults: [],
      filterOptions: {
        departments: [],
        faculties: [],
        rooms: [],
        students: [],
        staff: [],
        dateRange: {
          start: '',
          end: ''
        },
        timeSlots: [],
        examTypes: []
      },
      
      // Status
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
      
      // Settings
      settings: {
        theme: 'light',
        constraintWeights: {
          noOverlap: 1.0,
          roomCapacity: 0.9,
          instructorAvailability: 0.8,
          studentConflicts: 0.95,
        },
        notifications: {
          emailNotifications: true,
          conflictAlerts: true,
          schedulingUpdates: true,
        },
      },
      
      // Actions
      setCurrentPage: (page) => set({ currentPage: page }),
      
      setAuthenticated: (isAuth, user = null) => 
        set({ isAuthenticated: isAuth, user }),
      
      setExams: (exams) => set({ exams }),
      
      setConflicts: (conflicts) => set({ conflicts }),
      
      setSystemStatus: (status) => 
        set((state) => ({
          systemStatus: { ...state.systemStatus, ...status }
        })),
      
      setSchedulingStatus: (status) =>
        set((state) => ({
          schedulingStatus: { ...state.schedulingStatus, ...status }
        })),
      
      setUploadStatus: (status) =>
        set((state) => ({
          uploadStatus: { ...state.uploadStatus, ...status }
        })),
      
      updateSettings: (newSettings) =>
        set((state) => ({
          settings: { ...state.settings, ...newSettings }
        })),
      
      setStudentExams: (exams) => set({ studentExams: exams }),
      
      setStaffAssignments: (assignments) => set({ staffAssignments: assignments }),
      
      addConflictReport: (report) =>
        set((state) => {
          const newReport = {
            ...report,
            id: `report-${Date.now()}`,
            status: 'pending' as const,
            submittedAt: new Date().toISOString(),
          };
          
          // Add notification for admin
          const notification = {
            type: 'conflict_report' as const,
            title: 'New Conflict Report',
            message: `Student conflict reported for ${report.courseCode}`,
            priority: 'medium' as const,
            isRead: false,
            relatedId: newReport.id,
            actionRequired: true,
          };
          
          return {
            conflictReports: [...state.conflictReports, newReport],
            notifications: [
              ...state.notifications,
              {
                ...notification,
                id: `notif-${Date.now()}`,
                createdAt: new Date().toISOString(),
              }
            ]
          };
        }),
      
      addChangeRequest: (request) =>
        set((state) => {
          const newRequest = {
            ...request,
            id: `request-${Date.now()}`,
            status: 'pending' as const,
            submittedAt: new Date().toISOString(),
          };
          
          // Add notification for admin
          const notification = {
            type: 'change_request' as const,
            title: 'New Change Request',
            message: `Staff change request for ${request.courseCode}`,
            priority: 'medium' as const,
            isRead: false,
            relatedId: newRequest.id,
            actionRequired: true,
          };
          
          return {
            changeRequests: [...state.changeRequests, newRequest],
            notifications: [
              ...state.notifications,
              {
                ...notification,
                id: `notif-${Date.now()}`,
                createdAt: new Date().toISOString(),
              }
            ]
          };
        }),
      
      updateConflictReportStatus: (id, status) =>
        set((state) => ({
          conflictReports: state.conflictReports.map(report =>
            report.id === id ? { ...report, status } : report
          )
        })),
      
      updateChangeRequestStatus: (id, status) =>
        set((state) => ({
          changeRequests: state.changeRequests.map(request =>
            request.id === id ? { ...request, status } : request
          )
        })),
      
      // Admin actions
      addNotification: (notification) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            {
              ...notification,
              id: `notif-${Date.now()}`,
              createdAt: new Date().toISOString(),
            }
          ]
        })),
      
      markNotificationAsRead: (id) =>
        set((state) => ({
          notifications: state.notifications.map(notif =>
            notif.id === id ? { ...notif, isRead: true } : notif
          )
        })),
      
      clearNotifications: () => set({ notifications: [] }),
      
      addHistoryEntry: (entry) =>
        set((state) => ({
          history: [
            {
              ...entry,
              id: `history-${Date.now()}`,
              timestamp: new Date().toISOString(),
            },
            ...state.history
          ]
        })),
      
      addJobResult: (result) =>
        set((state) => ({
          jobResults: [result, ...state.jobResults]
        })),
      
      updateFilterOptions: (options) =>
        set((state) => ({
          filterOptions: { ...state.filterOptions, ...options }
        })),
      
      // Scheduling actions
      startSchedulingJob: async (sessionId) => {
        const jobId = `job-${Date.now()}`;
        const startTime = new Date().toISOString();
        
        set((state) => ({
          schedulingStatus: {
            ...state.schedulingStatus,
            isRunning: true,
            phase: 'cp-sat',
            progress: 0,
            jobId,
            startTime,
            canPause: true,
            canResume: false,
            canCancel: true,
            metrics: {
              processed_exams: 0,
              total_exams: state.exams.length,
            }
          }
        }));
        
        // Mock scheduling job with WebSocket-like updates
        return new Promise((resolve) => {
          let progress = 0;
          const interval = setInterval(() => {
            progress += Math.random() * 10;
            
            if (progress >= 100) {
              clearInterval(interval);
              
              // Job completed successfully
              set((state) => ({
                schedulingStatus: {
                  ...state.schedulingStatus,
                  isRunning: false,
                  phase: 'completed',
                  progress: 100,
                  canPause: false,
                  canResume: false,
                  canCancel: false,
                  metrics: {
                    ...state.schedulingStatus.metrics,
                    processed_exams: state.exams.length,
                    hard_constraints_violations: 0,
                    soft_constraints_violations: 2,
                    fitness_score: 98.5,
                  }
                }
              }));
              
              // Add notification
              get().addNotification({
                type: 'job_completed',
                title: 'Scheduling Job Completed',
                message: 'Exam timetable has been successfully generated',
                priority: 'high',
                isRead: false,
                actionRequired: false,
              });
              
              resolve();
            } else {
              set((state) => ({
                schedulingStatus: {
                  ...state.schedulingStatus,
                  progress: Math.min(progress, 100),
                  phase: progress > 50 ? 'genetic-algorithm' : 'cp-sat',
                  metrics: {
                    ...state.schedulingStatus.metrics,
                    processed_exams: Math.floor((progress / 100) * state.exams.length),
                    generation: progress > 50 ? Math.floor(progress - 50) : undefined,
                  }
                }
              }));
            }
          }, 500);
        });
      },
      
      pauseSchedulingJob: () =>
        set((state) => ({
          schedulingStatus: {
            ...state.schedulingStatus,
            canPause: false,
            canResume: true,
          }
        })),
      
      resumeSchedulingJob: () =>
        set((state) => ({
          schedulingStatus: {
            ...state.schedulingStatus,
            canPause: true,
            canResume: false,
          }
        })),
      
      cancelSchedulingJob: () =>
        set((state) => ({
          schedulingStatus: {
            ...state.schedulingStatus,
            isRunning: false,
            phase: 'cancelled',
            canPause: false,
            canResume: false,
            canCancel: false,
          }
        })),
      
      initializeApp: async () => {
        // Mock initialization - in real app would fetch active session
        const mockSession = {
          id: 'session-2024-1',
          name: '2024/2025 Academic Session',
          start_date: '2024-09-01T00:00:00Z',
          end_date: '2025-08-31T23:59:59Z',
          is_active: true
        };
        
        set({ 
          activeSessionId: mockSession.id,
          systemStatus: {
            constraintEngine: 'active',
            autoResolution: true,
            dataSyncProgress: 100,
          }
        });
      },
    }));