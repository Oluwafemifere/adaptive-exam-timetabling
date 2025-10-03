import { useState, useMemo, useEffect } from 'react';
import { TimetableGrid } from '../components/TimetableGrid';
import { FilterControls } from '../components/FilterControls';
import { ConflictPanel } from '../components/ConflictPanel';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { AlertTriangle, Grid, Loader2, Calendar, User, MapPin } from 'lucide-react';
import { useAppStore } from '../store';
import { toast } from 'sonner';
import { useLatestTimetable } from '../hooks/useApi';
import { RenderableExam } from '../store/types';

// A simple card to display exam details in list views
const ExamDetailsCard = ({ exam }: { exam: RenderableExam }) => (
  <div className="p-3 border rounded-md bg-card hover:bg-muted/50">
    <div className="font-semibold">{exam.courseCode} - {exam.courseName}</div>
    <div className="text-sm text-muted-foreground">
      {new Date(exam.date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
      {' @ '}{exam.startTime} - {exam.endTime}
    </div>
    <div className="text-xs text-muted-foreground mt-1">
      Room: {exam.room} ({exam.building}) | Invigilator: {exam.invigilator}
    </div>
  </div>
);

export function Timetable() {
  const { exams, conflicts, user, addHistoryEntry, activeSessionId } = useAppStore();
  const { isLoading, error, fetchTimetable } = useLatestTimetable();

  // Component state for filters and view mode
  const [viewMode, setViewMode] = useState<'date' | 'room' | 'invigilator'>('date');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedDepartments, setSelectedDepartments] = useState<string[]>([]);
  const [selectedFaculties, setSelectedFaculties] = useState<string[]>([]);
  const [selectedRooms, setSelectedRooms] = useState<string[]>([]);
  const [selectedStaff, setSelectedStaff] = useState<string[]>([]);

  useEffect(() => {
    if (activeSessionId) {
      fetchTimetable();
    }
  }, [activeSessionId, fetchTimetable]);

  // Memoized selectors to get unique values for filters from the exam data
  const { departments, faculties, rooms, staff } = useMemo(() => {
    const deptSet = new Set<string>();
    const facultySet = new Set<string>();
    const roomSet = new Set<string>();
    const staffSet = new Set<string>();

    exams.forEach(exam => {
      exam.departments.forEach(dept => deptSet.add(dept));
      if (exam.facultyName) facultySet.add(exam.facultyName);
      if (exam.room) roomSet.add(exam.room);
      exam.invigilator.split(', ').forEach(inv => staffSet.add(inv));
    });

    return {
      departments: Array.from(deptSet).sort(),
      faculties: Array.from(facultySet).sort(),
      rooms: Array.from(roomSet).sort(),
      staff: Array.from(staffSet).sort(),
    };
  }, [exams]);

  // Filter exams based on all active filter criteria
  const filteredExams = useMemo(() => {
    return exams.filter(exam => {
      if (selectedDepartments.length > 0 && !exam.departments.some(dept => selectedDepartments.includes(dept))) return false;
      if (selectedFaculties.length > 0 && (!exam.facultyName || !selectedFaculties.includes(exam.facultyName))) return false;
      if (selectedRooms.length > 0 && !selectedRooms.includes(exam.room)) return false;
      if (selectedStaff.length > 0 && !exam.invigilator.split(', ').some(inv => selectedStaff.includes(inv))) return false;
      
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase();
        return (
          exam.courseCode.toLowerCase().includes(term) ||
          exam.courseName.toLowerCase().includes(term) ||
          exam.room.toLowerCase().includes(term) ||
          exam.invigilator.toLowerCase().includes(term)
        );
      }
      return true;
    });
  }, [exams, searchTerm, selectedDepartments, selectedFaculties, selectedRooms, selectedStaff]);
  
  // Group exams by room for the "Room View"
  const examsByRoom = useMemo(() => {
    return filteredExams.reduce((acc, exam) => {
      const key = exam.room || 'Unassigned';
      if (!acc[key]) acc[key] = [];
      acc[key].push(exam);
      return acc;
    }, {} as Record<string, RenderableExam[]>);
  }, [filteredExams]);
  
  // Group exams by invigilator for the "Invigilator View"
  const examsByInvigilator = useMemo(() => {
    return filteredExams.reduce((acc, exam) => {
      const invigilators = exam.invigilator ? exam.invigilator.split(', ') : ['Unassigned'];
      invigilators.forEach(inv => {
        if (!acc[inv]) acc[inv] = [];
        acc[inv].push(exam);
      });
      return acc;
    }, {} as Record<string, RenderableExam[]>);
  }, [filteredExams]);

  const handleMoveExam = (examId: string, newDate: string, newStartTime: string) => {
    const originalExam = exams.find(e => e.id === examId);
    if (!originalExam) return;

    addHistoryEntry({
      action: 'Manually moved exam',
      entityType: 'exam',
      entityId: originalExam.examId,
      userId: user?.id || 'system',
      userName: user?.name || 'System',
      details: {
        courseCode: originalExam.courseCode,
        from: `${originalExam.date} @ ${originalExam.startTime}`,
        to: `${newDate} @ ${newStartTime}`,
      },
    });

    toast.info(`${originalExam.courseCode} moved. Note: This is a UI-only change. API for manual edit is needed.`);
  };
  
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
        <h2 className="text-xl font-semibold">Loading Timetable</h2>
        <p className="text-muted-foreground mt-2">Fetching the latest exam schedule...</p>
      </div>
    );
  }

  if (error) {
     return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] text-center">
        <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold text-destructive">Failed to Load Timetable</h2>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <Button onClick={fetchTimetable} className="mt-4">Retry</Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Exam Timetable</h2>
          <p className="text-muted-foreground">
            {filteredExams.length} of {exams.length} exams shown
            {conflicts.length > 0 && (
              <span className="text-destructive ml-2">• {conflicts.length} conflict{conflicts.length !== 1 ? 's' : ''} detected</span>
            )}
          </p>
        </div>
      </div>

      <FilterControls
        viewMode={viewMode}
        onViewModeChange={(mode) => setViewMode(mode as any)}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
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
      />

      <Tabs defaultValue="timetable" className="space-y-4">
        <TabsList>
          <TabsTrigger value="timetable">
            <Grid className="h-4 w-4 mr-2" />
            Timetable Views
          </TabsTrigger>
          {conflicts.length > 0 && (
            <TabsTrigger value="conflicts">
              <AlertTriangle className="h-4 w-4 mr-2" />
              Conflicts ({conflicts.length})
            </TabsTrigger>
          )}
        </TabsList>
        <TabsContent value="timetable">
          {viewMode === 'date' && (
            <TimetableGrid 
              exams={filteredExams}
              viewMode={'general'} // or department based on another setting
              departments={departments}
              onMoveExam={handleMoveExam}
            />
          )}
          {viewMode === 'room' && (
             <div className="space-y-4">
              {Object.entries(examsByRoom).sort(([roomA], [roomB]) => roomA.localeCompare(roomB)).map(([room, examsInRoom]) => (
                <Card key={room}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2"><MapPin className="w-5 h-5" /> {room}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {examsInRoom.sort((a,b) => new Date(a.date).getTime() - new Date(b.date).getTime()).map(exam => (
                       <ExamDetailsCard key={exam.id} exam={exam} />
                    ))}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
          {viewMode === 'invigilator' && (
             <div className="space-y-4">
              {Object.entries(examsByInvigilator).sort(([invA], [invB]) => invA.localeCompare(invB)).map(([invigilator, examsForInvigilator]) => (
                <Card key={invigilator}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2"><User className="w-5 h-5" /> {invigilator}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {examsForInvigilator.sort((a,b) => new Date(a.date).getTime() - new Date(b.date).getTime()).map(exam => (
                      <ExamDetailsCard key={exam.id} exam={exam} />
                    ))}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
        {conflicts.length > 0 && (
          <TabsContent value="conflicts">
            <ConflictPanel conflicts={conflicts} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}