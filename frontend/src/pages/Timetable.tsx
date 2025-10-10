import { useState, useMemo, useEffect } from 'react';
import { TimetableGrid } from '../components/TimetableGrid';
import { FilterControls } from '../components/FilterControls';
import { ConflictPanel } from '../components/ConflictPanel';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { AlertTriangle, Grid, Loader2, Calendar, User, MapPin, Building, Book, PlayCircle, CheckCircle, ListCollapse } from 'lucide-react';
import { useAppStore } from '../store';
import { toast } from 'sonner';
import { RenderableExam } from '../store/types';
import { api } from '../services/api';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { formatDistanceToNow } from 'date-fns';
import { Badge } from '../components/ui/badge';

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
  const { exams, conflicts, user, addHistoryEntry, activeSessionId, setCurrentPage, currentJobId, sessionJobs, fetchSessionJobs, fetchAndSetJobResult } = useAppStore();
  const [isPublishing, setIsPublishing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Component state for filters and view mode
  const [viewMode, setViewMode] = useState<'date' | 'room' | 'invigilator'>('date');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedDepartments, setSelectedDepartments] = useState<string[]>([]);
  const [selectedFaculties, setSelectedFaculties] = useState<string[]>([]);
  const [selectedRooms, setSelectedRooms] = useState<string[]>([]);
  const [selectedStaff, setSelectedStaff] = useState<string[]>([]);
  const [selectedBuildings, setSelectedBuildings] = useState<string[]>([]);

  // Data fetching logic
  useEffect(() => {
    const loadInitialData = async () => {
      if (activeSessionId) {
        setIsLoading(true);
        setError(null);
        try {
          await fetchSessionJobs(activeSessionId);
          const jobs = useAppStore.getState().sessionJobs;
          const publishedJob = jobs.find(j => j.is_published);
          const jobToLoad = publishedJob || jobs[0];

          if (jobToLoad) {
            await fetchAndSetJobResult(jobToLoad.id);
          }
        } catch (err) {
          setError(err instanceof Error ? err : new Error('Failed to load initial timetable data'));
        } finally {
          setIsLoading(false);
        }
      } else {
        setIsLoading(false);
      }
    };
    loadInitialData();
  }, [activeSessionId, fetchSessionJobs, fetchAndSetJobResult]);

  // Memoized selectors to get unique values for filters from the exam data
  const { departments, faculties, rooms, staff, buildings } = useMemo(() => {
    const deptSet = new Set<string>();
    const facultySet = new Set<string>();
    const roomSet = new Set<string>();
    const staffSet = new Set<string>();
    const buildingSet = new Set<string>();

    exams.forEach(exam => {
      exam.departments.forEach(dept => deptSet.add(dept));
      if (exam.facultyName) facultySet.add(exam.facultyName);
      if (exam.room) roomSet.add(exam.room);
      if (exam.building) buildingSet.add(exam.building);
      exam.invigilator.split(', ').forEach(inv => {
        if (inv && inv !== 'N/A') staffSet.add(inv);
      });
    });

    return {
      departments: Array.from(deptSet).sort(),
      faculties: Array.from(facultySet).sort(),
      rooms: Array.from(roomSet).sort(),
      staff: Array.from(staffSet).sort(),
      buildings: Array.from(buildingSet).sort(),
    };
  }, [exams]);

  // Filter exams based on all active filter criteria
  const filteredExams = useMemo(() => {
    return exams.filter(exam => {
      if (selectedDepartments.length > 0 && !exam.departments.some(dept => selectedDepartments.includes(dept))) return false;
      if (selectedFaculties.length > 0 && (!exam.facultyName || !selectedFaculties.includes(exam.facultyName))) return false;
      if (selectedRooms.length > 0 && !selectedRooms.includes(exam.room)) return false;
      if (selectedBuildings.length > 0 && !selectedBuildings.includes(exam.building)) return false;
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
  }, [exams, searchTerm, selectedDepartments, selectedFaculties, selectedRooms, selectedStaff, selectedBuildings]);
  
  // Group exams by building, then by room for the "Room View"
  const examsByBuildingAndRoom = useMemo(() => {
    return filteredExams.reduce((acc, exam) => {
      const building = exam.building || 'Unassigned Building';
      const room = exam.room || 'Unassigned Room';
      
      if (!acc[building]) acc[building] = {};
      if (!acc[building][room]) acc[building][room] = [];
      
      acc[building][room].push(exam);
      return acc;
    }, {} as Record<string, Record<string, RenderableExam[]>>);
  }, [filteredExams]);
  
  // Group exams by faculty, then department, then invigilator for the "Invigilator View"
  const examsByFacultyDeptAndInvigilator = useMemo(() => {
    return filteredExams.reduce((acc, exam) => {
      const faculty = exam.facultyName || 'Unknown Faculty';
      const invigilators = exam.invigilator ? exam.invigilator.split(', ').filter(i => i) : ['Unassigned'];

      exam.departments.forEach(department => {
        if (!acc[faculty]) acc[faculty] = {};
        if (!acc[faculty][department]) acc[faculty][department] = {};

        invigilators.forEach(inv => {
          if (inv === 'N/A' || inv === 'Unassigned') return;
          if (!acc[faculty][department][inv]) acc[faculty][department][inv] = [];
          acc[faculty][department][inv].push(exam);
        });
      });
      
      return acc;
    }, {} as Record<string, Record<string, Record<string, RenderableExam[]>>>);
  }, [filteredExams]);

  const handleMoveExam = (examId: string, newDate: string, newStartTime: string) => {
    const originalExam = exams.find(e => e.id === examId);
    if (!originalExam) return;

    addHistoryEntry({
      action: 'Manually move exam',
      entityType: 'exam',
      entityId: originalExam.examId,
      userName: user?.name || 'Unknown User',
      timestamp: new Date().toISOString(),
      details: {
        courseCode: originalExam.courseCode,
        courseName: originalExam.courseName
      },
      changes: {
        before: { date: originalExam.date, startTime: originalExam.startTime },
        after: { date: newDate, startTime: newStartTime },
      },
    });


    toast.info(`${originalExam.courseCode} moved. Note: This is a UI-only change. API for manual edit is needed.`);
  };
  
  const handlePublish = async () => {
    if (!currentJobId) {
      toast.error("No timetable job is currently loaded to be published.");
      return;
    }

    setIsPublishing(true);
    try {
      await api.publishVersion(currentJobId);
      toast.success("Timetable published successfully!", {
        description: "This timetable is now the official version for the session.",
      });
    } catch (error: any) {
      const detail = error.response?.data?.detail || "An unknown error occurred.";
      toast.error(`Publishing failed: ${detail}`);
    } finally {
      setIsPublishing(false);
    }
  };

  const handleJobSelect = async (jobId: string) => {
    setIsLoading(true);
    await fetchAndSetJobResult(jobId);
    setIsLoading(false);
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
        <Button onClick={() => window.location.reload()} className="mt-4">Retry</Button>
      </div>
    )
  }

  if (exams.length === 0 && !isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <Card className="w-full max-w-lg text-center p-8">
          <CardHeader>
            <div className="mx-auto bg-primary/10 rounded-full p-4 w-fit">
              <Calendar className="h-12 w-12 text-primary" />
            </div>
            <CardTitle className="mt-4">No Timetable Generated</CardTitle>
            <CardDescription>
              There is no exam schedule to display for the current academic session.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="mb-6 text-muted-foreground">
              To view the timetable, you first need to generate a schedule using the automated solver.
            </p>
            <Button onClick={() => setCurrentPage('scheduling')}>
              <PlayCircle className="h-4 w-4 mr-2" />
              Go to Scheduling Page
            </Button>
          </CardContent>
        </Card>
      </div>
    );
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
        <div className="flex items-center gap-2">
          <Select onValueChange={handleJobSelect} value={currentJobId ?? ""}>
            <SelectTrigger className="w-64">
              <div className="flex items-center gap-2">
                <ListCollapse className="h-4 w-4" />
                <SelectValue placeholder="Select a timetable version..." />
              </div>
            </SelectTrigger>
            <SelectContent>
              {sessionJobs.map((job, index) => (
                <SelectItem key={`${job.id}-${index}`} value={job.id}>
                  <div className="flex justify-between items-center">
                    <span>{formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}</span>
                    {job.is_published && <Badge variant="default" className="ml-2">Published</Badge>}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
            
          </Select>

          <Button onClick={handlePublish} disabled={!currentJobId || isPublishing}>
            {isPublishing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle className="h-4 w-4 mr-2" />}
            Publish Timetable
          </Button>
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
        buildings={buildings}
        selectedBuildings={selectedBuildings}
        onBuildingsChange={setSelectedBuildings}
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
              {Object.entries(examsByBuildingAndRoom).sort(([buildingA], [buildingB]) => buildingA.localeCompare(buildingB)).map(([building, roomsInBuilding]) => (
                <Card key={building}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Building className="w-5 h-5" /> {building}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {Object.entries(roomsInBuilding).sort(([roomA], [roomB]) => roomA.localeCompare(roomB)).map(([room, examsInRoom]) => (
                      <div key={room} className="p-3 border rounded-md">
                         <h4 className="font-semibold flex items-center gap-2 mb-2"><MapPin className="w-4 h-4 text-muted-foreground"/>{room}</h4>
                         <div className='space-y-2'>
                          {examsInRoom.sort((a,b) => new Date(a.date).getTime() - new Date(b.date).getTime()).map(exam => (
                            <ExamDetailsCard key={exam.id} exam={exam} />
                          ))}
                         </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
          {viewMode === 'invigilator' && (
             <div className="space-y-4">
              {Object.entries(examsByFacultyDeptAndInvigilator).sort(([facultyA], [facultyB]) => facultyA.localeCompare(facultyB)).map(([faculty, departments]) => (
                <Card key={faculty}>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Book className="w-5 h-5" /> {faculty}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {Object.entries(departments).sort(([deptA], [deptB]) => deptA.localeCompare(deptB)).map(([department, invigilators]) => (
                       <Card key={department} className="bg-muted/50">
                        <CardHeader className='py-3'>
                          <CardTitle className="text-base">{department}</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {Object.entries(invigilators).sort(([invA], [invB]) => invA.localeCompare(invB)).map(([invigilator, exams]) => (
                             <div key={invigilator}>
                               <h4 className="font-semibold flex items-center gap-2 mb-2 text-sm"><User className="w-4 h-4 text-muted-foreground"/>{invigilator}</h4>
                               <div className="space-y-2 pl-6 border-l ml-2">
                                {exams.sort((a,b) => new Date(a.date).getTime() - new Date(b.date).getTime()).map(exam => (
                                    <ExamDetailsCard key={exam.id} exam={exam} />
                                ))}
                               </div>
                            </div>
                          ))}
                        </CardContent>
                       </Card>
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