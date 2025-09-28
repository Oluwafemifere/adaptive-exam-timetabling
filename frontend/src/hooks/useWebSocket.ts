import { useCallback } from 'react';
import { useScheduling, useConstraints } from '../store';
import { schedulingApi } from '../services/scheduling';
import type { Constraint, ExamSlot, OptimizationRequest } from '../store/schedulingSlice';

// Types
export interface UseSchedulingOptions {
  autoRefreshInterval?: number;
  enableRealTimeUpdates?: boolean;
  conflictResolutionStrategy?: 'minimal_change' | 'optimal_solution' | 'greedy';
}

export interface UseSchedulingReturn {
  // State from store
  schedule: ExamSlot[];
  conflicts: any[];
  isOptimizing: boolean;
  optimizationProgress: any;
  constraints: Constraint[];
  error: string | null;
  
  // Optimization actions
  startOptimization: (request?: Partial<OptimizationRequest>) => Promise<void>;
  stopOptimization: () => void;
  
  // Schedule manipulation
  moveExam: (examId: string, newDate: string, newTimeSlot: string, newRoom?: string) => Promise<void>;
  updateExam: (examId: string, updates: Partial<ExamSlot>) => Promise<void>;
  bulkUpdateExams: (updates: Array<{ examId: string; changes: Partial<ExamSlot> }>) => Promise<void>;
  
  // Conflict resolution
  resolveConflict: (conflictId: string, resolution?: any) => Promise<void>;
  autoResolveConflicts: (conflictIds: string[], strategy?: string) => Promise<void>;
  getConflictSuggestions: (conflictId: string) => Promise<any>;
  
  // Data management
  refreshSchedule: () => Promise<void>;
  exportSchedule: (format: string) => Promise<void>;
  
  // Template management
  saveAsTemplate: (name: string, description: string) => Promise<void>;
  loadTemplate: (templateId: string) => Promise<void>;
  
  // Utility functions
  validateSchedule: () => Promise<any>;
  getScheduleStatistics: () => Promise<any>;
  compareWithPrevious: (previousScheduleId: string) => Promise<any>;
}

export const useScheduling = (options: UseSchedulingOptions = {}): UseSchedulingReturn => {
  const {
    autoRefreshInterval = 30000, // 30 seconds
    enableRealTimeUpdates = true,
    conflictResolutionStrategy = 'minimal_change',
  } = options;

  // Get state and actions from store
  const {
    schedule,
    conflicts,
    isOptimizing,
    optimizationProgress,
    error,
    startOptimization: storeStartOptimization,
    stopOptimization: storeStopOptimization,
    moveExam: storeMoveExam,
    clearError,
  } = useScheduling();

  const { constraints, updateConstraint } = useConstraints();

  // Start optimization with enhanced options
  const startOptimization = useCallback(async (request: Partial<OptimizationRequest> = {}) => {
    try {
      clearError();
      
      const optimizationRequest: OptimizationRequest = {
        constraints: constraints.filter(c => c.enabled),
        parameters: {
          maxTimeMinutes: 30,
          populationSize: 50,
          maxGenerations: 100,
          mutationRate: 0.1,
          crossoverRate: 0.8,
          ...request.parameters,
        },
        ...request,
      };

      await storeStartOptimization();
      
      // Start the actual optimization on the backend
      const response = await schedulingApi.startOptimization(optimizationRequest);
      
      // The WebSocket connection will handle progress updates
      return response;
      
    } catch (error) {
      console.error('Failed to start optimization:', error);
      throw error;
    }
  }, [constraints, storeStartOptimization, clearError]);

  // Stop optimization
  const stopOptimization = useCallback(() => {
    storeStopOptimization();
    // The API call to stop is handled in the store
  }, [storeStopOptimization]);

  // Move exam with validation
  const moveExam = useCallback(async (
    examId: string,
    newDate: string,
    newTimeSlot: string,
    newRoom?: string
  ) => {
    try {
      await storeMoveExam(examId, newDate, newTimeSlot, newRoom);
    } catch (error) {
      console.error('Failed to move exam:', error);
      throw error;
    }
  }, [storeMoveExam]);

  // Update single exam
  const updateExam = useCallback(async (examId: string, updates: Partial<ExamSlot>) => {
    try {
      await schedulingApi.updateExam(examId, updates);
      // The store will be updated via WebSocket or manual refresh
    } catch (error) {
      console.error('Failed to update exam:', error);
      throw error;
    }
  }, []);

  // Bulk update exams
  const bulkUpdateExams = useCallback(async (
    updates: Array<{ examId: string; changes: Partial<ExamSlot> }>
  ) => {
    try {
      await schedulingApi.bulkUpdateExams({ updates });
      // Refresh the schedule after bulk update
      await refreshSchedule();
    } catch (error) {
      console.error('Failed to bulk update exams:', error);
      throw error;
    }
  }, []);

  // Resolve conflict
  const resolveConflict = useCallback(async (conflictId: string, resolution?: any) => {
    try {
      await schedulingApi.resolveConflict(conflictId, resolution);
      // The store will be updated via the API call in schedulingSlice
    } catch (error) {
      console.error('Failed to resolve conflict:', error);
      throw error;
    }
  }, []);

  // Auto-resolve conflicts
  const autoResolveConflicts = useCallback(async (
    conflictIds: string[],
    strategy: string = conflictResolutionStrategy
  ) => {
    try {
      const result = await schedulingApi.autoResolveConflicts(conflictIds, strategy as any);
      
      // Refresh schedule to reflect changes
      await refreshSchedule();
      
      return result;
    } catch (error) {
      console.error('Failed to auto-resolve conflicts:', error);
      throw error;
    }
  }, [conflictResolutionStrategy]);

  // Get conflict suggestions
  const getConflictSuggestions = useCallback(async (conflictId: string) => {
    try {
      return await schedulingApi.getConflictSuggestions(conflictId);
    } catch (error) {
      console.error('Failed to get conflict suggestions:', error);
      throw error;
    }
  }, []);

  // Refresh schedule data
  const refreshSchedule = useCallback(async () => {
    try {
      const [scheduleData, conflictsData] = await Promise.all([
        schedulingApi.getSchedules(),
        schedulingApi.getConflicts(),
      ]);

      // Update store with fresh data
      useSchedulingStore.getState().setSchedule(scheduleData);
      useSchedulingStore.getState().setConflicts(conflictsData);
      
    } catch (error) {
      console.error('Failed to refresh schedule:', error);
      throw error;
    }
  }, []);

  // Export schedule
  const exportSchedule = useCallback(async (format: string) => {
    try {
      await useSchedulingStore.getState().exportSchedule(format);
    } catch (error) {
      console.error('Failed to export schedule:', error);
      throw error;
    }
  }, []);

  // Save current configuration as template
  const saveAsTemplate = useCallback(async (name: string, description: string) => {
    try {
      await schedulingApi.saveScheduleTemplate(
        name,
        description,
        constraints,
        {
          // Add any additional parameters here
          dateRange: useSchedulingStore.getState().dateRange,
          filters: useSchedulingStore.getState().filters,
        }
      );
    } catch (error) {
      console.error('Failed to save template:', error);
      throw error;
    }
  }, [constraints]);

  // Load template
  const loadTemplate = useCallback(async (templateId: string) => {
    try {
      const templates = await schedulingApi.getScheduleTemplates();
      const template = templates.find(t => t.id === templateId);
      
      if (!template) {
        throw new Error('Template not found');
      }

      // Update constraints with template values
      template.constraints.forEach(constraint => {
        updateConstraint(constraint.id, constraint);
      });

      // Apply template to current schedule if it exists
      const scheduleId = 'current'; // This would be dynamic in a real app
      await schedulingApi.applyScheduleTemplate(templateId, scheduleId);
      
    } catch (error) {
      console.error('Failed to load template:', error);
      throw error;
    }
  }, [updateConstraint]);

  // Validate current schedule
  const validateSchedule = useCallback(async () => {
    try {
      // This would call a validation endpoint
      const validation = await schedulingApi.getConflicts();
      return {
        isValid: validation.length === 0,
        conflicts: validation,
        warnings: validation.filter(c => c.severity === 'low'),
        errors: validation.filter(c => c.severity === 'critical'),
      };
    } catch (error) {
      console.error('Failed to validate schedule:', error);
      throw error;
    }
  }, []);

  // Get schedule statistics
  const getScheduleStatistics = useCallback(async () => {
    try {
      const scheduleId = 'current'; // This would be dynamic
      return await schedulingApi.getScheduleStatistics(scheduleId);
    } catch (error) {
      console.error('Failed to get schedule statistics:', error);
      throw error;
    }
  }, []);

  // Compare with previous schedule
  const compareWithPrevious = useCallback(async (previousScheduleId: string) => {
    try {
      const currentScheduleId = 'current'; // This would be dynamic
      return await schedulingApi.compareSchedules([currentScheduleId, previousScheduleId]);
    } catch (error) {
      console.error('Failed to compare schedules:', error);
      throw error;
    }
  }, []);

  return {
    // State
    schedule,
    conflicts,
    isOptimizing,
    optimizationProgress,
    constraints,
    error,
    
    // Actions
    startOptimization,
    stopOptimization,
    moveExam,
    updateExam,
    bulkUpdateExams,
    resolveConflict,
    autoResolveConflicts,
    getConflictSuggestions,
    refreshSchedule,
    exportSchedule,
    saveAsTemplate,
    loadTemplate,
    validateSchedule,
    getScheduleStatistics,
    compareWithPrevious,
  };
};