import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { CalendarDays, Clock, MapPin, Building, FileEdit, GraduationCap, Shield, LogOut, Grid3X3, List } from 'lucide-react';
import { useAppStore } from '../store';
import { useAuth } from '../hooks/useAuth';
import { toast } from 'sonner';
import { TimetableGrid } from '../components/TimetableGrid';
import { FilterControls } from '../components/FilterControls';
import { RenderableExam } from '../store/types';

export function StaffPortal() {
  const { user, staffAssignments, setStaffAssignments, addChangeRequest } = useAppStore();
  const { logout } = useAuth();
  const [selectedAssignment, setSelectedAssignment] = useState('');
  const [changeReason, setChangeReason] = useState('');
  const [changeDescription, setChangeDescription] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'general' | 'department'>('general');

  useEffect(() => {
    // Load mock staff assignments
    const mockStaffAssignments = [
      {
        id: 'assign-1',
        examId: 'exam-1',
        courseCode: 'CS101',
        courseName: 'Introduction to Computer Science',
        date: '2024-12-10',
        startTime: '09:00',
        endTime: '12:00',
        room: 'LH-201',
        building: 'Science Building',
        role: 'instructor' as const,
        status: 'assigned' as const,
      },
      {
        id: 'assign-2',
        examId: 'exam-2',
        courseCode: 'MATH201',
        courseName: 'Calculus II',
        date: '2024-12-12',
        startTime: '14:00',
        endTime: '17:00',
        room: 'EX-101',
        building: 'Engineering Building',
        role: 'lead-invigilator' as const,
        status: 'assigned' as const,
      },
      {
        id: 'assign-3',
        examId: 'exam-3',
        courseCode: 'PHYS150',
        courseName: 'General Physics',
        date: '2024-12-15',
        startTime: '09:00',
        endTime: '11:30',
        room: 'SH-305',
        building: 'Science Hall',
        role: 'invigilator' as const,
        status: 'assigned' as const,
      },
      {
        id: 'assign-4',
        examId: 'exam-4',
        courseCode: 'ENG102',
        courseName: 'English Composition',
        date: '2024-12-18',
        startTime: '10:00',
        endTime: '12:30',
        room: 'LA-204',
        building: 'Liberal Arts Building',
        role: 'invigilator' as const,
        status: 'change-requested' as const,
      },
    ];
    setStaffAssignments(mockStaffAssignments);
  }, [setStaffAssignments]);

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

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'instructor':
        return <GraduationCap className="h-4 w-4" />;
      case 'lead-invigilator':
        return <Shield className="h-4 w-4" />;
      case 'invigilator':
        return <FileEdit className="h-4 w-4" />;
      default:
        return <FileEdit className="h-4 w-4" />;
    }
  };

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'instructor':
        return 'Instructor';
      case 'lead-invigilator':
        return 'Lead Invigilator';
      case 'invigilator':
        return 'Invigilator';
      default:
        return role;
    }
  };

  const getRoleVariant = (role: string) => {
    switch (role) {
      case 'instructor':
        return 'default';
      case 'lead-invigilator':
        return 'secondary';
      case 'invigilator':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'assigned':
        return 'default';
      case 'change-requested':
        return 'secondary';
      case 'confirmed':
        return 'default';
      default:
        return 'outline';
    }
  };

  const handleSubmitChangeRequest = () => {
    if (!selectedAssignment || !changeReason) {
      toast.error('Please select an assignment and reason');
      return;
    }

    const assignment = staffAssignments.find(a => a.id === selectedAssignment);
    if (!assignment) return;

    addChangeRequest({
      staffId: user!.id,
      assignmentId: selectedAssignment,
      courseCode: assignment.courseCode,
      reason: changeReason,
      description: changeDescription.trim() || undefined,
    });

    toast.success('Change request submitted successfully');
    setSelectedAssignment('');
    setChangeReason('');
    setChangeDescription('');
    setIsModalOpen(false);
  };

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

  // Convert StaffAssignment to RenderableExam format for grid view
  const renderableExams: RenderableExam[] = useMemo(() => {
    return staffAssignments.map(assignment => {
      const duration = calculateDurationFromTimes(assignment.startTime, assignment.endTime);
      return {
        id: assignment.id,
        courseCode: assignment.courseCode,
        courseName: assignment.courseName,
        date: assignment.date,
        startTime: assignment.startTime,
        endTime: assignment.endTime,
        duration: duration,
        expectedStudents: 0, // Not available in staff view
        room: assignment.room,
        roomCapacity: 0, // Not available in staff view
        building: assignment.building,
        invigilator: `${getRoleLabel(assignment.role)} - ${user?.name || 'Staff'}`,
        departments: [getDepartmentFromCourseCode(assignment.courseCode)],
        level: 'undergraduate', // Default
        semester: 'fall',
        academicYear: '2024-2025'
      };
    });
  }, [staffAssignments, user?.name]);

  // Extract departments from assignments
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

  // Helper function to calculate duration in minutes
  function calculateDurationFromTimes(startTime: string, endTime: string): number {
    const start = new Date(`1970-01-01T${startTime}:00`);
    const end = new Date(`1970-01-01T${endTime}:00`);
    return Math.floor((end.getTime() - start.getTime()) / (1000 * 60));
  }

  const handleMoveExam = (examId: string, newDate: string, newStartTime: string) => {
    // Staff cannot move exams directly - they need to submit change requests
    toast.error('Staff cannot reschedule assignments directly. Please submit a change request.');
  };

  // Separate assignments by role
  const instructorAssignments = staffAssignments.filter(a => a.role === 'instructor');
  const invigilationAssignments = staffAssignments.filter(a => a.role === 'invigilator' || a.role === 'lead-invigilator');

  // Sort by date
  const sortAssignments = (assignments: typeof staffAssignments) => 
    [...assignments].sort((a, b) => 
      new Date(a.date + ' ' + a.startTime).getTime() - 
      new Date(b.date + ' ' + b.startTime).getTime()
    );

  const AssignmentCard = ({ assignment }: { assignment: typeof staffAssignments[0] }) => (
    <Card key={assignment.id} className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
          <div>
            <CardTitle className="text-lg">
              {assignment.courseCode}
            </CardTitle>
            <p className="text-muted-foreground">
              {assignment.courseName}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={getRoleVariant(assignment.role)}>
              {getRoleIcon(assignment.role)}
              <span className="ml-1">{getRoleLabel(assignment.role)}</span>
            </Badge>
            {assignment.status === 'change-requested' && (
              <Badge variant="secondary">
                Change Requested
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <div className="flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">
              {formatDate(assignment.date)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">
              {formatTime(assignment.startTime)} - {formatTime(assignment.endTime)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">
              {assignment.room}
            </span>
          </div>
        </div>
        <div className="flex items-center justify-between pt-3 border-t border-border">
          <div className="flex items-center gap-2">
            <Building className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              {assignment.building}
            </span>
          </div>
          {assignment.status === 'assigned' && (
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
              <DialogTrigger asChild>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setSelectedAssignment(assignment.id)}
                >
                  Request Change
                </Button>
              </DialogTrigger>
            </Dialog>
          )}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-card border-b border-border">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl">My Assignments</h1>
              <p className="text-muted-foreground">Teaching and Invigilation Duties - Fall 2024</p>
              <p className="text-sm text-muted-foreground">Welcome, {user?.name}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </div>

      {/* Assignment Tabs */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        <Tabs defaultValue="exams-list" className="w-full">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
            <TabsList className="grid w-full lg:w-fit grid-cols-4">
              <TabsTrigger value="exams-list" className="flex items-center gap-1 text-xs">
                <GraduationCap className="h-3 w-3" />
                <List className="h-3 w-3" />
                <span className="hidden sm:inline">Exams List</span>
              </TabsTrigger>
              <TabsTrigger value="exams-grid" className="flex items-center gap-1 text-xs">
                <GraduationCap className="h-3 w-3" />
                <Grid3X3 className="h-3 w-3" />
                <span className="hidden sm:inline">Exams Grid</span>
              </TabsTrigger>
              <TabsTrigger value="invigilation-list" className="flex items-center gap-1 text-xs">
                <Shield className="h-3 w-3" />
                <List className="h-3 w-3" />
                <span className="hidden sm:inline">Duties List</span>
              </TabsTrigger>
              <TabsTrigger value="invigilation-grid" className="flex items-center gap-1 text-xs">
                <Shield className="h-3 w-3" />
                <Grid3X3 className="h-3 w-3" />
                <span className="hidden sm:inline">Duties Grid</span>
              </TabsTrigger>
            </TabsList>
          </div>
          
          <TabsContent value="exams-list" className="mt-0">
            <div className="space-y-4">
              {sortAssignments(instructorAssignments).length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center">
                    <GraduationCap className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3>No Teaching Assignments</h3>
                    <p className="text-muted-foreground">
                      You have no exam proctoring duties as an instructor.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                sortAssignments(instructorAssignments).map((assignment) => (
                  <AssignmentCard key={assignment.id} assignment={assignment} />
                ))
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="exams-grid" className="mt-0">
            <div className="space-y-6">
              <FilterControls
                departments={departments}
                selectedDepartment={selectedDepartment}
                onDepartmentChange={setSelectedDepartment}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
              
              {filteredExams.filter(exam => {
                const assignment = staffAssignments.find(a => a.id === exam.id);
                return assignment?.role === 'instructor';
              }).length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center">
                    <GraduationCap className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3>No Teaching Assignments to Display</h3>
                    <p className="text-muted-foreground">
                      No instructor assignments match the selected filters.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <TimetableGrid 
                  exams={filteredExams.filter(exam => {
                    const assignment = staffAssignments.find(a => a.id === exam.id);
                    return assignment?.role === 'instructor';
                  })}
                  viewMode={viewMode}
                  departments={departments}
                  onMoveExam={handleMoveExam}
                />
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="invigilation-list" className="mt-0">
            <div className="space-y-4">
              {sortAssignments(invigilationAssignments).length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center">
                    <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3>No Invigilation Duties</h3>
                    <p className="text-muted-foreground">
                      You have no assigned invigilation duties.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                sortAssignments(invigilationAssignments).map((assignment) => (
                  <AssignmentCard key={assignment.id} assignment={assignment} />
                ))
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="invigilation-grid" className="mt-0">
            <div className="space-y-6">
              <FilterControls
                departments={departments}
                selectedDepartment={selectedDepartment}
                onDepartmentChange={setSelectedDepartment}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
              
              {filteredExams.filter(exam => {
                const assignment = staffAssignments.find(a => a.id === exam.id);
                return assignment?.role === 'invigilator' || assignment?.role === 'lead-invigilator';
              }).length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center">
                    <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3>No Invigilation Duties to Display</h3>
                    <p className="text-muted-foreground">
                      No invigilation assignments match the selected filters.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <TimetableGrid 
                  exams={filteredExams.filter(exam => {
                    const assignment = staffAssignments.find(a => a.id === exam.id);
                    return assignment?.role === 'invigilator' || assignment?.role === 'lead-invigilator';
                  })}
                  viewMode={viewMode}
                  departments={departments}
                  onMoveExam={handleMoveExam}
                />
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Change Request Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Request Assignment Change</DialogTitle>
            <DialogDescription>
              Submit a request to change your exam assignment. Provide a clear reason for the change request.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {selectedAssignment && (
              <div className="p-3 bg-muted rounded-md">
                <p className="text-sm">
                  <strong>Assignment:</strong> {staffAssignments.find(a => a.id === selectedAssignment)?.courseCode}
                </p>
                <p className="text-sm text-muted-foreground">
                  {staffAssignments.find(a => a.id === selectedAssignment)?.courseName}
                </p>
              </div>
            )}
            <div>
              <Label htmlFor="reason-select">Reason for Change</Label>
              <Select value={changeReason} onValueChange={setChangeReason}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a reason..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="scheduling-conflict">Scheduling Conflict</SelectItem>
                  <SelectItem value="medical-appointment">Medical Appointment</SelectItem>
                  <SelectItem value="personal-emergency">Personal Emergency</SelectItem>
                  <SelectItem value="academic-commitment">Academic Commitment</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="description">Additional Details (Optional)</Label>
              <Textarea
                id="description"
                placeholder="Provide any additional information about your request..."
                value={changeDescription}
                onChange={(e) => setChangeDescription(e.target.value)}
                rows={3}
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={handleSubmitChangeRequest} className="flex-1">
                Submit Request
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
    </div>
  );
}