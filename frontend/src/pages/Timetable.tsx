import { useState, useMemo, useEffect } from 'react';
import { TimetableGrid } from '../components/TimetableGrid';
import { FilterControls } from '../components/FilterControls';
import { ConflictPanel } from '../components/ConflictPanel';
import { mockExamData, Exam } from '../data/mockExamData';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { AlertTriangle, Grid, List } from 'lucide-react';
import { useAppStore } from '../store';
import { toast } from 'sonner';

export function Timetable() {
  const [selectedDepartments, setSelectedDepartments] = useState<string[]>([]);
  const [selectedFaculties, setSelectedFaculties] = useState<string[]>([]);
  const [selectedRooms, setSelectedRooms] = useState<string[]>([]);
  const [selectedStaff, setSelectedStaff] = useState<string[]>([]);
  const [selectedStudents, setSelectedStudents] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [viewMode, setViewMode] = useState<'general' | 'department'>('general');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [exams, setExams] = useState<Exam[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterPresets, setFilterPresets] = useState<any[]>([]);
  
  const { conflicts, user, addHistoryEntry } = useAppStore();

  // Initialize exams data
  useEffect(() => {
    try {
      if (mockExamData && Array.isArray(mockExamData)) {
        setExams(mockExamData);
      }
    } catch (error) {
      console.error('Error loading exam data:', error);
      setExams([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const departments = useMemo(() => {
    const deptSet = new Set<string>();
    if (Array.isArray(exams)) {
      exams.forEach(exam => {
        if (exam && Array.isArray(exam.departments)) {
          exam.departments.forEach(dept => deptSet.add(dept));
        }
      });
    }
    return Array.from(deptSet).sort();
  }, [exams]);

  const faculties = useMemo(() => {
    // Extract faculties from departments (simplified - in real app this would be proper data)
    return ['Engineering', 'Science', 'Arts', 'Business', 'Medicine'];
  }, []);

  const rooms = useMemo(() => {
    const roomSet = new Set<string>();
    if (Array.isArray(exams)) {
      exams.forEach(exam => {
        if (exam && exam.room) {
          roomSet.add(exam.room);
        }
      });
    }
    return Array.from(roomSet).sort();
  }, [exams]);

  const staff = useMemo(() => {
    const staffSet = new Set<string>();
    if (Array.isArray(exams)) {
      exams.forEach(exam => {
        if (exam && exam.invigilator) {
          staffSet.add(exam.invigilator);
        }
      });
    }
    return Array.from(staffSet).sort();
  }, [exams]);

  const students = useMemo(() => {
    // Mock student data - in real app this would come from enrollment data
    return ['John Smith', 'Emma Johnson', 'Michael Brown', 'Sarah Wilson', 'David Lee'];
  }, []);

  const filteredExams = useMemo(() => {
    if (!Array.isArray(exams)) return [];
    
    return exams.filter(exam => {
      if (!exam) return false;

      // Department filter
      if (selectedDepartments.length > 0) {
        const hasMatchingDept = exam.departments.some(dept => 
          selectedDepartments.includes(dept)
        );
        if (!hasMatchingDept) return false;
      }

      // Room filter
      if (selectedRooms.length > 0 && !selectedRooms.includes(exam.room)) {
        return false;
      }

      // Staff filter
      if (selectedStaff.length > 0 && !selectedStaff.includes(exam.invigilator)) {
        return false;
      }

      // Search term filter
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        const searchableText = [
          exam.courseCode,
          exam.courseName,
          exam.room,
          exam.building,
          exam.invigilator,
          ...exam.departments
        ].join(' ').toLowerCase();
        
        if (!searchableText.includes(term)) return false;
      }

      return true;
    });
  }, [selectedDepartments, selectedRooms, selectedStaff, searchTerm, exams]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg">Loading exam timetable...</div>
        </div>
      </div>
    );
  }

  const handleMoveExam = (examId: string, newDate: string, newStartTime: string) => {
    console.log('Moving exam:', examId, 'to', newDate, newStartTime);
    setExams(prevExams => 
      prevExams.map(exam => {
        if (exam.id === examId) {
          // Calculate duration to maintain exam length
          const start = new Date(`1970-01-01T${exam.startTime}:00`);
          const end = new Date(`1970-01-01T${exam.endTime}:00`);
          const durationMs = end.getTime() - start.getTime();
          
          const newStart = new Date(`1970-01-01T${newStartTime}:00`);
          const newEnd = new Date(newStart.getTime() + durationMs);
          
          const newEndTime = newEnd.toTimeString().slice(0, 5);
          
          // Add to history
          addHistoryEntry({
            action: 'Moved exam',
            entityType: 'exam',
            entityId: examId,
            userId: user?.id || '',
            userName: user?.name || '',
            details: {
              courseCode: exam.courseCode,
              from: { date: exam.date, startTime: exam.startTime },
              to: { date: newDate, startTime: newStartTime }
            }
          });
          
          toast.success(`Moved ${exam.courseCode} to ${newDate} at ${newStartTime}`);
          
          return {
            ...exam,
            date: newDate,
            startTime: newStartTime,
            endTime: newEndTime
          };
        }
        return exam;
      })
    );
  };

  const handleSavePreset = (preset: any) => {
    const newPreset = {
      ...preset,
      id: `preset_${Date.now()}`
    };
    setFilterPresets(prev => [...prev, newPreset]);
    toast.success(`Saved filter preset: ${preset.name}`);
  };

  const handleLoadPreset = (preset: any) => {
    setSelectedDepartments(preset.departments || []);
    setSelectedFaculties(preset.faculties || []);
    setSelectedRooms(preset.rooms || []);
    setSelectedStaff(preset.staff || []);
    setSearchTerm(preset.searchTerm || '');
    toast.success(`Loaded filter preset: ${preset.name}`);
  };

  const handleResolveConflict = (conflictId: string) => {
    // Mock conflict resolution
    toast.success('Conflict resolved successfully');
    addHistoryEntry({
      action: 'Resolved conflict',
      entityType: 'schedule',
      entityId: conflictId,
      userId: user?.id || '',
      userName: user?.name || '',
      details: { conflictId }
    });
  };

  const handleAutoResolve = () => {
    // This would be handled by the ConflictPanel component
    console.log('Auto-resolving conflicts...');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Exam Timetable</h2>
          <p className="text-muted-foreground">
            {filteredExams.length} of {exams.length} exams shown
            {conflicts.length > 0 && (
              <span className="text-destructive ml-2">
                • {conflicts.length} conflict{conflicts.length !== 1 ? 's' : ''} detected
              </span>
            )}
          </p>
        </div>
        
        {conflicts.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            className="text-destructive border-destructive"
          >
            <AlertTriangle className="h-4 w-4 mr-2" />
            {conflicts.length} Conflict{conflicts.length !== 1 ? 's' : ''}
          </Button>
        )}
      </div>

      <FilterControls
        departments={departments}
        selectedDepartments={selectedDepartments}
        onDepartmentsChange={setSelectedDepartments}
        faculties={faculties}
        selectedFaculties={selectedFaculties}
        onFacultiesChange={setSelectedFaculties}
        rooms={rooms}
        selectedRooms={selectedRooms}
        onRoomsChange={setSelectedRooms}
        staff={staff}
        selectedStaff={selectedStaff}
        onStaffChange={setSelectedStaff}
        students={students}
        selectedStudents={selectedStudents}
        onStudentsChange={setSelectedStudents}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        showAdvancedFilters={showAdvancedFilters}
        onAdvancedFiltersToggle={() => setShowAdvancedFilters(!showAdvancedFilters)}
        filterPresets={filterPresets}
        onSavePreset={handleSavePreset}
        onLoadPreset={handleLoadPreset}
      />

      <Tabs defaultValue="timetable" className="space-y-4">
        <TabsList>
          <TabsTrigger value="timetable" className="flex items-center gap-2">
            <Grid className="h-4 w-4" />
            Timetable View
          </TabsTrigger>
          {conflicts.length > 0 && (
            <TabsTrigger value="conflicts" className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Conflicts ({conflicts.length})
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="timetable">
          <TimetableGrid 
            exams={filteredExams}
            viewMode={viewMode}
            departments={departments}
            onMoveExam={handleMoveExam}
          />
        </TabsContent>

        {conflicts.length > 0 && (
          <TabsContent value="conflicts">
            <ConflictPanel
              conflicts={conflicts}
              onResolveConflict={handleResolveConflict}
              onAutoResolve={handleAutoResolve}
              onExportReport={() => {}}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}