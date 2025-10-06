// frontend/src/pages/StaffPortal.tsx
import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { CalendarDays, Clock, MapPin, Building, FileEdit, GraduationCap, Shield, LogOut, Grid3X3, List, Loader2, AlertTriangle, Sun, Moon } from 'lucide-react';
import { useAppStore } from '../store';
import { useAuth } from '../hooks/useAuth';
import { useStaffPortalData } from '../hooks/useApi';
import { toast } from 'sonner';
import { TimetableGrid } from '../components/TimetableGrid';
import { FilterControls } from '../components/FilterControls';
import { RenderableExam, StaffAssignment, ChangeRequest } from '../store/types';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';

export function StaffPortal() {
  const { user, instructorSchedule, invigilatorSchedule, changeRequests, addChangeRequest, settings, updateSettings } = useAppStore();
  const { logout } = useAuth();
  const { isLoading, error, refetch } = useStaffPortalData();

  const [selectedAssignment, setSelectedAssignment] = useState('');
  const [changeReason, setChangeReason] = useState('');
  const [changeDescription, setChangeDescription] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [portalView, setPortalView] = useState<'list' | 'grid'>('list');
  const [selectedDepartments, setSelectedDepartments] = useState<string[]>([]);
  
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

  const allAssignments = useMemo(() => [...instructorSchedule, ...invigilatorSchedule], [instructorSchedule, invigilatorSchedule]);

  const getDepartmentFromCourseCode = (courseCode: string): string => {
    const prefix = courseCode.replace(/[0-9]/g, '');
    const departmentMap: Record<string, string> = {
      'CS': 'Computer Science', 'MATH': 'Mathematics', 'PHYS': 'Physics', 'ENG': 'English', 'CHEM': 'Chemistry', 'BIO': 'Biology', 'STAT': 'Statistics', 'HIST': 'History', 'ECON': 'Economics', 'ART': 'Art', 'PSYC': 'Psychology', 'PHIL': 'Philosophy', 'LANG': 'Modern Languages'
    };
    return departmentMap[prefix] || 'General Studies';
  };

  const renderableExams = useMemo((): RenderableExam[] => {
    return allAssignments.map((assignment) => ({
      id: assignment.id,
      examId: assignment.examId,
      courseCode: assignment.courseCode,
      courseName: assignment.courseName,
      date: assignment.date,
      startTime: assignment.startTime,
      endTime: assignment.endTime,
      duration: new Date(`1970-01-01T${assignment.endTime}`).getTime() - new Date(`1970-01-01T${assignment.startTime}`).getTime(),
      expectedStudents: 0,
      room: assignment.room,
      roomCapacity: 0,
      building: assignment.building,
      invigilator: assignment.role === 'invigilator' ? user?.name || 'N/A' : 'N/A',
      departments: [getDepartmentFromCourseCode(assignment.courseCode)],
      facultyName: 'N/A',
      instructor: assignment.role === 'instructor' ? user?.name || 'N/A' : 'N/A',
      examType: 'Theory',
      conflicts: [],
      level: 'undergraduate',
      semester: 'Fall 2025',
      academicYear: '2025-2026',
    }));
  }, [allAssignments, user]);

  const departments = useMemo(() => {
    const deptSet = new Set<string>();
    renderableExams.forEach(exam => exam.departments.forEach(dept => deptSet.add(dept)));
    return Array.from(deptSet).sort();
  }, [renderableExams]);

  const filteredGridExams = useMemo(() => {
    if (selectedDepartments.length === 0) return renderableExams;
    return renderableExams.filter(exam => exam.departments.some(dept => selectedDepartments.includes(dept)));
  }, [renderableExams, selectedDepartments]);
  
  const handleMoveExam = () => toast.error('Staff cannot reschedule assignments directly. Please submit a change request.');

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const userTimezoneOffset = date.getTimezoneOffset() * 60000;
    const adjustedDate = new Date(date.getTime() + userTimezoneOffset);
    return adjustedDate.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  };

  const formatTime = (time: string) => {
    if (!time) return 'N/A';
    const [hours, minutes] = time.split(':');
    const date = new Date();
    date.setHours(parseInt(hours, 10), parseInt(minutes, 10));
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  };

  const getRoleIcon = (role: StaffAssignment['role']) => {
    const iconMap = { 'instructor': <GraduationCap className="h-4 w-4" />, 'lead-invigilator': <Shield className="h-4 w-4" />, 'invigilator': <FileEdit className="h-4 w-4" /> };
    return iconMap[role] || <FileEdit className="h-4 w-4" />;
  };

  const getRoleLabel = (role: StaffAssignment['role']) => {
    const labelMap = { 'instructor': 'Instructor', 'lead-invigilator': 'Lead Invigilator', 'invigilator': 'Invigilator' };
    return labelMap[role] || role;
  };
  
  const handleSubmitChangeRequest = () => {
    if (!selectedAssignment || !changeReason) {
      toast.error('Please select an assignment and specify a reason for the change.');
      return;
    }
    const assignment = allAssignments.find(a => a.id === selectedAssignment);
    if (!assignment || !user) {
      toast.error('Could not find assignment or user details.');
      return;
    }
    addChangeRequest({ staffId: user.id, assignmentId: selectedAssignment, courseCode: assignment.courseCode, reason: changeReason, description: changeDescription.trim() || undefined });
    toast.success('Change request submitted successfully');
    setIsModalOpen(false);
    setSelectedAssignment('');
    setChangeReason('');
    setChangeDescription('');
  };

  const sortAssignments = (assignments: StaffAssignment[]) => [...assignments].sort((a, b) => new Date(`${a.date}T${a.startTime}`).getTime() - new Date(`${b.date}T${b.startTime}`).getTime());

  const sortedInstructorSchedule = useMemo(() => sortAssignments(instructorSchedule), [instructorSchedule]);
  const sortedInvigilatorSchedule = useMemo(() => sortAssignments(invigilatorSchedule), [invigilatorSchedule]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" /> <p className="ml-2">Loading your assignments...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-center p-4">
        <AlertTriangle className="mx-auto h-12 w-12 text-destructive" />
        <h3 className="mt-2 text-lg font-medium">Failed to Load Assignments</h3>
        <p className="mt-1 text-sm text-muted-foreground">{error instanceof Error ? error.message : 'An unknown error occurred.'}</p>
        <Button onClick={() => refetch()} className="mt-4">Try Again</Button>
      </div>
    );
  }

  const AssignmentCard = ({ assignment }: { assignment: StaffAssignment }) => (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
          <div>
            <CardTitle className="text-lg">{assignment.courseCode}</CardTitle>
            <p className="text-muted-foreground">{assignment.courseName}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={assignment.role === 'instructor' ? 'default' : 'secondary'}>{getRoleIcon(assignment.role)}<span className="ml-1.5">{getRoleLabel(assignment.role)}</span></Badge>
            {assignment.status === 'change-requested' && (<Badge variant="outline" className="text-amber-600 border-amber-500">Change Requested</Badge>)}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-y-2 gap-x-4 mb-4">
          <div className="flex items-center gap-2"><CalendarDays className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{formatDate(assignment.date)}</span></div>
          <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{formatTime(assignment.startTime)} - {formatTime(assignment.endTime)}</span></div>
          <div className="flex items-center gap-2"><MapPin className="h-4 w-4 text-muted-foreground" /><span className="text-sm">{assignment.room}</span></div>
        </div>
        <div className="flex items-center justify-between pt-3 border-t">
          <div className="flex items-center gap-2"><Building className="h-4 w-4 text-muted-foreground" /><span className="text-sm text-muted-foreground">{assignment.building}</span></div>
          {assignment.status === 'assigned' && (<DialogTrigger asChild><Button variant="outline" size="sm" onClick={() => { setSelectedAssignment(assignment.id); setIsModalOpen(true); }}>Request Change</Button></DialogTrigger>)}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-background">
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <div className="bg-card border-b border-border">
          <div className="max-w-6xl mx-auto px-4 py-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold">My Assignments</h1>
                <p className="text-muted-foreground">Teaching & Invigilation Duties - Fall 2025</p>
                <p className="text-sm text-muted-foreground">Welcome, {user?.name}</p>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="icon" onClick={toggleTheme}>
                  {settings.theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                </Button>
                <Button variant="ghost" size="sm" onClick={logout}><LogOut className="h-4 w-4 mr-2" />Logout</Button>
              </div>
            </div>
          </div>
        </div>
        <div className="max-w-6xl mx-auto px-4 py-6">
          <Tabs value={portalView} onValueChange={(value) => setPortalView(value as 'list' | 'grid')} className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="list"><List className="h-4 w-4 mr-2" />Assignments</TabsTrigger>
              <TabsTrigger value="grid"><Grid3X3 className="h-4 w-4 mr-2" />Timetable View</TabsTrigger>
            </TabsList>
            <TabsContent value="list">
              <Tabs defaultValue="teaching" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="teaching"><GraduationCap className="h-4 w-4 mr-2" />Teaching ({instructorSchedule.length})</TabsTrigger>
                  <TabsTrigger value="invigilation"><Shield className="h-4 w-4 mr-2" />Invigilation ({invigilatorSchedule.length})</TabsTrigger>
                  <TabsTrigger value="requests"><FileEdit className="h-4 w-4 mr-2" />My Requests ({changeRequests.length})</TabsTrigger>
                </TabsList>
                <TabsContent value="teaching" className="mt-4"><div className="space-y-4">{sortedInstructorSchedule.length === 0 ? <Card><CardContent className="py-8 text-center"><h3 className="font-semibold">No Teaching Assignments</h3><p className="text-sm text-muted-foreground">You have no teaching duties assigned.</p></CardContent></Card> : sortedInstructorSchedule.map((assignment) => <AssignmentCard key={assignment.id} assignment={assignment} />)}</div></TabsContent>
                <TabsContent value="invigilation" className="mt-4"><div className="space-y-4">{sortedInvigilatorSchedule.length === 0 ? <Card><CardContent className="py-8 text-center"><h3 className="font-semibold">No Invigilation Duties</h3><p className="text-sm text-muted-foreground">You have no invigilation duties assigned.</p></CardContent></Card> : sortedInvigilatorSchedule.map((assignment) => <AssignmentCard key={assignment.id} assignment={assignment} />)}</div></TabsContent>
                <TabsContent value="requests" className="mt-4">
                  <Card>
                    <CardHeader>
                      <CardTitle>My Change Requests</CardTitle>
                      <CardDescription>A history of all assignment change requests you have submitted.</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {changeRequests.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          <p>You have not submitted any change requests.</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {changeRequests.map((request: ChangeRequest) => (
                            <Alert key={request.id}>
                              <FileEdit className="h-4 w-4" />
                              <AlertTitle className="flex justify-between items-center">
                                <span>Request for Assignment: {request.assignmentId.substring(0,8)}...</span>
                                <Badge variant={
                                  request.status === 'approved' ? 'default' :
                                  request.status === 'denied' ? 'destructive' :
                                  'secondary'
                                }>
                                  {request.status}
                                </Badge>
                              </AlertTitle>
                              <AlertDescription>
                                <p className="font-medium mt-2">Reason: {request.reason}</p>
                                {request.description && <p className="mt-1">{request.description}</p>}
                                <p className="text-xs text-muted-foreground mt-2">
                                  Submitted: {new Date(request.submittedAt).toLocaleString()}
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
            </TabsContent>
            <TabsContent value="grid">
              <div className="space-y-4">
                <FilterControls departments={departments} selectedDepartments={selectedDepartments} onDepartmentsChange={setSelectedDepartments} />
                <TimetableGrid exams={filteredGridExams} viewMode="general" departments={departments} onMoveExam={handleMoveExam} />
              </div>
            </TabsContent>
          </Tabs>
        </div>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle>Request Assignment Change</DialogTitle><DialogDescription>Submit a request to change your exam assignment. Provide a clear reason for the request.</DialogDescription></DialogHeader>
          <div className="space-y-4 py-2">
            {selectedAssignment && <div className="p-3 bg-muted rounded-md text-sm"><p className="font-semibold">{allAssignments.find(a => a.id === selectedAssignment)?.courseCode}</p><p className="text-muted-foreground">{allAssignments.find(a => a.id === selectedAssignment)?.courseName}</p></div>}
            <div><Label htmlFor="reason-select">Reason for Change</Label><Select value={changeReason} onValueChange={setChangeReason}><SelectTrigger><SelectValue placeholder="Select a reason..." /></SelectTrigger><SelectContent><SelectItem value="scheduling-conflict">Scheduling Conflict</SelectItem><SelectItem value="medical-appointment">Medical Appointment</SelectItem><SelectItem value="personal-emergency">Personal Emergency</SelectItem><SelectItem value="other">Other</SelectItem></SelectContent></Select></div>
            <div><Label htmlFor="description">Additional Details (Optional)</Label><Textarea id="description" placeholder="Provide more details..." value={changeDescription} onChange={(e) => setChangeDescription(e.target.value)} rows={3} /></div>
            <div className="flex justify-end gap-2 pt-2"><Button variant="ghost" onClick={() => setIsModalOpen(false)}>Cancel</Button><Button onClick={handleSubmitChangeRequest}>Submit Request</Button></div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}