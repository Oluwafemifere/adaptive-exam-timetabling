// Main store index - combines all slices and provides global store configuration
import { useAuthStore } from './authSlice';
import { useSchedulingStore } from './schedulingSlice';

// Re-export all stores for easy import
export { useAuthStore, useAuth, useAuthToken, useUserRole, useUserPermissions } from './authSlice';
export { 
  useSchedulingStore, 
  useScheduling, 
  useScheduleStats, 
  useConstraints,
  type Constraint,
  type ExamSlot,
  type Conflict,
  type OptimizationProgress,
  type SchedulingState 
} from './schedulingSlice';

// Global store actions
export const resetAllStores = () => {
  // Reset auth store
  useAuthStore.getState().logout();
  
  // Reset scheduling store to initial state
  useSchedulingStore.setState({
    uploadedFiles: {},
    validationResults: {},
    schedule: [],
    conflicts: [],
    isOptimizing: false,
    optimizationProgress: null,
    optimizationHistory: [],
    selectedExam: null,
    selectedConflicts: [],
    viewMode: 'calendar',
    filters: {
      rooms: [],
      courses: [],
      timeSlots: [],
      conflictTypes: [],
    },
    isLoading: false,
    error: null,
    lastUpdated: null,
  });
};

// Global error handling
export const handleGlobalError = (error: Error) => {
  console.error('Global error:', error);
  
  // Handle authentication errors
  if (error.message.includes('unauthorized') || error.message.includes('401')) {
    useAuthStore.getState().logout();
    return;
  }
  
  // Handle network errors
  if (error.message.includes('fetch')) {
    // Could show a global network error notification
    return;
  }
  
  // Generic error handling
  // Could integrate with a notification system here
};

// Store persistence utilities
export const clearPersistedData = () => {
  try {
    localStorage.removeItem('auth-storage');
    localStorage.removeItem('scheduling-preferences');
  } catch (error) {
    console.error('Failed to clear persisted data:', error);
  }
};

// Development utilities
if (process.env.NODE_ENV === 'development') {
  // Make stores available in window for debugging
  (window as any).stores = {
    auth: useAuthStore,
    scheduling: useSchedulingStore,
  };
  
  // Add store debugging utilities
  (window as any).debugStores = {
    printAuthState: () => console.log(useAuthStore.getState()),
    printSchedulingState: () => console.log(useSchedulingStore.getState()),
    resetAll: resetAllStores,
    clearPersisted: clearPersistedData,
  };
}