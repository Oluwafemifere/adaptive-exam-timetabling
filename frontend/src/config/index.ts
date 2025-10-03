// frontend/src/config/index.ts
export const config = {
  // API Configuration
  api: {
    baseUrl: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1', // Updated to match your backend
    timeout: 30000, // 30 seconds
    retryAttempts: 3,
    retryDelay: 1000, // 1 second
  },

  // WebSocket Configuration
  websocket: {
    url: import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws', // Updated WebSocket URL
    reconnectInterval: 5000,
    maxReconnectAttempts: 10,
  },

  // Application Settings
  app: {
    name: 'Adaptive Exam Timetabling System',
    version: '1.0.0',
    environment: import.meta.env.NODE_ENV || 'development',
  },

  // Timetable Configuration
  timetable: {
    // UPDATED: Define the start and end hours for the timetable view
    dayStartHour: 9, // 9 AM
    dayEndHour: 18, // 6 PM
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
    enableMockData: false, // Disabled to use live API
    enableDebugMode: import.meta.env.REACT_APP_DEBUG === 'true',
    logLevel: import.meta.env.REACT_APP_LOG_LEVEL || 'info',
  },
}

// Export individual sections for easier imports
export const { api, timetable, scheduling, upload, reports, ui, features, security, cache } = config

// Helper functions and type definitions remain the same...
export const getApiUrl = (endpoint: string): string => {
  return `${config.api.baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`
}

export const isFeatureEnabled = (feature: keyof typeof config.features): boolean => {
  return config.features[feature]
}

// Type definitions for better TypeScript support
export type ReportFormat = typeof config.reports.formats[number]
export type ConstraintWeight = keyof typeof config.scheduling.defaultConstraintWeights
export type FeatureFlag = keyof typeof config.features

export default config