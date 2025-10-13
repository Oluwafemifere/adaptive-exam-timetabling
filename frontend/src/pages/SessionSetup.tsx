// frontend/src/pages/SessionSetup.tsx
import React, { useState, useMemo, useRef, useEffect } from 'react';
import { 
  ChevronRight, 
  ChevronLeft,
  Calendar,
  Upload,
  FileText,
  CheckCircle,
  AlertTriangle,
  Clock,
  Users,
  MapPin,
  Loader2,
  Building,
  GraduationCap,
  Library,
  ClipboardList,
  UserCheck,
  CalendarX,
  Database,
  ShieldCheck,
  XCircle,
  FolderUp,
  RefreshCw,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { cn, formatHeader } from '../utils/utils'; 
import { toast } from 'sonner';
import { useCreateSession, useFileUpload, useSessionSummary, useProcessStagedData, useSeedingStatus } from '../hooks/useApi';
import { useAppStore } from '../store';
import { StagingDataReviewTable } from '../components/StagingDataReviewTable'; 

// --- Type Definitions ---
interface TimeSlot {
  start_time: string;
  end_time: string;
  name: string;
}

export interface SessionSetupCreate {
  session_name: string;
  start_date: string;
  end_date: string;
  slot_generation_mode: string;
  time_slots: TimeSlot[];
}

export interface SessionSetupSummary {
  session_details: Record<string, any>;
  data_summary: Record<string, any>;
  validation_results: {
    warnings: string[];
    errors: string[];
    [key: string]: any;
  };
}

// --- Status-to-Style Mapping Object (Fixes TS Error) ---
const statusStyles = {
    success: {
        bg: "bg-green-100",
        text: "text-green-600",
        icon: <CheckCircle className="h-4 w-4 text-green-500" />
    },
    failed: {
        bg: "bg-red-100",
        text: "text-red-600",
        icon: <XCircle className="h-4 w-4 text-red-500" />
    },
    pending: {
        bg: "bg-gray-100",
        text: "text-gray-600",
        icon: null
    },
    processing: {
        bg: "bg-blue-100",
        text: "text-blue-600",
        icon: <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
    }
};

// Component
export function SessionSetup() {
  const { setCurrentPage } = useAppStore();
  const [currentStep, setCurrentStep] = useState(1);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // API Hooks
  const { mutateAsync: createSession, isPending: isCreatingSession } = useCreateSession();
  const { mutateAsync: uploadFiles, isPending: isUploading } = useFileUpload();
  const { data: summaryData, isLoading: isLoadingSummary, refetch: refetchSummary } = useSessionSummary(sessionId);
  const { mutateAsync: processData, isPending: isProcessing } = useProcessStagedData();

  // State and hook for polling file upload status
  const [isPolling, setIsPolling] = useState(false);
  const { data: seedingStatus, refetch: refetchSeedingStatus } = useSeedingStatus(sessionId);
  
  // New state for summary refresh
  const [isSummaryRefetching, setIsSummaryRefetching] = useState(false);

  // File Upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadResults, setUploadResults] = useState<Record<string, { status: 'success' | 'failed' | 'processing' | 'pending'; message?: string; fileName?: string }>>({});
  
  // Form State
  const [sessionData, setSessionData] = useState({
    name: '25C SEMESTER EXAM',
    startDate: '2025-12-01',
    endDate: '2025-12-12',
    slotGenerationMode: 'flexible',
    timeSlots: [
      { id: '1', startTime: '09:00', endTime: '12:00', name: 'Morning' },
      { id: '2', startTime: '12:00', endTime: '15:00', name: 'Afternoon' },
      { id: '3', startTime: '15:00', endTime: '18:00', name: 'Evening' },
    ]
  });
  
  const durationInDays = useMemo(() => {
    if (!sessionData.startDate || !sessionData.endDate) return 0;
    const start = new Date(sessionData.startDate);
    const end = new Date(sessionData.endDate);
    const diff = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    return diff > 0 ? diff : 0;
  }, [sessionData.startDate, sessionData.endDate]);
  
  useEffect(() => {
    if (currentStep === 5 && sessionId) {
      refetchSummary();
    }
  }, [currentStep, sessionId, refetchSummary]);

  // Effect to handle polling for file status updates
  useEffect(() => {
    if (!isPolling || !sessionId) return;

    const intervalId = setInterval(() => {
      refetchSeedingStatus();
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(intervalId);
  }, [isPolling, sessionId, refetchSeedingStatus]);

  // Effect to process polling results and update the UI
  useEffect(() => {
    if (!seedingStatus?.files) return;

    const newUploadResults: typeof uploadResults = {};
    let allDone = true;
    const requiredFileKeys = new Set(requiredFiles.map(f => f.key));

    seedingStatus.files.forEach((file: any) => {
        const uiStatus = file.status === 'completed' ? 'success' : file.status;
        
        newUploadResults[file.upload_type] = {
            status: uiStatus,
            fileName: file.file_name,
            message: file.validation_errors?.error
        };
        
        if (requiredFileKeys.has(file.upload_type) && (uiStatus === 'pending' || uiStatus === 'processing')) {
            allDone = false;
        }
    });

    setUploadResults(prev => ({...prev, ...newUploadResults}));

    const allTrackedFiles = Object.keys(uploadResults).filter(key => requiredFileKeys.has(key));
    if (allTrackedFiles.length > 0 && allTrackedFiles.every(key => newUploadResults[key]?.status === 'success' || newUploadResults[key]?.status === 'failed')) {
        allDone = true;
    }

    if (allDone && allTrackedFiles.length > 0) {
      setIsPolling(false);
      toast.info("File processing complete. You may now proceed.");
    }
  }, [seedingStatus]);
  
  const steps = [
    { id: 1, name: 'Define Session', icon: Calendar },
    { id: 2, name: 'Schedule Structure', icon: Clock },
    { id: 3, name: 'Upload Data', icon: Upload },
    { id: 4, name: 'Review & Edit Data', icon: Database },
    { id: 5, name: 'Summary & Finish', icon: ShieldCheck },
  ];

  const requiredFiles = [
    { key: 'faculties', name: 'Faculties', description: 'Faculty names and codes', icon: Library, required: true },
    { key: 'departments', name: 'Departments', description: 'Department details and faculty relations', icon: Building, required: true },
    { key: 'programmes', name: 'Programmes', description: 'Academic programmes and departments', icon: GraduationCap, required: true },
    { key: 'buildings', name: 'Buildings', description: 'Building names and locations', icon: Building, required: true },
    { key: 'rooms', name: 'Rooms', description: 'Room capacities and building relations', icon: MapPin, required: true },
    { key: 'courses', name: 'Courses', description: 'Course codes, names, and departments', icon: FileText, required: true },
    { key: 'staff', name: 'Staff', description: 'Staff/Invigilator details', icon: Users, required: true },
    { key: 'students', name: 'Students', description: 'Student IDs, names, and programs', icon: Users, required: true },
    { key: 'course_registrations', name: 'Course Registrations', description: 'Student course enrollment data', icon: ClipboardList, required: true },
    { key: 'course_instructors', name: 'Course Instructors', description: 'Staff teaching assignments for courses', icon: UserCheck, required: true },
    { key: 'staff_unavailability', name: 'Staff Unavailability', description: 'Stated unavailable times for staff (Optional)', icon: CalendarX, required: false },
  ];
  
  const uploadedEntityTypes = useMemo(() => 
    Object.entries(uploadResults)
      .filter(([, result]) => result.status === 'success')
      .map(([key]) => key),
    [uploadResults]
  );

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
      const payload: SessionSetupCreate = {
        session_name: sessionData.name,
        start_date: sessionData.startDate,
        end_date: sessionData.endDate,
        slot_generation_mode: sessionData.slotGenerationMode,
        time_slots: sessionData.timeSlots.map(({ startTime, endTime, name }) => ({ start_time: startTime, end_time: endTime, name })),
      };
      try {
        const result = await createSession(payload);
        if (result.success && result.data?.academic_session_id) {
          setSessionId(result.data.academic_session_id);
          setCurrentStep(3);
        } else {
          toast.error("Failed to create session.", { description: result.message });
        }
      } catch (error) { /* Handled by hook */ }
    } else if (currentStep < 5) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => { if (currentStep > 1) setCurrentStep(currentStep - 1); };

  const handleFileSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) setSelectedFiles(Array.from(files));
  };

  const handleBatchUpload = async () => {
    if (selectedFiles.length === 0 || !sessionId) return;
    try {
      const result = await uploadFiles({ files: selectedFiles, academicSessionId: sessionId });
      const newResults: typeof uploadResults = {};

      result.dispatched_tasks.forEach((file: any) => { 
        newResults[file.entity_type] = { status: 'processing', fileName: file.file_name }; 
      });

      result.failed_files.forEach((file: any) => {
        if (file.entity_type) { 
          newResults[file.entity_type] = { status: 'failed', message: file.error, fileName: file.file_name }; 
        } else { 
          toast.error(`File upload failed: ${file.file_name}`, { description: file.error }); 
        }
      });

      setUploadResults(prev => ({ ...prev, ...newResults }));
      setSelectedFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      
      setIsPolling(true);

    } catch (error) { /* Handled by hook */ }
  };

  const handleProcessData = async () => {
    if (!sessionId) return;
    try {
      const result = await processData({ sessionId });
      if (result.success) {
        toast.success('Session setup complete!', { description: 'All data has been processed. You can now configure constraints.' });
        setCurrentPage('constraints');
      }
    } catch (error) { /* Handled by hook */ }
  };
  
  const handleManualSummaryRefresh = async () => {
      setIsSummaryRefetching(true);
      await refetchSummary();
      setIsSummaryRefetching(false);
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1: return <Card><CardHeader><CardTitle>Exam Session Information</CardTitle><CardDescription>Define the basic period and name for this exam session.</CardDescription></CardHeader><CardContent className="space-y-4 pt-6"><div className="space-y-2"><Label htmlFor="session-name">Session Name</Label><Input id="session-name" placeholder="e.g., Fall 2025 Final Exams" value={sessionData.name} onChange={(e) => setSessionData(prev => ({ ...prev, name: e.target.value }))} /></div><div className="grid grid-cols-1 md:grid-cols-2 gap-4"><div className="space-y-2"><Label htmlFor="start-date">Start Date</Label><Input id="start-date" type="date" value={sessionData.startDate} onChange={(e) => setSessionData(prev => ({ ...prev, startDate: e.target.value }))} /></div><div className="space-y-2"><Label htmlFor="end-date">End Date</Label><Input id="end-date" type="date" value={sessionData.endDate} onChange={(e) => setSessionData(prev => ({ ...prev, endDate: e.target.value }))} /></div></div>{durationInDays > 0 && (<Alert variant={durationInDays < 7 || durationInDays > 21 ? 'destructive' : 'default'}><Calendar className="h-4 w-4" /><AlertDescription>This session will span {durationInDays} days. Recommended duration is 2-3 weeks.</AlertDescription></Alert>)}</CardContent></Card>;
      case 2: return <Card><CardHeader><CardTitle>Schedule Structure</CardTitle><CardDescription>Configure the daily time slots for your exam session.</CardDescription></CardHeader><CardContent className="space-y-6 pt-6"><div className="w-full md:w-1/2"><Label>Slot Generation Mode</Label><Select value={sessionData.slotGenerationMode} onValueChange={(value) => setSessionData(prev => ({...prev, slotGenerationMode: value}))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="flexible">Flexible</SelectItem><SelectItem value="fixed">Fixed</SelectItem></SelectContent></Select></div><h4 className="font-medium">Daily Time Slots</h4><div className="space-y-3">{sessionData.timeSlots.map((slot) => (<div key={slot.id} className="flex items-center space-x-3 p-3 border rounded-lg"><div className="flex-1 grid grid-cols-3 gap-3"><div><Label className="text-xs">Slot Name</Label><Input placeholder="e.g., Morning" value={slot.name} onChange={(e) => setSessionData(prev => ({...prev, timeSlots: prev.timeSlots.map(s => s.id === slot.id ? {...s, name: e.target.value} : s)}))} /></div><div><Label className="text-xs">Start Time</Label><Input type="time" value={slot.startTime} onChange={(e) => setSessionData(prev => ({...prev, timeSlots: prev.timeSlots.map(s => s.id === slot.id ? {...s, startTime: e.target.value} : s)}))} /></div><div><Label className="text-xs">End Time</Label><Input type="time" value={slot.endTime} onChange={(e) => setSessionData(prev => ({...prev, timeSlots: prev.timeSlots.map(s => s.id === slot.id ? {...s, endTime: e.target.value} : s)}))} /></div></div></div>))}</div></CardContent></Card>;
      case 3: return (
        <Card><CardHeader><CardTitle>Batch Data Upload</CardTitle><CardDescription>Select all required CSV files. The system will automatically detect the entity type.</CardDescription></CardHeader><CardContent className="space-y-4 pt-6">
            <div className="p-6 border-2 border-dashed rounded-lg text-center"><FolderUp className="mx-auto h-12 w-12 text-gray-400" /><Label htmlFor="file-upload" className="mt-2 block font-medium text-primary cursor-pointer hover:underline">{selectedFiles.length > 0 ? `${selectedFiles.length} files selected` : 'Choose files to upload'}</Label><p className="mt-1 text-xs text-muted-foreground">Select multiple CSV files by holding Ctrl/Cmd</p><input id="file-upload" ref={fileInputRef} type="file" multiple onChange={handleFileSelection} accept=".csv" className="sr-only" /></div>
            {selectedFiles.length > 0 && (<div className="space-y-2"><h4 className="font-medium">Selected Files:</h4><ul className="list-disc list-inside text-sm text-muted-foreground">{selectedFiles.map(f => <li key={f.name}>{f.name} ({Math.round(f.size / 1024)} KB)</li>)}</ul><Button onClick={handleBatchUpload} disabled={isUploading}>{isUploading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Uploading...</> : `Upload ${selectedFiles.length} Files`}</Button></div>)}
            <div className="space-y-2 pt-4"><h4 className="font-medium">Upload Status:</h4>
              {requiredFiles.map((file) => {
                const Icon = file.icon;
                const result = uploadResults[file.key];
                const status = result?.status || 'pending';
                const style = statusStyles[status];
                return (
                  <div key={file.key} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3"><div className={cn("p-2 rounded-full", style.bg)}><Icon className={cn("h-4 w-4", style.text)} /></div>
                      <div>
                        <div className="flex items-center space-x-2"><h4 className="font-medium">{file.name}</h4>{file.required && <Badge variant="destructive">Required</Badge>}{style.icon}</div>
                        <p className="text-sm text-muted-foreground">{result?.fileName || file.description}</p>
                        {status === 'failed' && <p className="text-xs text-red-600">{result?.message}</p>}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent></Card>
      );
      case 4: return (
        <Card><CardHeader><CardTitle>Review & Edit Staged Data</CardTitle><CardDescription>Correct individual records before final processing.</CardDescription></CardHeader><CardContent>
            {sessionId ? <StagingDataReviewTable sessionId={sessionId} uploadedEntityTypes={uploadedEntityTypes} /> : <Alert variant="destructive">Session ID is missing. Cannot load data.</Alert>}
        </CardContent></Card>
      );
      case 5: return (
        <div className="space-y-6">{isLoadingSummary ? (<div className="flex justify-center items-center py-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>) : !summaryData ? (<Card><CardContent className="py-8 text-center"><p className="text-muted-foreground">Could not load session summary.</p><Button onClick={handleManualSummaryRefresh} variant="outline" className="mt-4"><RefreshCw className={`h-4 w-4 mr-2 ${isSummaryRefetching ? 'animate-spin' : ''}`} />Try Again</Button></CardContent></Card>) : (
          <><Card><CardHeader><div className="flex justify-between items-center"><div><CardTitle>Final Summary</CardTitle><CardDescription>Review your configuration before final processing.</CardDescription></div><Button onClick={handleManualSummaryRefresh} variant="outline" size="sm" disabled={isSummaryRefetching}><RefreshCw className={`h-4 w-4 mr-2 ${isSummaryRefetching ? 'animate-spin' : ''}`} />Refresh</Button></div></CardHeader><CardContent className="space-y-4 pt-6"><div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><h4 className="font-medium mb-2">Session Details</h4><div className="space-y-1 text-sm"><div><span className="text-muted-foreground">Name:</span> {summaryData.session_details.name}</div><div><span className="text-muted-foreground">Period:</span> {new Date(summaryData.session_details.start_date).toLocaleDateString()} to {new Date(summaryData.session_details.end_date).toLocaleDateString()}</div><div><span className="text-muted-foreground">Daily Slots:</span> {summaryData.session_details.time_slots?.length || 0}</div></div></div>
            <div><h4 className="font-medium mb-2">Data Summary</h4><div className="space-y-1 text-sm">{Object.entries(summaryData.data_summary).map(([key, value]) => (<div key={key}><span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}:</span> {value as any}</div>))}</div></div>
          </div></CardContent></Card>
          <Card><CardHeader><CardTitle className="flex items-center">{summaryData.validation_results.errors.length === 0 ? <CheckCircle className="h-5 w-5 mr-2 text-green-500" /> : <AlertTriangle className="h-5 w-5 mr-2 text-red-500" />}Validation Results</CardTitle></CardHeader><CardContent className="space-y-4">
              {summaryData.validation_results.errors.length > 0 && (<Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertDescription><div className="font-medium mb-2">Errors found:</div><ul className="list-disc list-inside space-y-1">{summaryData.validation_results.errors.map((error, index) => (<li key={index}>{error}</li>))}</ul></AlertDescription></Alert>)}
              {summaryData.validation_results.warnings.length > 0 && (<Alert><AlertTriangle className="h-4 w-4" /><AlertDescription><div className="font-medium mb-2">Warnings:</div><ul className="list-disc list-inside space-y-1">{summaryData.validation_results.warnings.map((warning, index) => (<li key={index}>{warning}</li>))}</ul></AlertDescription></Alert>)}
              {summaryData.validation_results.errors.length === 0 && (<Alert><CheckCircle className="h-4 w-4" /><AlertDescription>All validation checks passed. Your session is ready for final processing.</AlertDescription></Alert>)}
          </CardContent></Card></>
        )}</div>
      );
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between"><div><h1 className="text-2xl font-semibold">Exam Session Setup Wizard</h1><p className="text-muted-foreground">A step-by-step guide to configure a new academic exam session.</p></div><div className="flex items-center space-x-2"><span className="text-sm text-muted-foreground">Step {currentStep} of {steps.length}</span><Progress value={(currentStep / steps.length) * 100} className="w-24" /></div></div>
      <Card><CardContent className="p-6">
        <div className="flex items-center justify-between">{steps.map((step, index) => {
          const Icon = step.icon; const isActive = currentStep === step.id; const isCompleted = currentStep > step.id;
          return (<React.Fragment key={step.id}><div className="flex flex-col items-center space-y-2 text-center"><div className={cn("w-10 h-10 rounded-full flex items-center justify-center border-2", isActive && "border-primary text-primary", isCompleted && "bg-primary border-primary text-primary-foreground", !isActive && !isCompleted && "border-muted-foreground text-muted-foreground")}><Icon className="h-5 w-5" /></div><div className={cn("text-sm font-medium", isActive && "text-primary")}>{step.name}</div></div>{index < steps.length - 1 && <div className={cn("flex-1 h-0.5 mx-4", isCompleted ? "bg-primary" : "bg-muted")} />}</React.Fragment>);
        })}</div>
      </CardContent></Card>
      
      <div className="min-h-[30rem]">{renderStepContent()}</div>

      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={prevStep} disabled={currentStep === 1 || isCreatingSession || isUploading || isProcessing}><ChevronLeft className="h-4 w-4 mr-2" />Previous</Button>
        <div className="flex space-x-3">
          {currentStep < 5 && (<Button onClick={handleNextStep} disabled={!isStepValid(currentStep) || isCreatingSession}>{isCreatingSession ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Creating...</> : <>Next<ChevronRight className="h-4 w-4 ml-2" /></>}</Button>)}
          {currentStep === 5 && (
            <Button 
              onClick={handleProcessData} 
              disabled={!isStepValid(5) || isLoadingSummary || isProcessing}
            >
              {isProcessing ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Processing Data...</> : <>Process & Finish<ChevronRight className="h-4 w-4 ml-2" /></>}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}