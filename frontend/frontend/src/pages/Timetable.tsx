// frontend/src/pages/Timetable.tsx
import React, { useState } from 'react';
import { Loader2, AlertTriangle } from 'lucide-react';
import { useActiveTimetable, useUpdateExam } from '../hooks/useApi';
import { TimetableGrid } from '../components/timetable/TimetableGrid';
import { FilterControls } from '../components/timetable/FilterControls';
import { Button } from '../components/ui/button';

export function Timetable() {
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'general' | 'department'>('general');
  
  const { data, isLoading, error, refetch } = useActiveTimetable();
  const updateExamMutation = useUpdateExam();

  const filteredExams = React.useMemo(() => {
    if (!data?.renderableExams) return [];
    if (viewMode === 'department' && selectedDepartment === 'all') {
      return data.renderableExams;
    }
    if (selectedDepartment === 'all') {
        return data.renderableExams;
    }
    return data.renderableExams.filter(exam => 
      exam.departments.includes(selectedDepartment)
    );
  }, [selectedDepartment, data?.renderableExams, viewMode]);

  const handleMoveExam = (examId: string, newDate: string, newStartTime: string) => {
    console.log(`Attempting to move exam ${examId} to ${newDate} at ${newStartTime}`);
    updateExamMutation.mutate({ 
      examId, 
      data: { date: newDate, start_time: newStartTime } 
    });
  };
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="ml-4 text-lg">Loading Timetable...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] text-center">
        <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold text-destructive">Failed to Load Timetable</h2>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <Button onClick={() => refetch()} className="mt-4">Retry</Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold mb-4">Exam Timetable</h1>
          <FilterControls
            departments={data?.uniqueDepartments || []}
            selectedDepartment={selectedDepartment}
            onDepartmentChange={setSelectedDepartment}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        </div>
        
        <TimetableGrid 
          exams={filteredExams}
          viewMode={viewMode}
          departments={data?.uniqueDepartments || []}
          onMoveExam={handleMoveExam}
          dateRange={data?.dateRange || []}
          timeSlots={data?.timeSlots || []}
        />
      </div>
    </div>
  );
}

export default Timetable;