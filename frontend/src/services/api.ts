// Mock API service for the exam timetabling system
// In a real application, these would be actual API calls

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

export interface KPIData {
  total_exams: number;
  total_courses: number;
  total_students_registered: number;
  total_rooms_used: number;
  scheduling_status: {
    running_jobs: number;
    failed_jobs: number;
  };
}

export interface AcademicSession {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

export interface SchedulingRequest {
  session_id: string;
  start_date: string;
  end_date: string;
  options: {
    timeLimit: number;
    populationSize: number;
    constraints: Record<string, number>;
  };
}

export interface JobUpdate {
  job_id: string;
  phase: string;
  progress: number;
  metrics: Record<string, any>;
}

// Mock data
const mockKPIData: KPIData = {
  total_exams: 152,
  total_courses: 89,
  total_students_registered: 3247,
  total_rooms_used: 23,
  scheduling_status: {
    running_jobs: 0,
    failed_jobs: 0,
  },
};

const mockSessions: AcademicSession[] = [
  {
    id: 'session-2024-1',
    name: '2024/2025 Academic Session - First Semester',
    start_date: '2024-09-01T00:00:00Z',
    end_date: '2025-01-31T23:59:59Z',
    is_active: true,
  },
  {
    id: 'session-2024-2',
    name: '2024/2025 Academic Session - Second Semester',
    start_date: '2025-02-01T00:00:00Z',
    end_date: '2025-08-31T23:59:59Z',
    is_active: false,
  },
];

const mockUsers = [
  {
    id: 'admin-1',
    name: 'Dr. Sarah Johnson',
    email: 'admin@baze.edu',
    role: 'administrator',
    department: 'Academic Administration',
  },
  {
    id: 'student-1',
    name: 'John Smith',
    email: 'student@baze.edu',
    role: 'student',
    studentId: 'STU001',
    department: 'Computer Science',
  },
  {
    id: 'staff-1',
    name: 'Prof. Michael Davis',
    email: 'staff@baze.edu',
    role: 'staff',
    staffId: 'STF001',
    department: 'Computer Science',
  },
];

export const api = {
  // Authentication
  login: async (username: string, password: string): Promise<ApiResponse<{ user: any; token: string }>> => {
    // Mock login
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // For demo purposes, we'll accept any password and route based on email
    const user = mockUsers.find(u => u.email === username);
    
    if (user) {
      return {
        success: true,
        data: {
          user,
          token: 'mock-jwt-token',
        },
      };
    } else {
      throw new Error('Invalid credentials');
    }
  },

  // KPI Data
  getKPIData: async (): Promise<ApiResponse<KPIData>> => {
    await new Promise(resolve => setTimeout(resolve, 500));
    return {
      success: true,
      data: mockKPIData,
    };
  },

  // Academic Sessions
  getAcademicSessions: async (): Promise<ApiResponse<AcademicSession[]>> => {
    await new Promise(resolve => setTimeout(resolve, 300));
    return {
      success: true,
      data: mockSessions,
    };
  },

  // File Upload
  uploadFile: async (formData: FormData, entityType: string): Promise<ApiResponse<{ message: string }>> => {
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Mock validation
    const file = formData.get('file') as File;
    if (!file) {
      throw new Error('No file provided');
    }
    
    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      throw new Error('File size too large');
    }

    return {
      success: true,
      data: {
        message: `Successfully uploaded and processed ${entityType} data (${file.name})`,
      },
    };
  },

  // Scheduling
  startScheduling: async (request: SchedulingRequest): Promise<ApiResponse<{ job_id: string }>> => {
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const jobId = `job-${Date.now()}`;
    return {
      success: true,
      data: { job_id: jobId },
    };
  },

  cancelScheduling: async (jobId: string): Promise<ApiResponse<{ message: string }>> => {
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return {
      success: true,
      data: {
        message: `Job ${jobId} cancelled successfully`,
      },
    };
  },

  // Reports
  generateReport: async (reportType: string, options: Record<string, any>): Promise<ApiResponse<{ report_id: string }>> => {
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    const reportId = `report-${Date.now()}`;
    return {
      success: true,
      data: { report_id: reportId },
    };
  },
};

// WebSocket Mock for job updates
export class MockWebSocket {
  private callbacks: { [event: string]: Function[] } = {};
  private interval: NodeJS.Timeout | null = null;
  private jobId: string;

  constructor(jobId: string) {
    this.jobId = jobId;
  }

  on(event: string, callback: Function) {
    if (!this.callbacks[event]) {
      this.callbacks[event] = [];
    }
    this.callbacks[event].push(callback);
  }

  connect() {
    // Simulate job progress updates
    let progress = 0;
    let phase = 'cp-sat';
    
    this.interval = setInterval(() => {
      progress += Math.random() * 15;
      
      if (progress >= 50 && phase === 'cp-sat') {
        phase = 'genetic-algorithm';
      }
      
      if (progress >= 100) {
        progress = 100;
        phase = 'completed';
        this.disconnect();
      }

      const update: JobUpdate = {
        job_id: this.jobId,
        phase,
        progress: Math.min(progress, 100),
        metrics: {
          hard_constraints_violations: Math.max(0, Math.floor(Math.random() * 10) - Math.floor(progress / 20)),
          soft_constraints_violations: Math.max(0, Math.floor(Math.random() * 25) - Math.floor(progress / 10)),
          fitness_score: Math.min(1, progress / 100),
          generation: phase === 'genetic-algorithm' ? Math.floor(progress - 50) : 0,
        },
      };

      this.emit('job_update', update);
    }, 1000);
  }

  disconnect() {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  private emit(event: string, data: any) {
    if (this.callbacks[event]) {
      this.callbacks[event].forEach(callback => callback(data));
    }
  }
}