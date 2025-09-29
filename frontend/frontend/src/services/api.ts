// API Service Layer with best practices for error handling and data management

const API_BASE_URL = 'http://localhost:3001/api'

class ApiError extends Error {
  constructor(public status: number, message: string, public data?: any) {
    super(message)
    this.name = 'ApiError'
  }
}

interface ApiResponse<T> {
  data: T
  message?: string
  status: 'success' | 'error'
}

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new ApiError(
          response.status,
          errorData.message || `HTTP ${response.status}`,
          errorData
        )
      }

      const result: ApiResponse<T> = await response.json()
      
      if (result.status === 'error') {
        throw new ApiError(400, result.message || 'API Error', result)
      }

      return result.data
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network Error', error)
    }
  }

  // KPI and Dashboard APIs
  async getKPIData() {
    return this.request<{
      scheduledExams: number
      activeConflicts: number
      constraintSatisfactionRate: number
      roomUtilization: number
      studentsAffected: number
      processingTime: number
    }>('/dashboard/kpis')
  }

  async getRecentActivity() {
    return this.request<Array<{
      id: string
      type: 'upload' | 'schedule' | 'conflict' | 'export'
      message: string
      timestamp: string
      status: 'success' | 'warning' | 'error'
    }>>('/dashboard/activity')
  }

  // File Upload APIs
  async uploadFiles(files: FormData) {
    return this.request<{
      uploadId: string
      status: 'processing' | 'completed' | 'failed'
      validation: Record<string, { valid: boolean; errors: string[] }>
    }>('/upload/files', {
      method: 'POST',
      body: files,
      headers: {}, // Let browser set Content-Type for FormData
    })
  }

  async getUploadStatus(uploadId: string) {
    return this.request<{
      status: 'processing' | 'completed' | 'failed'
      progress: number
      validation: Record<string, { valid: boolean; errors: string[] }>
    }>(`/upload/status/${uploadId}`)
  }

  async validateFiles(files: FormData) {
    return this.request<{
      validation: Record<string, { valid: boolean; errors: string[] }>
      summary: {
        totalRows: number
        validRows: number
        errorRows: number
      }
    }>('/upload/validate', {
      method: 'POST',
      body: files,
      headers: {},
    })
  }

  // Scheduling APIs
  async startScheduling(constraints: any) {
    return this.request<{
      jobId: string
      status: 'started'
    }>('/scheduling/start', {
      method: 'POST',
      body: JSON.stringify({ constraints }),
    })
  }

  async getSchedulingStatus(jobId: string) {
    return this.request<{
      status: 'running' | 'completed' | 'failed' | 'paused'
      phase: 'cp-sat' | 'genetic-algorithm' | 'optimization'
      progress: number
      metrics: {
        constraintsSatisfied: number
        totalConstraints: number
        iterationsCompleted: number
        bestSolution: number
      }
    }>(`/scheduling/status/${jobId}`)
  }

  async pauseScheduling(jobId: string) {
    return this.request<{ status: 'paused' }>(`/scheduling/pause/${jobId}`, {
      method: 'POST',
    })
  }

  async cancelScheduling(jobId: string) {
    return this.request<{ status: 'cancelled' }>(`/scheduling/cancel/${jobId}`, {
      method: 'POST',
    })
  }

  // Timetable APIs
  async getTimetable() {
    return this.request<Array<{
      id: string
      courseCode: string
      courseName: string
      date: string
      timeSlot: string
      room: string
      instructor: string
      capacity: number
      studentsCount: number
      duration: number
    }>>('/timetable')
  }

  async updateExamSlot(examId: string, newSlot: { date: string; timeSlot: string; room?: string }) {
    return this.request<{ success: boolean }>(`/timetable/exam/${examId}`, {
      method: 'PUT',
      body: JSON.stringify(newSlot),
    })
  }

  async getConflicts() {
    return this.request<Array<{
      id: string
      type: 'hard' | 'soft'
      severity: 'high' | 'medium' | 'low'
      message: string
      examIds: string[]
      autoResolvable: boolean
      suggestedResolution?: {
        examId: string
        newDate?: string
        newTimeSlot?: string
        newRoom?: string
      }
    }>>('/timetable/conflicts')
  }

  async resolveConflict(conflictId: string, resolution?: any) {
    return this.request<{ success: boolean }>(`/timetable/conflicts/${conflictId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution }),
    })
  }

  async autoResolveConflicts() {
    return this.request<{
      resolved: number
      remaining: number
      conflicts: Array<{ id: string; resolution: string }>
    }>('/timetable/conflicts/auto-resolve', {
      method: 'POST',
    })
  }

  // Rooms and Resources APIs
  async getRooms() {
    return this.request<Array<{
      id: string
      name: string
      capacity: number
      type: string
      facilities: string[]
      available: boolean
      utilization?: number
    }>>('/resources/rooms')
  }

  async getInstructors() {
    return this.request<Array<{
      id: string
      name: string
      email: string
      department: string
      availableSlots: string[]
      maxExamsPerDay: number
    }>>('/resources/instructors')
  }

  // Reports APIs
  async generateReport(type: 'student' | 'room' | 'conflicts' | 'instructor', options: any) {
    return this.request<{
      reportId: string
      status: 'generating' | 'completed'
      downloadUrl?: string
    }>('/reports/generate', {
      method: 'POST',
      body: JSON.stringify({ type, options }),
    })
  }

  async getReportStatus(reportId: string) {
    return this.request<{
      status: 'generating' | 'completed' | 'failed'
      progress: number
      downloadUrl?: string
      error?: string
    }>(`/reports/status/${reportId}`)
  }

  async downloadReport(reportId: string, format: 'pdf' | 'csv' | 'excel') {
    const response = await fetch(`${API_BASE_URL}/reports/download/${reportId}?format=${format}`)
    
    if (!response.ok) {
      throw new ApiError(response.status, 'Download failed')
    }

    return response.blob()
  }

  // Settings APIs
  async getSettings() {
    return this.request<{
      constraintWeights: Record<string, number>
      systemPreferences: Record<string, any>
      userProfiles: Array<any>
    }>('/settings')
  }

  async updateSettings(settings: any) {
    return this.request<{ success: boolean }>('/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  }

  // Real-time WebSocket connection helper
  createWebSocket(endpoint: string, onMessage: (data: any) => void) {
    const wsUrl = API_BASE_URL.replace('http', 'ws') + endpoint
    const ws = new WebSocket(wsUrl)
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (error) {
        console.error('WebSocket message parse error:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    return ws
  }
}

export const apiService = new ApiService()
export { ApiError }

// Mock data generators for development
export const mockData = {
  kpiData: {
    scheduledExams: 156,
    activeConflicts: 8,
    constraintSatisfactionRate: 94.5,
    roomUtilization: 78.2,
    studentsAffected: 1247,
    processingTime: 2.3,
  },
  
  exams: [
    {
      id: '1',
      courseCode: 'MATH101',
      courseName: 'Calculus I',
      date: '2024-01-15',
      timeSlot: '09:00',
      room: 'A-101',
      instructor: 'Dr. Smith',
      capacity: 120,
      studentsCount: 95,
      duration: 180,
    },
    {
      id: '2',
      courseCode: 'PHYS201',
      courseName: 'Physics II',
      date: '2024-01-15',
      timeSlot: '09:00',
      room: 'B-203',
      instructor: 'Prof. Johnson',
      capacity: 80,
      studentsCount: 67,
      duration: 180,
    },
    // Add more mock exams as needed
  ],
  
  conflicts: [
    {
      id: 'c1',
      type: 'hard' as const,
      severity: 'high' as const,
      message: 'Student has overlapping exams: MATH101 and PHYS201',
      examIds: ['1', '2'],
      autoResolvable: true,
    },
    {
      id: 'c2',
      type: 'soft' as const,
      severity: 'medium' as const,
      message: 'Room A-101 exceeds capacity by 15 students',
      examIds: ['1'],
      autoResolvable: false,
    },
  ],
}