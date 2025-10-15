// frontend/src/pages/SessionManagement.tsx
import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import {
  ChevronRight, ChevronLeft, Calendar, Upload, FileText, CheckCircle, AlertTriangle, Clock,
  Users, MapPin, Loader2, Building, GraduationCap, Library, ClipboardList, UserCheck,
  CalendarX, Database, ShieldCheck, XCircle, FolderUp, RefreshCw, PlusCircle, Edit, Trash2, BookOpen, UserPlus
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { cn, formatHeader } from '../utils/utils';
import { toast } from 'sonner';
import { useCreateSession, useFileUpload, useSessionSummary, useProcessStagedData, useSeedingStatus, useSessionManager } from '../hooks/useApi';
import { useAppStore } from '../store';
import { StagingDataReviewTable } from '../components/StagingDataReviewTable';
import { SessionDataForm } from '../components/SessionDataForm';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';

// --- Type Definitions ---
interface TimeSlot { start_time: string; end_time: string; name: string; }
export interface SessionSetupCreate { session_name: string; start_date: string; end_date: string; slot_generation_mode: string; time_slots: TimeSlot[]; }
export interface SessionSetupSummary { session_details: Record<string, any>; data_summary: Record<string, any>; validation_results: { warnings: string[]; errors: string[];[key: string]: any; }; }

const statusStyles: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  success: { bg: "bg-green-100", text: "text-green-600", icon: <CheckCircle className="h-4 w-4 text-green-500" /> },
  failed: { bg: "bg-red-100", text: "text-red-600", icon: <XCircle className="h-4 w-4 text-red-500" /> },
  pending: { bg: "bg-gray-100", text: "text-gray-600", icon: null },
  processing: { bg: "bg-blue-100", text: "text-blue-600", icon: <Loader2 className="h-4 w-4 animate-spin text-blue-500" /> }
};

type EditableEntityType = 'courses' | 'buildings' | 'rooms' | 'departments' | 'staff' | 'exams';

// --- UPDATED: Viewer now accepts a Map for efficient lookups ---
const CourseRegistrationsViewer = ({ courses, studentMap }: { courses: any[], studentMap: Map<string, any> }) => {
    if (!courses || courses.length === 0) {
        return <div className="text-center py-8 text-muted-foreground">No courses with student registrations found.</div>;
    }

    return (
        <Accordion type="single" collapsible className="w-full">
            {courses.map(course => (
                <AccordionItem value={course.id} key={course.id}>
                    <AccordionTrigger>
                        <div className="flex items-center justify-between w-full pr-4">
                            <div className="flex flex-col items-start text-left">
                                <span className="font-semibold">{course.code} - {course.title}</span>
                            </div>
                            <Badge variant="secondary">{course.student_ids?.length || 0} Students</Badge>
                        </div>
                    </AccordionTrigger>
                    <AccordionContent>
                        <div className="p-2 bg-muted/50 rounded-md">
                            {course.student_ids && course.student_ids.length > 0 ? (
                                <ul className="list-disc list-inside space-y-1">
                                    {course.student_ids.map((studentId: string) => {
                                        const student = studentMap.get(studentId);
                                        return (
                                            <li key={studentId} className="text-sm">
                                                {student ? `${student.first_name} ${student.last_name} (${student.matric_number})` : `Unknown Student (${studentId.substring(0,8)})`}
                                            </li>
                                        );
                                    })}
                                </ul>
                            ) : (
                                <p className="text-sm text-muted-foreground">No students are registered for this course.</p>
                            )}
                        </div>
                    </AccordionContent>
                </AccordionItem>
            ))}
        </Accordion>
    );
};


const ReadOnlyDataTable = ({ entityType, data }: { entityType: string; data: any[] }) => {
    const columns = useMemo(() => {
        if (!data || data.length === 0) return [];
        return Object.keys(data[0]).filter(key => !key.endsWith('_id') && key.toLowerCase() !== 'id');
    }, [data]);

    if (!data || data.length === 0) {
        return <div className="text-center py-8 text-muted-foreground">No data available for {formatHeader(entityType)}.</div>;
    }

    return (
        <div className="border rounded-lg overflow-auto max-h-[60vh]">
            <Table>
                <TableHeader className="sticky top-0 bg-background z-10"><TableRow>{columns.map(col => <TableHead key={col}>{formatHeader(col)}</TableHead>)}</TableRow></TableHeader>
                <TableBody>{data.map((row, index) => <TableRow key={row.id || index}>{columns.map(col => <TableCell key={col}>{String(row[col] ?? '')}</TableCell>)}</TableRow>)}</TableBody>
            </Table>
        </div>
    );
};

const LiveEntityDataTable = ({ entityType, data, dataGraph, onAdd, onEdit, onDelete }: {
  entityType: EditableEntityType;
  data: any[];
  dataGraph: any;
  onAdd: () => void;
  onEdit: (record: any) => void;
  onDelete: (record: any) => void;
}) => {
    const columns = useMemo(() => {
        if (data.length === 0) return [];
        const allKeys = Object.keys(data[0]);
        const filteredKeys = allKeys.filter(key => !key.endsWith('_id') && key.toLowerCase() !== 'id');
        const preferredOrder = ['code', 'name', 'title', 'staff_number', 'first_name', 'last_name', 'department_name', 'building_name', 'capacity', 'exam_capacity', 'can_invigilate'];
        return filteredKeys.sort((a, b) => {
            const indexA = preferredOrder.indexOf(a);
            const indexB = preferredOrder.indexOf(b);
            if (indexA !== -1 && indexB !== -1) return indexA - indexB;
            if (indexA !== -1) return -1;
            if (indexB !== -1) return 1;
            return a.localeCompare(b);
        });
    }, [data]);

    const renderCellContent = (row: any, col: string) => {
        const value = row[col];
        if (col === 'building_name' && entityType === 'rooms' && dataGraph?.buildings) {
            const building = dataGraph.buildings.find((b: any) => b.id === row.building_id);
            return building ? building.name : 'Unknown';
        }
        if (col === 'department_name' && (entityType === 'courses' || entityType === 'staff') && dataGraph?.departments) {
            const department = dataGraph.departments.find((d: any) => d.id === row.department_id);
            return department ? department.name : 'Unknown';
        }
        if (typeof value === 'boolean') {
            return <Badge variant={value ? 'default' : 'secondary'}>{value ? 'Yes' : 'No'}</Badge>;
        }
        return String(value ?? '');
    };

    return (
        <div className="space-y-4">
            <div className="flex justify-end">
                <Button onClick={onAdd}><PlusCircle className="h-4 w-4 mr-2" />Add New {formatHeader(entityType).slice(0, -1)}</Button>
            </div>
            <div className="border rounded-lg overflow-auto max-h-[60vh]">
                <Table>
                    <TableHeader className="sticky top-0 bg-background z-10"><TableRow>{columns.map(col => <TableHead key={col}>{formatHeader(col)}</TableHead>)}<TableHead>Actions</TableHead></TableRow></TableHeader>
                    <TableBody>
                        {data.map((row) => (
                            <TableRow key={row.id}>
                                {columns.map(col => <TableCell key={col}>{renderCellContent(row, col)}</TableCell>)}
                                <TableCell>
                                    <div className="flex space-x-2">
                                        <Button variant="ghost" size="icon" onClick={() => onEdit(row)}><Edit className="h-4 w-4" /></Button>
                                        <Button variant="ghost" size="icon" onClick={() => onDelete(row)}><Trash2 className="h-4 w-4" /></Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
};

const ActiveSessionManager = ({ sessionId, onStartNewSession }: { sessionId: string; onStartNewSession: () => void; }) => {
  const { activeSessionName } = useAppStore();
  const { dataGraph, isLoading, error, createEntity, updateEntity, deleteEntity, paginatedData, isPaginating, fetchPaginatedEntities } = useSessionManager(sessionId);
  
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<any | null>(null);
  const [currentEntityType, setCurrentEntityType] = useState<EditableEntityType | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  
  const [studentCache, setStudentCache] = useState<any[]>([]);
  const studentMap = useMemo(() => new Map(studentCache.map(s => [s.id, s])), [studentCache]);

  // MOVED HOOK TO THE TOP LEVEL
  const studentData = paginatedData.student;
  const studentColumns = useMemo(() => {
    if (!studentData?.items || studentData.items.length === 0) return [];
    return Object.keys(studentData.items[0]).filter(key => !key.endsWith('_id') && key.toLowerCase() !== 'id');
  }, [studentData?.items]);

  useEffect(() => {
    if (sessionId) {
      fetchPaginatedEntities('student', { page: 1, page_size: 50 });
    }
  }, [sessionId, fetchPaginatedEntities]);

  useEffect(() => {
    const newStudents = paginatedData.student?.items;
    if (newStudents && newStudents.length > 0) {
      setStudentCache(prevCache => {
        const existingIds = new Set(prevCache.map(s => s.id));
        const uniqueNewStudents = newStudents.filter(s => !existingIds.has(s.id));
        return [...prevCache, ...uniqueNewStudents];
      });
    }
  }, [paginatedData.student]);


  const toSingularEntityType = (plural: EditableEntityType): 'course' | 'building' | 'room' | 'department' | 'staff' | 'exam' => {
      if (plural === 'staff') return 'staff';
      return plural.slice(0, -1) as 'course' | 'building' | 'room' | 'department' | 'exam';
  };

  const handleAdd = (entityType: EditableEntityType) => {
    setCurrentEntityType(entityType);
    setSelectedRecord({});
    setIsEditing(false);
    setIsFormOpen(true);
  };

  const handleEdit = (entityType: EditableEntityType, record: any) => {
    setCurrentEntityType(entityType);
    setSelectedRecord(record);
    setIsEditing(true);
    setIsFormOpen(true);
  };

  const handleDelete = (entityType: EditableEntityType, record: any) => {
    setCurrentEntityType(entityType);
    setSelectedRecord(record);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (selectedRecord && currentEntityType) {
      await deleteEntity(toSingularEntityType(currentEntityType), selectedRecord.id);
      setIsDeleteDialogOpen(false);
      setSelectedRecord(null);
    }
  };

  const handleSave = async (formData: any) => {
    if (currentEntityType) {
      const singularType = toSingularEntityType(currentEntityType);
      if (await (isEditing ? updateEntity(singularType, selectedRecord.id, formData) : createEntity(singularType, formData))) {
        setIsFormOpen(false);
        setSelectedRecord(null);
      }
    }
  };

  const handleStudentPageChange = (newPage: number) => {
    fetchPaginatedEntities('student', { page: newPage, page_size: 50 });
  };

  // CONDITIONAL RETURNS ARE NOW AFTER ALL HOOKS
  if (isLoading) return <div className="flex justify-center items-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  if (error) return <Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertDescription>{error.message}</AlertDescription></Alert>;
  if (!dataGraph) return <div className="text-center py-8 text-muted-foreground">No data found for this session.</div>;

  const entities = [
      { type: 'courses', icon: BookOpen, data: dataGraph.courses || [] },
      { type: 'students', icon: GraduationCap, data: dataGraph.students || [] }, 
      { type: 'registrations', icon: ClipboardList, data: [] }, 
      { type: 'staff', icon: Users, data: dataGraph.staff || [] },
      { type: 'departments', icon: Library, data: dataGraph.departments || [] },
      { type: 'buildings', icon: Building, data: dataGraph.buildings || [] },
      { type: 'rooms', icon: MapPin, data: dataGraph.rooms || [] },
      { type: 'exams', icon: FileText, data: dataGraph.exams || [] },
  ];

  const editableEntities: EditableEntityType[] = ['courses', 'buildings', 'rooms', 'departments', 'staff', 'exams'];
    
  return (
    <div className="space-y-6">
        <div className="flex items-center justify-between">
            <div><h1 className="text-2xl font-semibold">Session Management</h1><p className="text-muted-foreground">Manage live data for the active session: <span className="font-medium text-primary">{activeSessionName}</span></p></div>
            <Button onClick={onStartNewSession} variant="outline"><PlusCircle className="h-4 w-4 mr-2" />Create New Session</Button>
        </div>
        <Card>
            <CardHeader><CardTitle>Session Data</CardTitle><CardDescription>View and manage all data associated with this session.</CardDescription></CardHeader>
            <CardContent>
                <Tabs defaultValue="courses">
                    <TabsList className="flex-wrap h-auto">{entities.map(e => <TabsTrigger key={e.type} value={e.type}><e.icon className="h-4 w-4 mr-2"/>{formatHeader(e.type)}</TabsTrigger>)}</TabsList>
                    {entities.map(e => (
                        <TabsContent key={e.type} value={e.type} className="mt-4">
                           {e.type === 'registrations' ? (
                                <CourseRegistrationsViewer courses={dataGraph.courses || []} studentMap={studentMap} />
                           ) : e.type === 'students' ? (
                                <div className="space-y-4">
                                    <div className="border rounded-lg overflow-auto max-h-[60vh]">
                                        <Table>
                                            <TableHeader className="sticky top-0 bg-background z-10"><TableRow>{studentColumns.map(col => <TableHead key={col}>{formatHeader(col)}</TableHead>)}</TableRow></TableHeader>
                                            <TableBody>
                                                {isPaginating && (!studentData || studentData.items.length === 0) ? (
                                                    <TableRow><TableCell colSpan={studentColumns.length} className="h-24 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin" /></TableCell></TableRow>
                                                ) : studentData?.items.map((row: any, index: number) => <TableRow key={row.id || index}>{studentColumns.map(col => <TableCell key={col}>{String(row[col] ?? '')}</TableCell>)}</TableRow>)}
                                            </TableBody>
                                        </Table>
                                    </div>
                                    <div className="flex items-center justify-end space-x-2">
                                        <span className="text-sm text-muted-foreground">
                                            Page {studentData?.pagination?.page || 1} of {studentData?.pagination?.total_pages || 1}
                                        </span>
                                        <Button variant="outline" size="sm" onClick={() => handleStudentPageChange((studentData?.pagination?.page || 1) - 1)} disabled={(studentData?.pagination?.page || 1) <= 1 || isPaginating}><ChevronLeft className="h-4 w-4" />Previous</Button>
                                        <Button variant="outline" size="sm" onClick={() => handleStudentPageChange((studentData?.pagination?.page || 1) + 1)} disabled={(studentData?.pagination?.page || 1) >= (studentData?.pagination?.total_pages || 1) || isPaginating}>Next<ChevronRight className="h-4 w-4" /></Button>
                                    </div>
                                </div>
                            ) : editableEntities.includes(e.type as any) ? (
                                <LiveEntityDataTable 
                                    entityType={e.type as EditableEntityType} 
                                    data={e.data} dataGraph={dataGraph}
                                    onAdd={() => handleAdd(e.type as EditableEntityType)}
                                    onEdit={(record) => handleEdit(e.type as EditableEntityType, record)}
                                    onDelete={(record) => handleDelete(e.type as EditableEntityType, record)}
                                />
                            ) : (
                                <ReadOnlyDataTable entityType={e.type} data={e.data} />
                            )}
                        </TabsContent>
                    ))}
                </Tabs>
            </CardContent>
        </Card>

        <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}><DialogContent className="max-w-3xl">
            <DialogHeader><DialogTitle>{isEditing ? 'Edit' : 'Create'} {formatHeader(currentEntityType || '')}</DialogTitle></DialogHeader>
            {selectedRecord && currentEntityType && <SessionDataForm key={`${currentEntityType}-${selectedRecord.id || 'new'}`} entityType={currentEntityType} initialData={selectedRecord} dataGraph={dataGraph} onSave={handleSave} onCancel={() => setIsFormOpen(false)} />}
        </DialogContent></Dialog>
        
        <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Are you sure?</AlertDialogTitle><AlertDialogDescription>This will permanently delete the record.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={handleConfirmDelete}>Continue</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
    </div>
  );
};

// --- Session Creation Wizard Component ---
const SessionSetupWizard = ({ onSessionCreated, onCancel }: { onSessionCreated: () => void; onCancel: () => void; }) => {
    const { activeSessionId: existingSessionId } = useAppStore.getState();
    const [currentStep, setCurrentStep] = useState(1);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const { mutateAsync: createSession, isPending: isCreatingSession } = useCreateSession();
    const { mutateAsync: uploadFiles, isPending: isUploading } = useFileUpload();
    const { data: summaryData, isLoading: isLoadingSummary, refetch: refetchSummary } = useSessionSummary(sessionId);
    const { mutateAsync: processData, isPending: isProcessing } = useProcessStagedData();
    const [isPolling, setIsPolling] = useState(false);
    const { data: seedingStatus, refetch: refetchSeedingStatus } = useSeedingStatus(sessionId);
    const [isSummaryRefetching, setIsSummaryRefetching] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [uploadResults, setUploadResults] = useState<Record<string, { status: string; message?: string; fileName?: string }>>({});
    const [sessionData, setSessionData] = useState({
        name: '25C SEMESTER EXAM', startDate: '2025-12-01', endDate: '2025-12-12', slotGenerationMode: 'flexible',
        timeSlots: [{ id: '1', startTime: '09:00', endTime: '12:00', name: 'Morning' }, { id: '2', startTime: '12:00', endTime: '15:00', name: 'Afternoon' }, { id: '3', startTime: '15:00', endTime: '18:00', name: 'Evening' }]
    });

    const durationInDays = useMemo(() => {
        if (!sessionData.startDate || !sessionData.endDate) return 0;
        const diff = Math.round((new Date(sessionData.endDate).getTime() - new Date(sessionData.startDate).getTime()) / (1000 * 60 * 60 * 24)) + 1;
        return diff > 0 ? diff : 0;
    }, [sessionData.startDate, sessionData.endDate]);
    
    useEffect(() => { if (currentStep === 5 && sessionId) refetchSummary(); }, [currentStep, sessionId, refetchSummary]);
    useEffect(() => { if (!isPolling || !sessionId) return; const intervalId = setInterval(() => refetchSeedingStatus(), 3000); return () => clearInterval(intervalId); }, [isPolling, sessionId, refetchSeedingStatus]);
    
    const requiredFiles = useMemo(() => [
        { key: 'faculties', name: 'Faculties', icon: Library, required: true }, { key: 'departments', name: 'Departments', icon: Building, required: true }, { key: 'programmes', name: 'Programmes', icon: GraduationCap, required: true },
        { key: 'buildings', name: 'Buildings', icon: Building, required: true }, { key: 'rooms', name: 'Rooms', icon: MapPin, required: true }, { key: 'courses', name: 'Courses', icon: FileText, required: true },
        { key: 'staff', name: 'Staff', icon: Users, required: true }, { key: 'students', name: 'Students', icon: Users, required: true }, { key: 'course_registrations', name: 'Course Registrations', icon: ClipboardList, required: true },
        { key: 'course_instructors', name: 'Course Instructors', icon: UserCheck, required: true }, { key: 'staff_unavailability', name: 'Staff Unavailability', icon: CalendarX, required: false }
    ], []);

    useEffect(() => {
        if (!seedingStatus?.files) return;
        const newUploadResults: typeof uploadResults = {}; let allDone = true;
        const requiredFileKeys = new Set(requiredFiles.map(f => f.key));
        seedingStatus.files.forEach((file: any) => {
            const uiStatus = file.status === 'completed' ? 'success' : file.status;
            newUploadResults[file.upload_type] = { status: uiStatus, fileName: file.file_name, message: file.validation_errors?.error };
            if (requiredFileKeys.has(file.upload_type) && (uiStatus === 'pending' || uiStatus === 'processing')) allDone = false;
        });
        setUploadResults(prev => ({...prev, ...newUploadResults}));
        const allTrackedFiles = Object.keys(uploadResults).filter(key => requiredFileKeys.has(key));
        if (allTrackedFiles.length > 0 && allTrackedFiles.every(key => newUploadResults[key]?.status === 'success' || newUploadResults[key]?.status === 'failed')) allDone = true;
        if (allDone && allTrackedFiles.length > 0) { setIsPolling(false); toast.info("File processing complete."); }
    }, [seedingStatus, uploadResults, requiredFiles]);
    
    const steps = [{ id: 1, name: 'Define Session', icon: Calendar }, { id: 2, name: 'Schedule Structure', icon: Clock }, { id: 3, name: 'Upload Data', icon: Upload }, { id: 4, name: 'Review & Edit Data', icon: Database }, { id: 5, name: 'Summary & Finish', icon: ShieldCheck }];
    
    const uploadedEntityTypes = useMemo(() => Object.entries(uploadResults).filter(([, result]) => result.status === 'success').map(([key]) => key), [uploadResults]);
    
    const isStepValid = (step: number) => {
        switch (step) {
            case 1: return !!(sessionData.name && sessionData.startDate && sessionData.endDate && durationInDays > 0);
            case 2: return sessionData.timeSlots.every(ts => ts.startTime && ts.endTime);
            case 3: return requiredFiles.filter(f => f.required).every(f => uploadResults[f.key]?.status === 'success');
            case 4: return true;
            case 5: return !!summaryData && summaryData.validation_results.errors.length === 0;
            default: return false;
        }
    };

    const handleNextStep = async () => {
        if (!isStepValid(currentStep)) return;
        if (currentStep === 2) {
            try {
                const result = await createSession({ session_name: sessionData.name, start_date: sessionData.startDate, end_date: sessionData.endDate, slot_generation_mode: sessionData.slotGenerationMode, time_slots: sessionData.timeSlots.map(({ startTime, endTime, name }) => ({ start_time: startTime, end_time: endTime, name })) });
                if (result.success && result.data?.academic_session_id) { setSessionId(result.data.academic_session_id); setCurrentStep(3); } else { toast.error("Failed to create session.", { description: result.message }); }
            } catch (error) {}
        } else if (currentStep < 5) {
            setCurrentStep(currentStep + 1);
        }
    };

    const prevStep = () => { if (currentStep > 1) setCurrentStep(currentStep - 1); };
    const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => { if (event.target.files) setSelectedFiles(Array.from(event.target.files)); };
    const handleBatchUpload = async () => {
        if (selectedFiles.length === 0 || !sessionId) return;
        try {
            const result = await uploadFiles({ files: selectedFiles, academicSessionId: sessionId });
            const newResults: typeof uploadResults = {};
            result.dispatched_tasks.forEach((file: any) => { newResults[file.entity_type] = { status: 'processing', fileName: file.file_name }; });
            result.failed_files.forEach((file: any) => { if (file.entity_type) { newResults[file.entity_type] = { status: 'failed', message: file.error, fileName: file.file_name }; } else { toast.error(`File upload failed: ${file.file_name}`, { description: file.error }); }});
            setUploadResults(prev => ({ ...prev, ...newResults }));
            setSelectedFiles([]);
            if (fileInputRef.current) fileInputRef.current.value = "";
            setIsPolling(true);
        } catch (error) {}
    };

    const handleProcessData = async () => { if (!sessionId) return; try { const result = await processData({ sessionId }); if (result.success) { toast.success('Session setup complete!', { description: 'All data processed. You can now manage the session.' }); onSessionCreated(); } } catch (error) {} };
    const handleManualSummaryRefresh = async () => { setIsSummaryRefetching(true); await refetchSummary(); setIsSummaryRefetching(false); };

    const renderStepContent = () => {
        switch (currentStep) {
            case 1: return <Card><CardHeader><CardTitle>Exam Session Information</CardTitle><CardDescription>Define the basic period and name for this exam session.</CardDescription></CardHeader><CardContent className="space-y-4 pt-6"><div className="space-y-2"><Label htmlFor="session-name">Session Name</Label><Input id="session-name" placeholder="e.g., Fall 2025 Final Exams" value={sessionData.name} onChange={(e) => setSessionData(prev => ({ ...prev, name: e.target.value }))} /></div><div className="grid grid-cols-1 md:grid-cols-2 gap-4"><div className="space-y-2"><Label htmlFor="start-date">Start Date</Label><Input id="start-date" type="date" value={sessionData.startDate} onChange={(e) => setSessionData(prev => ({ ...prev, startDate: e.target.value }))} /></div><div className="space-y-2"><Label htmlFor="end-date">End Date</Label><Input id="end-date" type="date" value={sessionData.endDate} onChange={(e) => setSessionData(prev => ({ ...prev, endDate: e.target.value }))} /></div></div>{durationInDays > 0 && (<Alert variant={durationInDays < 7 || durationInDays > 21 ? 'destructive' : 'default'}><Calendar className="h-4 w-4" /><AlertDescription>This session will span {durationInDays} days.</AlertDescription></Alert>)}</CardContent></Card>;
            case 2: return <Card><CardHeader><CardTitle>Schedule Structure</CardTitle><CardDescription>Configure the daily time slots for your exam session.</CardDescription></CardHeader><CardContent className="space-y-6 pt-6"><div className="w-full md:w-1/2"><Label>Slot Generation Mode</Label><Select value={sessionData.slotGenerationMode} onValueChange={(value) => setSessionData(prev => ({...prev, slotGenerationMode: value}))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="flexible">Flexible</SelectItem><SelectItem value="fixed">Fixed</SelectItem></SelectContent></Select></div><h4 className="font-medium">Daily Time Slots</h4><div className="space-y-3">{sessionData.timeSlots.map((slot, index) => (<div key={index} className="flex items-center space-x-3 p-3 border rounded-lg"><div className="flex-1 grid grid-cols-3 gap-3"><div><Label className="text-xs">Slot Name</Label><Input placeholder="e.g., Morning" value={slot.name} onChange={(e) => setSessionData(prev => ({...prev, timeSlots: prev.timeSlots.map((s, i) => i === index ? {...s, name: e.target.value} : s)}))} /></div><div><Label className="text-xs">Start Time</Label><Input type="time" value={slot.startTime} onChange={(e) => setSessionData(prev => ({...prev, timeSlots: prev.timeSlots.map((s, i) => i === index ? {...s, startTime: e.target.value} : s)}))} /></div><div><Label className="text-xs">End Time</Label><Input type="time" value={slot.endTime} onChange={(e) => setSessionData(prev => ({...prev, timeSlots: prev.timeSlots.map((s, i) => i === index ? {...s, endTime: e.target.value} : s)}))} /></div></div></div>))}</div></CardContent></Card>;
            case 3: return <Card><CardHeader><CardTitle>Batch Data Upload</CardTitle><CardDescription>Select all required CSV files.</CardDescription></CardHeader><CardContent className="space-y-4 pt-6"><div className="p-6 border-2 border-dashed rounded-lg text-center"><FolderUp className="mx-auto h-12 w-12 text-gray-400" /><Label htmlFor="file-upload" className="mt-2 block font-medium text-primary cursor-pointer hover:underline">{selectedFiles.length > 0 ? `${selectedFiles.length} files selected` : 'Choose files to upload'}</Label><p className="mt-1 text-xs text-muted-foreground">Select multiple CSV files</p><input id="file-upload" ref={fileInputRef} type="file" multiple onChange={handleFileSelection} accept=".csv" className="sr-only" /></div>{selectedFiles.length > 0 && (<div className="space-y-2"><h4 className="font-medium">Selected:</h4><ul className="list-disc list-inside text-sm text-muted-foreground">{selectedFiles.map(f => <li key={f.name}>{f.name}</li>)}</ul><Button onClick={handleBatchUpload} disabled={isUploading}>{isUploading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Uploading...</> : `Upload ${selectedFiles.length} Files`}</Button></div>)}<div className="space-y-2 pt-4"><h4 className="font-medium">Upload Status:</h4>{requiredFiles.map((file) => { const result = uploadResults[file.key]; const status = result?.status || 'pending'; const style = statusStyles[status]; return (<div key={file.key} className="flex items-center justify-between p-3 border rounded-lg"><div className="flex items-center space-x-3"><div className={cn("p-2 rounded-full", style.bg)}><file.icon className={cn("h-4 w-4", style.text)} /></div><div><div className="flex items-center space-x-2"><h4 className="font-medium">{file.name}</h4>{file.required && <Badge variant="destructive">Required</Badge>}{style.icon}</div><p className="text-sm text-muted-foreground">{result?.fileName || 'Awaiting file...'}</p>{status === 'failed' && <p className="text-xs text-red-600">{result?.message}</p>}</div></div></div>);})}</div></CardContent></Card>;
            case 4: return <Card><CardHeader><CardTitle>Review & Edit Staged Data</CardTitle><CardDescription>Correct individual records before final processing.</CardDescription></CardHeader><CardContent>{sessionId ? <StagingDataReviewTable sessionId={sessionId} uploadedEntityTypes={uploadedEntityTypes} /> : <Alert variant="destructive">Session ID is missing.</Alert>}</CardContent></Card>;
            case 5: return <div className="space-y-6">{isLoadingSummary ? <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 animate-spin" /></div> : !summaryData ? <Card><CardContent className="py-8 text-center"><p>Could not load summary.</p><Button onClick={handleManualSummaryRefresh} variant="outline" className="mt-4" disabled={isSummaryRefetching}><RefreshCw className={`h-4 w-4 mr-2 ${isSummaryRefetching ? 'animate-spin' : ''}`} />Try Again</Button></CardContent></Card> : <><Card><CardHeader><div className="flex justify-between items-center"><div><CardTitle>Final Summary</CardTitle></div><Button onClick={handleManualSummaryRefresh} variant="outline" size="sm" disabled={isSummaryRefetching}><RefreshCw className={`h-4 w-4 mr-2 ${isSummaryRefetching ? 'animate-spin' : ''}`} />Refresh</Button></div></CardHeader><CardContent className="space-y-4 pt-6"><div className="grid md:grid-cols-2 gap-4"><div><h4 className="font-medium mb-2">Session Details</h4><div className="text-sm"><div><span className="text-muted-foreground">Name:</span> {summaryData.session_details.name}</div><div><span className="text-muted-foreground">Period:</span> {new Date(summaryData.session_details.start_date).toLocaleDateString()} to {new Date(summaryData.session_details.end_date).toLocaleDateString()}</div></div></div><div><h4 className="font-medium mb-2">Data Summary</h4><div className="text-sm">{Object.entries(summaryData.data_summary).map(([key, value]) => (<div key={key}><span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}:</span> {value as any}</div>))}</div></div></div></CardContent></Card><Card><CardHeader><CardTitle className="flex items-center">{summaryData.validation_results.errors.length === 0 ? <CheckCircle className="h-5 w-5 mr-2 text-green-500" /> : <AlertTriangle className="h-5 w-5 mr-2 text-red-500" />}Validation Results</CardTitle></CardHeader><CardContent className="space-y-4">{summaryData.validation_results.errors.length > 0 && <Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertDescription><div className="font-medium mb-2">Errors:</div><ul className="list-disc list-inside">{summaryData.validation_results.errors.map((e, i) => <li key={i}>{e}</li>)}</ul></AlertDescription></Alert>}{summaryData.validation_results.warnings.length > 0 && <Alert><AlertTriangle className="h-4 w-4" /><AlertDescription><div className="font-medium mb-2">Warnings:</div><ul className="list-disc list-inside">{summaryData.validation_results.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></AlertDescription></Alert>}{summaryData.validation_results.errors.length === 0 && <Alert><CheckCircle className="h-4 w-4" /><AlertDescription>All checks passed.</AlertDescription></Alert>}</CardContent></Card></>}</div>;
            default: return null;
        }
    };

    return (
        <div className="space-y-6">
             <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-semibold">Create New Exam Session</h1>
                    {existingSessionId && (
                        <Button variant="link" className="p-0 h-auto text-muted-foreground" onClick={onCancel}>
                            <ChevronLeft className="h-4 w-4 mr-1" />
                            Back to Session Management
                        </Button>
                    )}
                </div>
                <div className="flex items-center space-x-2">
                    <span className="text-sm text-muted-foreground">Step {currentStep} of {steps.length}</span>
                    <Progress value={(currentStep / steps.length) * 100} className="w-24" />
                </div>
            </div>
            <Card><CardContent className="p-6"><div className="flex items-center justify-between">{steps.map((step, index) => <React.Fragment key={step.id}><div className="flex flex-col items-center space-y-2 text-center"><div className={cn("w-10 h-10 rounded-full flex items-center justify-center border-2", currentStep === step.id && "border-primary text-primary", currentStep > step.id && "bg-primary border-primary text-primary-foreground", currentStep < step.id && "border-muted-foreground text-muted-foreground")}><step.icon className="h-5 w-5" /></div><div className={cn("text-sm font-medium", currentStep === step.id && "text-primary")}>{step.name}</div></div>{index < steps.length - 1 && <div className={cn("flex-1 h-0.5 mx-4", currentStep > step.id ? "bg-primary" : "bg-muted")} />}</React.Fragment>)}</div></CardContent></Card>
            <div className="min-h-[30rem]">{renderStepContent()}</div>
            <div className="flex items-center justify-between"><Button variant="outline" onClick={prevStep} disabled={currentStep === 1 || isCreatingSession || isUploading || isProcessing}><ChevronLeft className="h-4 w-4 mr-2" />Previous</Button><div className="flex space-x-3">{currentStep < 5 && <Button onClick={handleNextStep} disabled={!isStepValid(currentStep) || isCreatingSession}>{isCreatingSession ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Creating...</> : <>Next<ChevronRight className="h-4 w-4 ml-2" /></>}</Button>}{currentStep === 5 && <Button onClick={handleProcessData} disabled={!isStepValid(5) || isLoadingSummary || isProcessing}>{isProcessing ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Processing...</> : <>Process & Finish<ChevronRight className="h-4 w-4 ml-2" /></>}</Button>}</div></div>
        </div>
    );
};

// --- Main Exported Component ---
export function SessionManagement() {
  const { activeSessionId, initializeApp } = useAppStore();
  const [isCreatingNew, setIsCreatingNew] = useState(!activeSessionId);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    // Simulate a brief moment for the app to initialize
    setTimeout(() => {
      const currentSession = useAppStore.getState().activeSessionId;
      setIsCreatingNew(!currentSession);
      setIsLoading(false);
    }, 500);
  }, [activeSessionId]);

  const handleSessionCreated = useCallback(() => {
    initializeApp().then(() => setIsCreatingNew(false));
  }, [initializeApp]);

  const handleCancelCreation = () => {
    if (activeSessionId) {
      setIsCreatingNew(false);
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-[calc(100vh-200px)]"><Loader2 className="h-12 w-12 animate-spin text-primary" /></div>;
  }

  if (isCreatingNew) {
    return <SessionSetupWizard onSessionCreated={handleSessionCreated} onCancel={handleCancelCreation} />;
  }
  
  // Render the manager for the active session
  return <ActiveSessionManager sessionId={activeSessionId!} onStartNewSession={() => setIsCreatingNew(true)} />;
}