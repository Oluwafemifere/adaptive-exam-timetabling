// Configuration file for the Adaptive Exam Timetabling System

export const config = {
  // API Configuration
  api: {
    baseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:3001/api',
    timeout: 30000, // 30 seconds
    retryAttempts: 3,
    retryDelay: 1000, // 1 second
  },

  // WebSocket Configuration
  websocket: {
    url: process.env.REACT_APP_WS_URL || 'ws://localhost:3001/ws',
    reconnectInterval: 5000,
    maxReconnectAttempts: 10,
  },

  // Application Settings
  app: {
    name: 'Adaptive Exam Timetabling System',
    version: '1.0.0',
    environment: process.env.NODE_ENV || 'development',
  },

  // Timetable Configuration
  timetable: {
    timeSlots: ['09:00', '12:00', '15:00', '18:00'],
    examDurations: [120, 180, 240], // minutes
    maxExamsPerSlot: 10,
    minBreakBetweenExams: 30, // minutes
  },

  // Scheduling Configuration  
  scheduling: {
    maxIterations: 10000,
    defaultTimeLimit: 300, // 5 minutes in seconds
    populationSize: 50,
    mutationRate: 0.1,
    crossoverRate: 0.8,
    
    // Constraint weights (defaults)
    defaultConstraintWeights: {
      noOverlap: 1.0,
      roomCapacity: 0.9,
      instructorAvailability: 0.8,
      studentConflicts: 0.95,
    },
  },

  // File Upload Configuration
  upload: {
    maxFileSize: 10 * 1024 * 1024, // 10MB
    allowedFormats: ['.csv', '.json'],
    requiredFiles: ['students', 'courses', 'registrations', 'rooms'],
    optionalFiles: ['invigilators', 'constraints'],
  },

  // Report Configuration
  reports: {
    formats: ['pdf', 'csv', 'excel', 'json'],
    maxReportHistory: 50,
    reportRetentionDays: 30,
  },

  // UI Configuration
  ui: {
    theme: {
      colors: {
        primary: '#1e40af', // Deep blue
        secondary: '#059669', // Emerald  
        warning: '#d97706', // Amber
        error: '#dc2626', // Red
      },
      spacing: {
        unit: 8, // 8px base spacing unit
      },
      borderRadius: 6, // 6px border radius
      grid: {
        columns: 12,
      },
    },
    
    // Performance settings
    performance: {
      virtualScrollThreshold: 100,
      debounceDelay: 300,
      animationDuration: 200,
    },
  },

  // Feature Flags
  features: {
    realTimeUpdates: true,
    advancedConflictResolution: true,
    multipleAlgorithms: true,
    exportToMultipleFormats: true,
    userProfiles: true,
    auditLog: true,
  },

  // Security Configuration  
  security: {
    sessionTimeout: 30 * 60 * 1000, // 30 minutes
    maxLoginAttempts: 5,
    lockoutDuration: 15 * 60 * 1000, // 15 minutes
  },

  // Cache Configuration
  cache: {
    queryStaleTime: 5 * 60 * 1000, // 5 minutes
    queryCacheTime: 10 * 60 * 1000, // 10 minutes
    maxCacheSize: 50 * 1024 * 1024, // 50MB
  },

  // Notification Configuration
  notifications: {
    position: 'top-right' as const,
    duration: 5000, // 5 seconds
    maxVisible: 3,
  },

  // Development Configuration
  development: {
    enableMockData: process.env.NODE_ENV === 'development',
    enableDebugMode: process.env.REACT_APP_DEBUG === 'true',
    logLevel: process.env.REACT_APP_LOG_LEVEL || 'info',
  },
}

// Export individual sections for easier imports
export const { api, timetable, scheduling, upload, reports, ui, features, security, cache } = config

// Validation functions
export const validateConfig = () => {
  const requiredEnvVars = []
  
  if (config.app.environment === 'production') {
    if (!process.env.REACT_APP_API_BASE_URL) {
      requiredEnvVars.push('REACT_APP_API_BASE_URL')
    }
  }
  
  if (requiredEnvVars.length > 0) {
    throw new Error(`Missing required environment variables: ${requiredEnvVars.join(', ')}`)
  }
  
  return true
}

// Helper functions
export const getApiUrl = (endpoint: string): string => {
  return `${config.api.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`
}

export const isFeatureEnabled = (feature: keyof typeof config.features): boolean => {
  return config.features[feature]
}

export const getTimeSlotDuration = (): number => {
  // Calculate duration between time slots (assumes equal intervals)
  if (config.timetable.timeSlots.length < 2) return 180 // default 3 hours
  
  const first = config.timetable.timeSlots[0]
  const second = config.timetable.timeSlots[1]
  
  const firstMinutes = parseInt(first.split(':')[0]) * 60 + parseInt(first.split(':')[1])
  const secondMinutes = parseInt(second.split(':')[0]) * 60 + parseInt(second.split(':')[1])
  
  return secondMinutes - firstMinutes
}

export const formatTimeSlot = (timeSlot: string): string => {
  const [hours, minutes] = timeSlot.split(':')
  const hour = parseInt(hours)
  const period = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
  
  return `${displayHour}:${minutes} ${period}`
}

// Type definitions for better TypeScript support
export type TimeSlot = typeof config.timetable.timeSlots[number]
export type ReportFormat = typeof config.reports.formats[number]
export type ConstraintWeight = keyof typeof config.scheduling.defaultConstraintWeights
export type FeatureFlag = keyof typeof config.features

export default config