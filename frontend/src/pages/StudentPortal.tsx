import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { AlertTriangle, CalendarDays, Clock, MapPin, Building, LogOut, Grid3X3, List } from 'lucide-react';
import { useAppStore } from '../store';
import { useAuth } from '../hooks/useAuth';
import { toast } from 'sonner';
import { TimetableGrid } from '../components/TimetableGrid';
import { FilterControls } from '../components/FilterControls';
import { RenderableExam } from '../store/types';

export function StudentPortal() {
  const { user, studentExams, setStudentExams, addConflictReport } = useAppStore();
  const { logout } = useAuth();
  const [selectedExam, setSelectedExam] = useState('');
  const [conflictDescription, setConflictDescription] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'general' | 'department'>('general');

  useEffect(() => {
    // Load mock student exam data
    const mockStudentExams = [
      {
        id: 'exam-1',
        courseCode: 'CS101',
        courseName: 'Introduction to Computer Science',
        date: '2024-12-10',
        startTime: '09:00',
        endTime: '12:00',
        room: 'LH-201',
        building: 'Science Building',
        duration: 180,
      },
      {
        id: 'exam-2',
        courseCode: 'MATH201',
        courseName: 'Calculus II',
        date: '2024-12-12',
        startTime: '14:00',
        endTime: '17:00',
        room: 'EX-101',
        building: 'Engineering Building',
        duration: 180,
      },
      {
        id: 'exam-3',
        courseCode: 'PHYS150',
        courseName: 'General Physics',
        date: '2024-12-15',
        startTime: '09:00',
        endTime: '11:30',
        room: 'SH-305',
        building: 'Science Hall',
        duration: 150,
      },
      {
        id: 'exam-4',
        courseCode: 'ENG102',
        courseName: 'English Composition',
        date: '2024-12-18',
        startTime: '10:00',
        endTime: '12:30',
        room: 'LA-204',
        building: 'Liberal Arts Building',
        duration: 150,
      },
    ];
    setStudentExams(mockStudentExams);
  }, [setStudentExams]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  const formatTime = (time: string) => {
    const [hours, minutes] = time.split(':');
    const date = new Date();
    date.setHours(parseInt(hours), parseInt(minutes));
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const handleSubmitConflict = () => {
    if (!selectedExam || !conflictDescription.trim()) {
      toast.error('Please select an exam and provide a description');
      return;
    }

    const exam = studentExams.find(e => e.id === selectedExam);
    if (!exam) return;

    addConflictReport({
      studentId: user!.id,
      examId: selectedExam,
      courseCode: exam.courseCode,
      description: conflictDescription.trim(),
    });

    toast.success('Conflict report submitted successfully');
    setSelectedExam('');
    setConflictDescription('');
    setIsModalOpen(false);
  };

  // Convert StudentExam to RenderableExam format for grid view
  const renderableExams: RenderableExam[] = useMemo(() => {
    return studentExams.map(exam => ({
      id: exam.id,
      courseCode: exam.courseCode,
      courseName: exam.courseName,
      date: exam.date,
      startTime: exam.startTime,
      endTime: exam.endTime,
      duration: exam.duration,
      expectedStudents: 0, // Not available in student view
      room: exam.room,
      roomCapacity: 0, // Not available in student view
      building: exam.building,
      invigilator: '', // Not displayed to students
      departments: [getDepartmentFromCourseCode(exam.courseCode)],
      level: 'undergraduate', // Default
      semester: 'fall',
      academicYear: '2024-2025'
    }));
  }, [studentExams]);

  // Extract departments from course codes
  const departments = useMemo(() => {
    const deptSet = new Set<string>();
    renderableExams.forEach(exam => {
      exam.departments.forEach(dept => deptSet.add(dept));
    });
    return Array.from(deptSet).sort();
  }, [renderableExams]);

  // Filter exams for grid view
  const filteredExams = useMemo(() => {
    if (selectedDepartment === 'all') {
      return renderableExams;
    }
    return renderableExams.filter(exam => 
      exam.departments.includes(selectedDepartment)
    );
  }, [selectedDepartment, renderableExams]);

  // Sort exams by date
  const sortedExams = [...studentExams].sort((a, b) => 
    new Date(a.date + ' ' + a.startTime).getTime() - 
    new Date(b.date + ' ' + b.startTime).getTime()
  );

  // Helper function to determine department from course code
  function getDepartmentFromCourseCode(courseCode: string): string {
    const prefix = courseCode.replace(/[0-9]/g, '');
    const departmentMap: Record<string, string> = {
      'CS': 'Computer Science',
      'MATH': 'Mathematics',
      'PHYS': 'Physics',
      'ENG': 'English',
      'CHEM': 'Chemistry',
      'BIO': 'Biology',
      'STAT': 'Statistics',
      'HIST': 'History',
      'ECON': 'Economics',
      'ART': 'Art',
      'PSYC': 'Psychology',
      'PHIL': 'Philosophy',
      'LANG': 'Modern Languages'
    };
    return departmentMap[prefix] || 'General Studies';
  }

  const handleMoveExam = (examId: string, newDate: string, newStartTime: string) => {
    // Students cannot move exams - this is just for display
    toast.error('Students cannot reschedule exams. Please contact your instructor or report a conflict.');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-card border-b border-border">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl">My Exam Schedule</h1>
              <p className="text-muted-foreground">Fall 2024 - Spring 2025</p>
              <p className="text-sm text-muted-foreground">Welcome, {user?.name}</p>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="w-full sm:w-auto">
                    <AlertTriangle className="h-4 w-4 mr-2" />
                    Report a Conflict
                  </Button>
                </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Report Exam Conflict</DialogTitle>
                  <DialogDescription>
                    Report a scheduling conflict or issue with one of your exams. Provide as much detail as possible.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="exam-select">Select Exam</Label>
                    <Select value={selectedExam} onValueChange={setSelectedExam}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choose an exam..." />
                      </SelectTrigger>
                      <SelectContent>
                        {studentExams.map((exam) => (
                          <SelectItem key={exam.id} value={exam.id}>
                            {exam.courseCode} - {exam.courseName}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="description">Describe the conflict</Label>
                    <Textarea
                      id="description"
                      placeholder="Please describe the scheduling conflict (e.g., 'I have another exam scheduled at the same time for a different university program')"
                      value={conflictDescription}
                      onChange={(e) => setConflictDescription(e.target.value)}
                      rows={4}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleSubmitConflict} className="flex-1">
                      Submit Report
                    </Button>
                    <Button 
                      variant="outline" 
                      onClick={() => setIsModalOpen(false)}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Exam Schedule */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        <Tabs defaultValue="list" className="w-full">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <TabsList className="grid w-full sm:w-fit grid-cols-2">
              <TabsTrigger value="list" className="flex items-center gap-2">
                <List className="h-4 w-4" />
                List View
              </TabsTrigger>
              <TabsTrigger value="grid" className="flex items-center gap-2">
                <Grid3X3 className="h-4 w-4" />
                Grid View
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="list" className="mt-0">
            {sortedExams.length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center">
                  <CalendarDays className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3>No Exams Scheduled</h3>
                  <p className="text-muted-foreground">
                    Your exam schedule will appear here once available.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {sortedExams.map((exam) => (
                  <Card key={exam.id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                        <div>
                          <CardTitle className="text-lg">
                            {exam.courseCode}
                          </CardTitle>
                          <p className="text-muted-foreground">
                            {exam.courseName}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="outline" className="w-fit">
                            {Math.floor(exam.duration / 60)}h {exam.duration % 60}m
                          </Badge>
                          <Badge variant="secondary" className="w-fit">
                            {getDepartmentFromCourseCode(exam.courseCode)}
                          </Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div className="flex items-center gap-2">
                          <CalendarDays className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">
                            {formatDate(exam.date)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Clock className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">
                            {formatTime(exam.startTime)} - {formatTime(exam.endTime)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <MapPin className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">
                            {exam.room}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border">
                        <Building className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
                          {exam.building}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="grid" className="mt-0">
            <div className="space-y-6">
              <FilterControls
                departments={departments}
                selectedDepartment={selectedDepartment}
                onDepartmentChange={setSelectedDepartment}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
              
              {filteredExams.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center">
                    <CalendarDays className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3>No Exams to Display</h3>
                    <p className="text-muted-foreground">
                      No exams match the selected filters.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <TimetableGrid 
                  exams={filteredExams}
                  viewMode={viewMode}
                  departments={departments}
                  onMoveExam={handleMoveExam}
                />
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}