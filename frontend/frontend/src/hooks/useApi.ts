import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiService, mockData } from '../services/api'
import { useAppStore } from '../store'
import { toast } from 'sonner'

// Custom hook for KPI data
export function useKPIData() {
  return useQuery({
    queryKey: ['kpi-data'],
    queryFn: async () => {
      // Use mock data for development
      return mockData.kpiData
    },
    refetchInterval: 30000, // Refresh every 30 seconds
    onSuccess: (data) => {
      useAppStore.getState().setKpiData(data)
    },
  })
}

// Custom hook for timetable data
export function useTimetable() {
  return useQuery({
    queryKey: ['timetable'],
    queryFn: async () => {
      // Use mock data for development
      return mockData.exams
    },
    onSuccess: (data) => {
      useAppStore.getState().setExams(data)
    },
  })
}

// Custom hook for conflicts
export function useConflicts() {
  return useQuery({
    queryKey: ['conflicts'],
    queryFn: async () => {
      // Use mock data for development
      return mockData.conflicts
    },
    onSuccess: (data) => {
      useAppStore.getState().setConflicts(data)
    },
  })
}

// Custom hook for file upload
export function useFileUpload() {
  const queryClient = useQueryClient()
  const { setUploadStatus } = useAppStore()

  return useMutation({
    mutationFn: async (files: FormData) => {
      setUploadStatus({ isUploading: true, progress: 0 })
      
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadStatus((prev) => ({
          progress: Math.min(prev.progress + 10, 90)
        }))
      }, 500)

      try {
        // Mock validation response
        const result = {
          uploadId: Math.random().toString(36).substr(2, 9),
          status: 'completed' as const,
          validation: {
            students: { valid: true, errors: [] },
            courses: { valid: true, errors: [] },
            registrations: { valid: true, errors: [] },
            rooms: { valid: true, errors: [] },
            invigilators: { valid: true, errors: [] },
            constraints: { valid: true, errors: [] },
          }
        }

        clearInterval(progressInterval)
        setUploadStatus({ progress: 100, isUploading: false })
        
        return result
      } catch (error) {
        clearInterval(progressInterval)
        setUploadStatus({ isUploading: false, progress: 0 })
        throw error
      }
    },
    onSuccess: () => {
      toast.success('Files uploaded successfully!')
      queryClient.invalidateQueries({ queryKey: ['timetable'] })
    },
    onError: (error: any) => {
      toast.error(`Upload failed: ${error.message}`)
      setUploadStatus({ isUploading: false, progress: 0 })
    },
  })
}

// Custom hook for scheduling
export function useScheduling() {
  const queryClient = useQueryClient()
  const { setSchedulingStatus } = useAppStore()

  const startScheduling = useMutation({
    mutationFn: async (constraints: any) => {
      setSchedulingStatus({
        isRunning: true,
        phase: 'cp-sat',
        progress: 0,
        canPause: true,
        canCancel: true,
      })

      // Simulate scheduling process
      return new Promise((resolve) => {
        let progress = 0
        const interval = setInterval(() => {
          progress += 5
          
          if (progress === 50) {
            setSchedulingStatus({ phase: 'genetic-algorithm' })
          }
          
          setSchedulingStatus({
            progress,
            metrics: {
              constraintsSatisfied: Math.floor((progress / 100) * 45),
              totalConstraints: 45,
              iterationsCompleted: Math.floor((progress / 100) * 1000),
              bestSolution: Math.max(0, 100 - progress / 2),
            }
          })

          if (progress >= 100) {
            clearInterval(interval)
            setSchedulingStatus({
              isRunning: false,
              phase: 'completed',
              progress: 100,
              canPause: false,
              canCancel: false,
            })
            resolve({ jobId: 'mock-job-id', status: 'completed' })
          }
        }, 1000)
      })
    },
    onSuccess: () => {
      toast.success('Scheduling completed successfully!')
      queryClient.invalidateQueries({ queryKey: ['timetable'] })
      queryClient.invalidateQueries({ queryKey: ['conflicts'] })
    },
    onError: (error: any) => {
      toast.error(`Scheduling failed: ${error.message}`)
      setSchedulingStatus({
        isRunning: false,
        phase: 'error',
        canPause: false,
        canCancel: false,
      })
    },
  })

  return {
    startScheduling,
    pauseScheduling: () => {
      setSchedulingStatus({ isRunning: false, canPause: false })
      toast.info('Scheduling paused')
    },
    cancelScheduling: () => {
      setSchedulingStatus({
        isRunning: false,
        phase: 'idle',
        progress: 0,
        canPause: false,
        canCancel: false,
      })
      toast.info('Scheduling cancelled')
    },
  }
}

// Custom hook for exam slot updates (drag & drop)
export function useUpdateExamSlot() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ examId, newSlot }: {
      examId: string
      newSlot: { date: string; timeSlot: string; room?: string }
    }) => {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 500))
      return { success: true }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['timetable'] })
      queryClient.invalidateQueries({ queryKey: ['conflicts'] })
      toast.success('Exam slot updated successfully!')
    },
    onError: (error: any) => {
      toast.error(`Failed to update exam slot: ${error.message}`)
    },
  })
}

// Custom hook for conflict resolution
export function useResolveConflict() {
  const queryClient = useQueryClient()
  const { resolveConflict } = useAppStore()

  return useMutation({
    mutationFn: async ({ conflictId, resolution }: {
      conflictId: string
      resolution?: any
    }) => {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      return { success: true }
    },
    onSuccess: (_, variables) => {
      resolveConflict(variables.conflictId)
      queryClient.invalidateQueries({ queryKey: ['conflicts'] })
      queryClient.invalidateQueries({ queryKey: ['timetable'] })
      toast.success('Conflict resolved successfully!')
    },
    onError: (error: any) => {
      toast.error(`Failed to resolve conflict: ${error.message}`)
    },
  })
}

// Custom hook for report generation
export function useGenerateReport() {
  return useMutation({
    mutationFn: async ({ type, options }: {
      type: 'student' | 'room' | 'conflicts' | 'instructor'
      options: any
    }) => {
      // Mock report generation
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      return {
        reportId: Math.random().toString(36).substr(2, 9),
        status: 'completed' as const,
        downloadUrl: `#download-${type}-report`,
      }
    },
    onSuccess: (data) => {
      toast.success('Report generated successfully!', {
        action: {
          label: 'Download',
          onClick: () => {
            // Mock download
            toast.info('Download started...')
          },
        },
      })
    },
    onError: (error: any) => {
      toast.error(`Report generation failed: ${error.message}`)
    },
  })
}

// Custom hook for real-time updates
export function useRealTimeUpdates() {
  const { setSystemStatus } = useAppStore()

  // Mock real-time status updates
  React.useEffect(() => {
    const interval = setInterval(() => {
      setSystemStatus({
        constraintEngine: Math.random() > 0.1 ? 'active' : 'idle',
        dataSyncProgress: Math.random() * 100,
      })
    }, 5000)

    return () => clearInterval(interval)
  }, [setSystemStatus])
}