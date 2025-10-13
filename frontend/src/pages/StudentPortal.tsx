// frontend/src/pages/StudentPortal.tsx
import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '../components/ui/dialog';
import { DialogFooter, DialogClose } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { AlertTriangle, CalendarDays, Clock, MapPin, Building, LogOut, Grid3X3, List, Loader2, Sun, Moon, GraduationCap, Shield } from 'lucide-react';
import { useAppStore } from '../store';
import { useAuth } from '../hooks/useAuth';
import { useStudentPortalData } from '../hooks/useApi';
import { toast } from 'sonner';
import { TimetableGrid } from '../components/TimetableGrid';
import { FilterControls } from '../components/FilterControls';
import { RenderableExam, StudentExam, ConflictReport } from '../store/types';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';

export function StudentPortal() {
  const { user, studentExams, conflictReports, addConflictReport, settings, updateSettings } = useAppStore();
  const { logout } = useAuth();
  const { isLoading, error, refetch } = useStudentPortalData();

  const [selectedExam, setSelectedExam] = useState('');
  const [conflictDescription, setConflictDescription] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDepartments, setSelectedDepartments] = useState<string[]>([]);
  const [viewMode, setViewMode] = useState<'general' | 'department'>('general');

  useEffect(() => {
    const root = document.documentElement;
    if (settings.theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [settings.theme]);

  const toggleTheme = () => {
    updateSettings({ 
      theme: settings.theme === 'light' ? 'dark' : 'light' 
    });
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const userTimezoneOffset = date.getTimezoneOffset() * 60000;
    const adjustedDate = new Date(date.getTime() + userTimezoneOffset);
    return adjustedDate.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const formatTime = (time: string) => {
    if (!time) return 'N/A';
    const [hours, minutes] = time.split(':');
    const date = new Date();
    date.setHours(parseInt(hours, 10), parseInt(minutes, 10));
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
    if (!exam || !user) {
      toast.error('Could not find the selected exam or user information.');
      return;
    }
    addConflictReport({
      studentId: user.id,
      examId: selectedExam,
      courseCode: exam.courseCode,
      description: conflictDescription.trim(),
    });
    toast.success('Conflict report submitted successfully');
    setIsModalOpen(false);
    setSelectedExam('');
    setConflictDescription('');
  };

  function getDepartmentFromCourseCode(courseCode: string): string {
    const prefix = courseCode.replace(/[0-9]/g, '');
    const departmentMap: Record<string, string> = {
      'CS': 'Computer Science', 'MATH': 'Mathematics', 'PHYS': 'Physics',
      'ENG': 'English', 'CHEM': 'Chemistry', 'BIO': 'Biology',
      'STAT': 'Statistics', 'HIST': 'History', 'ECON': 'Economics',
      'ART': 'Art', 'PSYC': 'Psychology', 'PHIL': 'Philosophy',
      'LANG': 'Modern Languages'
    };
    return departmentMap[prefix] || 'General Studies';
  }

  const renderableExams: RenderableExam[] = useMemo(() => {
    return studentExams.map((exam: StudentExam) => ({
      id: exam.id,
      examId: exam.id,
      courseCode: exam.courseCode,
      courseName: exam.courseName,
      date: exam.date,
      startTime: exam.startTime,
      endTime: exam.endTime,
      duration: exam.duration,
      expectedStudents: exam.expectedStudents,
      room: exam.room,
      roomCapacity: exam.roomCapacity,
      building: exam.building,
      invigilator: exam.invigilator,
      departments: [getDepartmentFromCourseCode(exam.courseCode)],
      facultyName: 'N/A',
      instructor: exam.instructor,
      examType: 'Theory',
      conflicts: [],
      level: 'undergraduate',
      semester: 'Fall 2025',
      academicYear: '2025-2026',
    }));
  }, [studentExams]);

  const departments = useMemo(() => {
    const deptSet = new Set<string>();
    renderableExams.forEach(exam => {
      exam.departments.forEach(dept => deptSet.add(dept));
    });
    return Array.from(deptSet).sort();
  }, [renderableExams]);

  const filteredExams = useMemo(() => {
    if (selectedDepartments.length === 0) {
      return renderableExams;
    }
    return renderableExams.filter(exam =>
      exam.departments.some(dept => selectedDepartments.includes(dept))
    );
  }, [selectedDepartments, renderableExams]);

  const sortedExams = useMemo(() => 
    [...studentExams].sort((a, b) =>
      new Date(`${a.date}T${a.startTime}`).getTime() - new Date(`${b.date}T${b.startTime}`).getTime()
    ), [studentExams]);
  
  const handleMoveExam = (examId: string, newDate: string, newStartTime: string) => {
    toast.error('Students cannot reschedule exams. Please report a conflict if you have an issue.');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="ml-2">Loading your schedule...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-center p-4">
        <AlertTriangle className="mx-auto h-12 w-12 text-destructive" />
        <h3 className="mt-2 text-lg font-medium">Failed to Load Schedule</h3>
        <p className="mt-1 text-sm text-muted-foreground">{error instanceof Error ? error.message : 'An unknown error occurred.'}</p>
        <Button onClick={() => refetch()} className="mt-4">Try Again</Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-card border-b border-border">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold">My Exam Schedule</h1>
              <p className="text-muted-foreground">Fall 2025 - Spring 2026</p>
              <p className="text-sm text-muted-foreground">Welcome, {user?.name}</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" onClick={toggleTheme}>
                {settings.theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
              </Button>
              <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="w-full sm:w-auto">
                    <AlertTriangle className="h-4 w-4 mr-2" />
                    Report a Conflict
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-xl">
                  <DialogHeader>
                    <DialogTitle>Report Exam Conflict</DialogTitle>
                    <DialogDescription>
                      Report a scheduling conflict or issue with one of your exams. Provide as much detail as possible.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
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
                        placeholder="e.g., 'I have another exam scheduled at the same time...'"
                        value={conflictDescription}
                        onChange={(e) => setConflictDescription(e.target.value)}
                        rows={4}
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <DialogClose asChild>
                      <Button type="button" variant="outline">Cancel</Button>
                    </DialogClose>
                    <Button type="submit" onClick={handleSubmitConflict}>Submit Report</Button>
                  </DialogFooter>
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
            <TabsList className="grid w-full sm:w-fit grid-cols-3">
              <TabsTrigger value="list" className="flex items-center gap-2"><List className="h-4 w-4" />List View</TabsTrigger>
              <TabsTrigger value="grid" className="flex items-center gap-2"><Grid3X3 className="h-4 w-4" />Grid View</TabsTrigger>
              <TabsTrigger value="conflicts" className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />Reports ({conflictReports.length})
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="list" className="mt-0">
            {sortedExams.length === 0 ? (
              <Card>
                <CardContent className="py-8 text-center">
                  <CalendarDays className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="font-semibold">No Exams Scheduled</h3>
                  <p className="text-muted-foreground text-sm">Your exam schedule will appear here once available.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {sortedExams.map((exam) => (
                  <Card key={exam.id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-3">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                        <div>
                          <CardTitle className="text-lg">{exam.courseCode}</CardTitle>
                          <p className="text-muted-foreground">{exam.courseName}</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="outline" className="w-fit">{Math.floor(exam.duration / 60)}h {exam.duration % 60}m</Badge>
                          <Badge variant="secondary" className="w-fit">{getDepartmentFromCourseCode(exam.courseCode)}</Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-y-2 gap-x-4">
                        <div className="flex items-center gap-2"><CalendarDays className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{formatDate(exam.date)}</span></div>
                        <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{formatTime(exam.startTime)} - {formatTime(exam.endTime)}</span></div>
                        <div className="flex items-center gap-2"><MapPin className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{exam.room}</span></div>
                      </div>
                      <div className="space-y-2 mt-3 pt-3 border-t">
                        <div className="flex items-center gap-2"><Building className="h-4 w-4 text-muted-foreground" /><span className="text-sm text-muted-foreground">{exam.building}</span></div>
                        <div className="flex items-center gap-2"><GraduationCap className="h-4 w-4 text-muted-foreground" /><span className="text-sm text-muted-foreground">Instructor(s): {exam.instructor}</span></div>
                        <div className="flex items-center gap-2"><Shield className="h-4 w-4 text-muted-foreground" /><span className="text-sm text-muted-foreground">Invigilator(s): {exam.invigilator}</span></div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="grid" className="mt-0">
            <div className="space-y-6">
              <Card>
                <CardContent className="p-4 flex flex-col sm:flex-row gap-4">
                  <div className="flex-grow">
                     <FilterControls
                        departments={departments}
                        selectedDepartments={selectedDepartments}
                        onDepartmentsChange={setSelectedDepartments}
                      />
                  </div>
                  <div className="w-full sm:w-48">
                    <Label>Color Scheme</Label>
                    <Select value={viewMode} onValueChange={(value) => setViewMode(value as 'general' | 'department')}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select color mode" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="general">Default</SelectItem>
                        <SelectItem value="department">By Department</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>
              
              {filteredExams.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center">
                    <CalendarDays className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="font-semibold">No Exams to Display</h3>
                    <p className="text-muted-foreground text-sm">No exams match the selected filters.</p>
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
          <TabsContent value="conflicts" className="mt-0">
            <Card>
              <CardHeader>
                <CardTitle>My Conflict Reports</CardTitle>
                <CardDescription>A history of all conflict reports you have submitted.</CardDescription>
              </CardHeader>
              <CardContent>
                {conflictReports.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>You have not submitted any conflict reports.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {conflictReports.map((report: ConflictReport) => (
                      <Alert key={report.id}>
                        <AlertTriangle className="h-4 w-4" />
                        <AlertTitle className="flex justify-between items-center">
                          <span>Conflict for Exam ID: {report.examId.substring(0, 8)}...</span>
                          <Badge variant={
                            report.status === 'resolved' ? 'default' :
                            report.status === 'reviewed' ? 'secondary' :
                            'destructive'
                          }>
                            {report.status}
                          </Badge>
                        </AlertTitle>
                        <AlertDescription>
                          <p className="mt-2">{report.description}</p>
                          <p className="text-xs text-muted-foreground mt-2">
                            Submitted: {new Date(report.submittedAt).toLocaleString()}
                          </p>
                        </AlertDescription>
                      </Alert>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}