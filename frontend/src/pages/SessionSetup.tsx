// frontend/src/pages/SessionSetup.tsx
import React, { useState, useMemo, useRef, useEffect } from 'react';
import { 
  Zap, 
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
  Plus,
  Trash2,
  Loader2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Badge } from '../components/ui/badge'
import { Progress } from '../components/ui/progress'
import { Alert, AlertDescription } from '../components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { cn } from '../components/ui/utils'
import { toast } from 'sonner'
import { useCreateSession, useFileUpload, useSessionSummary } from '../hooks/useApi';
import { useAppStore } from '../store';

// --- Type Definitions ---
interface TimeSlot {
  start_time: string;
  end_time: string;
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

// Component
export function SessionSetup() {
  const { setCurrentPage } = useAppStore();
  const [currentStep, setCurrentStep] = useState(1);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // API Hooks
  const { mutateAsync: createSession, isPending: isCreatingSession } = useCreateSession();
  const { mutateAsync: uploadFile, isPending: isUploading } = useFileUpload();
  const { data: summaryData, isLoading: isLoadingSummary, refetch: refetchSummary } = useSessionSummary(sessionId);

  // File Upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [currentUploadKey, setCurrentUploadKey] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<Record<string, { name: string; size: number } | null>>({
    courses: null, students: null, enrollments: null, rooms: null, invigilators: null,
  });

  // Form State
  const [sessionData, setSessionData] = useState({
    name: 'Fall 2025 Final Exams',
    startDate: '2025-12-01',
    endDate: '2025-12-15',
    slotGenerationMode: 'flexible',
    timeSlots: [
      { id: '1', startTime: '09:00', endTime: '12:00' },
      { id: '2', startTime: '14:00', endTime: '17:00' },
    ]
  });
  
  const durationInDays = useMemo(() => {
    if (!sessionData.startDate || !sessionData.endDate) return 0;
    const start = new Date(sessionData.startDate);
    const end = new Date(sessionData.endDate);
    const diff = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    return diff > 0 ? diff : 0;
  }, [sessionData.startDate, sessionData.endDate]);
  
  // Refetch summary when entering the final step
  useEffect(() => {
    if (currentStep === 4 && sessionId) {
      refetchSummary();
    }
  }, [currentStep, sessionId, refetchSummary]);
  
  const steps = [
    { id: 1, name: 'Define Session', icon: Calendar },
    { id: 2, name: 'Schedule Structure', icon: Clock },
    { id: 3, name: 'Upload Data', icon: Upload },
    { id: 4, name: 'Review & Confirm', icon: CheckCircle },
  ];

  const requiredFiles = [
    { key: 'courses', name: 'Courses', description: 'Course codes, names, departments', icon: FileText, required: true },
    { key: 'students', name: 'Students', description: 'Student IDs, names, and programs', icon: Users, required: true },
    { key: 'student_enrollments', name: 'Student Enrollments', description: 'Student course registrations', icon: FileText, required: true },
    { key: 'rooms', name: 'Rooms', description: 'Room capacities and locations', icon: MapPin, required: true },
    { key: 'staff', name: 'Invigilators', description: 'Staff availability (Optional)', icon: Users, required: false },
  ];

  const isStepValid = (step: number) => {
    switch (step) {
      case 1: return sessionData.name && sessionData.startDate && sessionData.endDate && durationInDays > 0;
      case 2: return sessionData.timeSlots.every(ts => ts.startTime && ts.endTime);
      case 3: return requiredFiles.filter(f => f.required).every(f => uploadedFiles[f.key]);
      case 4: return !!summaryData && summaryData.validation_results.errors.length === 0;
      default: return false;
    }
  };

  const handleNextStep = async () => {
    if (!isStepValid(currentStep)) return;

    if (currentStep === 2) { // After Schedule Structure, create the session
      const payload: SessionSetupCreate = {
        session_name: sessionData.name,
        start_date: sessionData.startDate,
        end_date: sessionData.endDate,
        slot_generation_mode: sessionData.slotGenerationMode,
        time_slots: sessionData.timeSlots.map(({ startTime, endTime }) => ({ start_time: startTime, end_time: endTime })),
      };
      try {
        const result = await createSession(payload);
        if (result.success && result.data.session_id) {
          setSessionId(result.data.session_id);
          setCurrentStep(3);
        }
      } catch (error) { /* Error toast is handled by the hook */ }
    } else if (currentStep < 4) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => { if (currentStep > 1) setCurrentStep(currentStep - 1); };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !currentUploadKey || !sessionId) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      await uploadFile({ formData, entityType: currentUploadKey, academicSessionId: sessionId });
      setUploadedFiles(prev => ({ ...prev, [currentUploadKey]: { name: file.name, size: file.size } }));
    } catch (error) { /* Error handled by hook */ }

    // Reset file input for next upload
    if (fileInputRef.current) fileInputRef.current.value = "";
    setCurrentUploadKey('');
  };

  const triggerFileUpload = (fileKey: string) => {
    setCurrentUploadKey(fileKey);
    fileInputRef.current?.click();
  };

  const addTimeSlot = () => setSessionData(prev => ({ ...prev, timeSlots: [...prev.timeSlots, { id: Date.now().toString(), startTime: '', endTime: '' }] }));
  const removeTimeSlot = (id: string) => setSessionData(prev => ({ ...prev, timeSlots: prev.timeSlots.filter(slot => slot.id !== id) }));
  const updateTimeSlot = (id: string, updates: Partial<{startTime: string, endTime: string}>) => setSessionData(prev => ({ ...prev, timeSlots: prev.timeSlots.map(slot => slot.id === id ? { ...slot, ...updates } : slot) }));
  
  const finishSetup = () => {
    toast.success('Session setup complete! You can now proceed to scheduling.');
    setCurrentPage('scheduling');
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1: return (
        <Card><CardHeader><CardTitle>Exam Session Information</CardTitle><CardDescription>Define the basic period and name for this exam session.</CardDescription></CardHeader><CardContent className="space-y-4 pt-6">
            <div className="space-y-2"><Label htmlFor="session-name">Session Name</Label><Input id="session-name" placeholder="e.g., Fall 2025 Final Exams" value={sessionData.name} onChange={(e) => setSessionData(prev => ({ ...prev, name: e.target.value }))} /></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4"><div className="space-y-2"><Label htmlFor="start-date">Start Date</Label><Input id="start-date" type="date" value={sessionData.startDate} onChange={(e) => setSessionData(prev => ({ ...prev, startDate: e.target.value }))} /></div><div className="space-y-2"><Label htmlFor="end-date">End Date</Label><Input id="end-date" type="date" value={sessionData.endDate} onChange={(e) => setSessionData(prev => ({ ...prev, endDate: e.target.value }))} /></div></div>
            {durationInDays > 0 && (<Alert variant={durationInDays < 7 || durationInDays > 21 ? 'destructive' : 'default'}><Calendar className="h-4 w-4" /><AlertDescription>This session will span {durationInDays} days. Recommended duration is 2-3 weeks.</AlertDescription></Alert>)}
        </CardContent></Card>
      );
      case 2: return (
        <Card><CardHeader><CardTitle>Schedule Structure</CardTitle><CardDescription>Configure the daily time slots and generation mode for your exam session.</CardDescription></CardHeader><CardContent className="space-y-6 pt-6">
            <div className="w-full md:w-1/2"><Label>Slot Generation Mode</Label><Select value={sessionData.slotGenerationMode} onValueChange={(value) => setSessionData(prev => ({...prev, slotGenerationMode: value}))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="flexible">Flexible</SelectItem><SelectItem value="fixed">Fixed</SelectItem></SelectContent></Select></div>
            <div className="flex items-center justify-between"><h4 className="font-medium">Daily Time Slots</h4><Button onClick={addTimeSlot} size="sm"><Plus className="h-4 w-4 mr-1" />Add Slot</Button></div>
            <div className="space-y-3">{sessionData.timeSlots.map((slot) => (<div key={slot.id} className="flex items-center space-x-3 p-3 border rounded-lg"><div className="flex-1 grid grid-cols-2 gap-3"><div><Label className="text-xs">Start Time</Label><Input type="time" value={slot.startTime} onChange={(e) => updateTimeSlot(slot.id, { startTime: e.target.value })} /></div><div><Label className="text-xs">End Time</Label><Input type="time" value={slot.endTime} onChange={(e) => updateTimeSlot(slot.id, { endTime: e.target.value })} /></div></div>{sessionData.timeSlots.length > 1 && (<Button variant="ghost" size="icon" onClick={() => removeTimeSlot(slot.id)}><Trash2 className="h-4 w-4" /></Button>)}</div>))}</div>
        </CardContent></Card>
      );
      case 3: return (
        <Card><CardHeader><CardTitle>Data Upload</CardTitle><CardDescription>Upload the required CSV files for your exam session.</CardDescription></CardHeader><CardContent className="space-y-4 pt-6">
            <input type="file" ref={fileInputRef} onChange={handleFileSelect} accept=".csv" className="hidden" />
            {requiredFiles.map((file) => {
              const Icon = file.icon; const isUploaded = !!uploadedFiles[file.key];
              return (<div key={file.key} className="flex items-center justify-between p-4 border rounded-lg"><div className="flex items-center space-x-3"><div className={cn("p-2 rounded-full", isUploaded ? "bg-green-100 dark:bg-green-900/50" : "bg-gray-100 dark:bg-gray-900/50")}><Icon className={cn("h-4 w-4", isUploaded ? "text-green-600 dark:text-green-300" : "text-gray-600 dark:text-gray-300")} /></div><div><div className="flex items-center space-x-2"><h4 className="font-medium">{file.name}</h4>{file.required && <Badge variant="destructive">Required</Badge>}{isUploaded && <CheckCircle className="h-4 w-4 text-green-500" />}</div><p className="text-sm text-muted-foreground">{file.description}</p></div></div><Button variant={isUploaded ? "outline" : "default"} onClick={() => triggerFileUpload(file.key)} disabled={isUploading || isUploaded}>{isUploaded ? 'Uploaded' : isUploading && currentUploadKey === file.key ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Upload'}</Button></div>);
            })}
        </CardContent></Card>
      );
      case 4: return (
        <div className="space-y-6">{isLoadingSummary ? (<div className="flex justify-center items-center py-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>) : !summaryData ? (<Card><CardContent className="py-8 text-center text-muted-foreground">Could not load session summary. Please try again.</CardContent></Card>) : (
          <><Card><CardHeader><CardTitle>Session Summary</CardTitle><CardDescription>Review your exam session configuration before creation.</CardDescription></CardHeader><CardContent className="space-y-4 pt-6"><div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><h4 className="font-medium mb-2">Session Details</h4><div className="space-y-1 text-sm"><div><span className="text-muted-foreground">Name:</span> {summaryData.session_details.name}</div><div><span className="text-muted-foreground">Period:</span> {new Date(summaryData.session_details.start_date).toLocaleDateString()} to {new Date(summaryData.session_details.end_date).toLocaleDateString()}</div><div><span className="text-muted-foreground">Daily Slots:</span> {summaryData.session_details.time_slots?.length || 0}</div></div></div>
            <div><h4 className="font-medium mb-2">Data Summary</h4><div className="space-y-1 text-sm"><div><span className="text-muted-foreground">Courses:</span> {summaryData.data_summary.courses}</div><div><span className="text-muted-foreground">Students:</span> {summaryData.data_summary.students}</div><div><span className="text-muted-foreground">Rooms:</span> {summaryData.data_summary.rooms}</div><div><span className="text-muted-foreground">Enrollments:</span> {summaryData.data_summary.enrollments}</div></div></div>
          </div></CardContent></Card>
          <Card><CardHeader><CardTitle className="flex items-center">{summaryData.validation_results.errors.length === 0 ? <CheckCircle className="h-5 w-5 mr-2 text-green-500" /> : <AlertTriangle className="h-5 w-5 mr-2 text-red-500" />}Validation Results</CardTitle></CardHeader><CardContent className="space-y-4">
              {summaryData.validation_results.errors.length > 0 && (<Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertDescription><div className="font-medium mb-2">Errors found:</div><ul className="list-disc list-inside space-y-1">{summaryData.validation_results.errors.map((error, index) => (<li key={index}>{error}</li>))}</ul></AlertDescription></Alert>)}
              {summaryData.validation_results.warnings.length > 0 && (<Alert><AlertTriangle className="h-4 w-4" /><AlertDescription><div className="font-medium mb-2">Warnings:</div><ul className="list-disc list-inside space-y-1">{summaryData.validation_results.warnings.map((warning, index) => (<li key={index}>{warning}</li>))}</ul></AlertDescription></Alert>)}
              {summaryData.validation_results.errors.length === 0 && (<Alert><CheckCircle className="h-4 w-4" /><AlertDescription>All validation checks passed. Your session is ready.</AlertDescription></Alert>)}
          </CardContent></Card></>
        )}</div>
      );
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between"><div><h1 className="text-2xl font-semibold">Exam Session Setup Wizard</h1><p className="text-muted-foreground">Configure a new academic exam session</p></div><div className="flex items-center space-x-2"><span className="text-sm text-muted-foreground">Step {currentStep} of {steps.length}</span><Progress value={(currentStep / steps.length) * 100} className="w-24" /></div></div>
      <Card><CardContent className="p-6">
        <div className="flex items-center justify-between">{steps.map((step, index) => {
          const Icon = step.icon; const isActive = currentStep === step.id; const isCompleted = sessionId ? step.id < 3 : currentStep > step.id;
          return (<React.Fragment key={step.id}><div className="flex flex-col items-center space-y-2 text-center"><div className={cn("w-10 h-10 rounded-full flex items-center justify-center border-2", isActive && "border-primary text-primary", isCompleted && "bg-primary border-primary text-primary-foreground", !isActive && !isCompleted && "border-muted-foreground text-muted-foreground")}><Icon className="h-5 w-5" /></div><div><div className={cn("text-sm font-medium", isActive && "text-primary")}>{step.name}</div></div></div>{index < steps.length - 1 && <div className={cn("flex-1 h-0.5 mx-4", isCompleted ? "bg-primary" : "bg-muted")} />}</React.Fragment>);
        })}</div>
      </CardContent></Card>
      
      <div className="min-h-[30rem]">{renderStepContent()}</div>

      <div className="flex items-center justify-between"><Button variant="outline" onClick={prevStep} disabled={currentStep === 1 || isCreatingSession}><ChevronLeft className="h-4 w-4 mr-2" />Previous</Button><div className="flex space-x-3">{currentStep < 4 && (<Button onClick={handleNextStep} disabled={!isStepValid(currentStep) || isCreatingSession}>{isCreatingSession ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Creating...</> : <>Next<ChevronRight className="h-4 w-4 ml-2" /></>}</Button>)}{currentStep === 4 && (<Button onClick={finishSetup} disabled={!isStepValid(4)}><Zap className="h-4 w-4 mr-2" />Finish Setup</Button>)}</div></div>
    </div>
  );
}