// frontend/src/pages/SessionSetup.tsx
import React, { useState, useMemo } from 'react';
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
  Settings,
  Plus,
  Trash2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Badge } from '../components/ui/badge'
import { Progress } from '../components/ui/progress'
import { Alert, AlertDescription } from '../components/ui/alert'
import { Separator } from '../components/ui/separator'
import { cn } from '../components/ui/utils'
import { toast } from 'sonner'

interface TimeSlot {
  id: string;
  startTime: string;
  endTime: string;
  duration: number;
}

interface ValidationResult {
  isValid: boolean;
  warnings: string[];
  errors: string[];
  summary: {
    courses: number;
    students: number;
    rooms: number;
    enrollments: number;
  };
}

export function SessionSetup() {
  const [currentStep, setCurrentStep] = useState(1);
  const [sessionData, setSessionData] = useState({
    name: 'Fall 2025 Final Exams',
    startDate: '2025-12-01',
    endDate: '2025-12-15',
    timeSlots: [
      { id: '1', startTime: '09:00', endTime: '12:00', duration: 180 },
      { id: '2', startTime: '14:00', endTime: '17:00', duration: 180 },
    ] as TimeSlot[]
  });

  const durationInDays = useMemo(() => {
    if (!sessionData.startDate || !sessionData.endDate) return 0;
    const start = new Date(sessionData.startDate);
    const end = new Date(sessionData.endDate);
    return Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
  }, [sessionData.startDate, sessionData.endDate]);


  const [uploadedFiles, setUploadedFiles] = useState<Record<string, boolean>>({
    courses: false,
    students: false,
    enrollments: false,
    rooms: false,
    invigilators: false
  });

  const [validationResult, setValidationResult] = useState<ValidationResult>({
    isValid: true,
    warnings: ['Room B102 has limited capacity for large exams'],
    errors: [],
    summary: { courses: 156, students: 2847, rooms: 24, enrollments: 4932 }
  });

  const steps = [
    { id: 1, name: 'Define Session', description: 'Basic session information', icon: Calendar },
    { id: 2, name: 'Upload Data', description: 'Import CSV files', icon: Upload },
    { id: 3, name: 'Schedule Structure', description: 'Configure time slots', icon: Clock },
    { id: 4, name: 'Review & Confirm', description: 'Final validation', icon: CheckCircle },
  ];

  const requiredFiles = [
    { key: 'courses', name: 'Courses.csv', description: 'Course codes, names, departments', icon: FileText, required: true },
    { key: 'students', name: 'Students.csv', description: 'Student IDs, names, and programs', icon: Users, required: true },
    { key: 'enrollments', name: 'Student_Enrollments.csv', description: 'Student course registrations', icon: FileText, required: true },
    { key: 'rooms', name: 'Rooms.csv', description: 'Room capacities and locations', icon: MapPin, required: true },
    { key: 'invigilators', name: 'Invigilators.csv', description: 'Staff availability and preferences', icon: Users, required: false },
  ];

  const isStepValid = (step: number) => {
    switch (step) {
      case 1: return sessionData.name && sessionData.startDate && sessionData.endDate && durationInDays > 0;
      case 2: return requiredFiles.filter(f => f.required).every(f => uploadedFiles[f.key]);
      case 3: return sessionData.timeSlots.length > 0;
      case 4: return validationResult.isValid && validationResult.errors.length === 0;
      default: return false;
    }
  };

  const nextStep = () => { if (currentStep < 4 && isStepValid(currentStep)) setCurrentStep(currentStep + 1); };
  const prevStep = () => { if (currentStep > 1) setCurrentStep(currentStep - 1); };

  const handleFileUpload = (fileKey: string) => {
    setUploadedFiles(prev => ({ ...prev, [fileKey]: true }));
    toast.success(`${requiredFiles.find(f => f.key === fileKey)?.name} uploaded successfully`);
  };

  const addTimeSlot = () => {
    const newSlot: TimeSlot = { id: Date.now().toString(), startTime: '18:00', endTime: '21:00', duration: 180 };
    setSessionData(prev => ({ ...prev, timeSlots: [...prev.timeSlots, newSlot] }));
  };

  const removeTimeSlot = (id: string) => setSessionData(prev => ({ ...prev, timeSlots: prev.timeSlots.filter(slot => slot.id !== id) }));

  const calculateDuration = (startTime: string, endTime: string): number => {
    if (!startTime || !endTime) return 0;
    const start = new Date(`2000-01-01T${startTime}:00`);
    const end = new Date(`2000-01-01T${endTime}:00`);
    if (end < start) end.setDate(end.getDate() + 1);
    return Math.round((end.getTime() - start.getTime()) / (1000 * 60));
  };

  const updateTimeSlot = (id: string, updates: Partial<TimeSlot>) => {
    setSessionData(prev => ({
      ...prev,
      timeSlots: prev.timeSlots.map(slot => {
        if (slot.id === id) {
          const updatedSlot = { ...slot, ...updates };
          if (updates.startTime || updates.endTime) {
            updatedSlot.duration = calculateDuration(updatedSlot.startTime, updatedSlot.endTime);
          }
          return updatedSlot;
        }
        return slot;
      })
    }));
  };

  const createSession = () => toast.success('Exam session created successfully!');

  const renderStepContent = () => {
    switch (currentStep) {
      case 1: return (
        <Card>
          <CardHeader><CardTitle>Exam Session Information</CardTitle><CardDescription>Define the basic period and name for this exam session.</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2"><Label htmlFor="session-name">Session Name</Label><Input id="session-name" placeholder="e.g., Fall 2025 Final Exams" value={sessionData.name} onChange={(e) => setSessionData(prev => ({ ...prev, name: e.target.value }))} /></div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2"><Label htmlFor="start-date">Start Date</Label><Input id="start-date" type="date" value={sessionData.startDate} onChange={(e) => setSessionData(prev => ({ ...prev, startDate: e.target.value }))} /></div>
              <div className="space-y-2"><Label htmlFor="end-date">End Date</Label><Input id="end-date" type="date" value={sessionData.endDate} onChange={(e) => setSessionData(prev => ({ ...prev, endDate: e.target.value }))} /></div>
            </div>
            {durationInDays > 0 && (
              <Alert variant={durationInDays < 7 || durationInDays > 21 ? 'destructive' : 'default'}>
                <Calendar className="h-4 w-4" />
                <AlertDescription>
                  This session will span {durationInDays} days. Recommended duration is 2-3 weeks (14-21 days).
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      );
      case 2: return (
        <Card>
          <CardHeader><CardTitle>Data Upload</CardTitle><CardDescription>Upload the required CSV files for your exam session.</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            {requiredFiles.map((file) => {
              const Icon = file.icon;
              const isUploaded = uploadedFiles[file.key];
              return (
                <div key={file.key} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className={cn("p-2 rounded-full", isUploaded ? "bg-green-100 dark:bg-green-900/50" : "bg-gray-100 dark:bg-gray-900/50")}><Icon className={cn("h-4 w-4", isUploaded ? "text-green-600 dark:text-green-300" : "text-gray-600 dark:text-gray-300")} /></div>
                    <div>
                      <div className="flex items-center space-x-2"><h4 className="font-medium">{file.name}</h4>{file.required && <Badge variant="destructive">Required</Badge>}{!file.required && <Badge variant="secondary">Optional</Badge>}{isUploaded && <CheckCircle className="h-4 w-4 text-green-500" />}</div>
                      <p className="text-sm text-muted-foreground">{file.description}</p>
                    </div>
                  </div>
                  <Button variant={isUploaded ? "outline" : "default"} onClick={() => handleFileUpload(file.key)} disabled={isUploaded}>{isUploaded ? 'Uploaded' : 'Upload'}</Button>
                </div>
              );
            })}
          </CardContent>
        </Card>
      );
      case 3: return (
        <Card>
          <CardHeader><CardTitle>Schedule Structure</CardTitle><CardDescription>Configure the daily time slots for your exam session.</CardDescription></CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between"><h4 className="font-medium">Daily Time Slots</h4><Button onClick={addTimeSlot} size="sm"><Plus className="h-4 w-4 mr-1" />Add Slot</Button></div>
            <div className="space-y-3">
              {sessionData.timeSlots.map((slot) => (
                <div key={slot.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <div className="flex-1 grid grid-cols-3 gap-3">
                    <div><Label className="text-xs">Start Time</Label><Input type="time" value={slot.startTime} onChange={(e) => updateTimeSlot(slot.id, { startTime: e.target.value })} /></div>
                    <div><Label className="text-xs">End Time</Label><Input type="time" value={slot.endTime} onChange={(e) => updateTimeSlot(slot.id, { endTime: e.target.value })} /></div>
                    <div><Label className="text-xs">Duration (min)</Label><Input type="number" value={slot.duration} onChange={(e) => updateTimeSlot(slot.id, { duration: parseInt(e.target.value) || 0 })} /></div>
                  </div>
                  {sessionData.timeSlots.length > 1 && (<Button variant="ghost" size="sm" onClick={() => removeTimeSlot(slot.id)}><Trash2 className="h-4 w-4" /></Button>)}
                </div>
              ))}
            </div>
            <Alert><Settings className="h-4 w-4" /><AlertDescription>Time slots will be applied to each exam day within the session period.</AlertDescription></Alert>
          </CardContent>
        </Card>
      );
      case 4: return (
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Session Summary</CardTitle><CardDescription>Review your exam session configuration before creation.</CardDescription></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2">Session Details</h4>
                  <div className="space-y-1 text-sm">
                    <div><span className="text-muted-foreground">Name:</span> {sessionData.name}</div>
                    <div><span className="text-muted-foreground">Period:</span> {sessionData.startDate} to {sessionData.endDate} ({durationInDays} days)</div>
                    <div><span className="text-muted-foreground">Daily Slots:</span> {sessionData.timeSlots.length}</div>
                  </div>
                </div>
                <div><h4 className="font-medium mb-2">Data Summary</h4><div className="space-y-1 text-sm"><div><span className="text-muted-foreground">Courses:</span> {validationResult.summary.courses}</div><div><span className="text-muted-foreground">Students:</span> {validationResult.summary.students.toLocaleString()}</div><div><span className="text-muted-foreground">Rooms:</span> {validationResult.summary.rooms}</div><div><span className="text-muted-foreground">Enrollments:</span> {validationResult.summary.enrollments.toLocaleString()}</div></div></div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="flex items-center">{validationResult.isValid && validationResult.errors.length === 0 ? <CheckCircle className="h-5 w-5 mr-2 text-green-500" /> : <AlertTriangle className="h-5 w-5 mr-2 text-red-500" />}Validation Results</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {validationResult.errors.length > 0 && (<Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertDescription><div className="font-medium mb-2">Errors found:</div><ul className="list-disc list-inside space-y-1">{validationResult.errors.map((error, index) => (<li key={index}>{error}</li>))}</ul></AlertDescription></Alert>)}
              {validationResult.warnings.length > 0 && (<Alert><AlertTriangle className="h-4 w-4" /><AlertDescription><div className="font-medium mb-2">Warnings:</div><ul className="list-disc list-inside space-y-1">{validationResult.warnings.map((warning, index) => (<li key={index}>{warning}</li>))}</ul></AlertDescription></Alert>)}
              {validationResult.isValid && validationResult.errors.length === 0 && (<Alert><CheckCircle className="h-4 w-4" /><AlertDescription>All validation checks passed. Your session is ready to be created.</AlertDescription></Alert>)}
            </CardContent>
          </Card>
        </div>
      );
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between"><div><h1 className="text-2xl font-semibold">Exam Session Setup Wizard</h1><p className="text-muted-foreground">Configure a new academic exam session</p></div><div className="flex items-center space-x-2"><span className="text-sm text-muted-foreground">Step {currentStep} of {steps.length}</span><Progress value={(currentStep / steps.length) * 100} className="w-24" /></div></div>
      <Card><CardContent className="p-6">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => {
              const Icon = step.icon; const isActive = currentStep === step.id; const isCompleted = currentStep > step.id; const isValid = isStepValid(step.id);
              return (<div key={step.id} className="flex items-center"><div className="flex flex-col items-center space-y-2"><div className={cn("w-10 h-10 rounded-full flex items-center justify-center border-2", isActive && isValid && "bg-primary border-primary text-primary-foreground", isActive && !isValid && "border-primary text-primary", isCompleted && "bg-green-500 border-green-500 text-white", !isActive && !isCompleted && "border-muted-foreground text-muted-foreground")}>{isCompleted ? <CheckCircle className="h-5 w-5" /> : <Icon className="h-5 w-5" />}</div><div className="text-center"><div className={cn("text-sm font-medium", isActive && "text-primary", isCompleted && "text-green-600", !isActive && !isCompleted && "text-muted-foreground")}>{step.name}</div><div className="text-xs text-muted-foreground max-w-24">{step.description}</div></div></div>{index < steps.length - 1 && (<div className={cn("flex-1 h-0.5 mx-4", isCompleted ? "bg-green-500" : "bg-muted")} />)}</div>);
            })}
          </div>
      </CardContent></Card>
      <div className="min-h-96">{renderStepContent()}</div>
      <div className="flex items-center justify-between"><Button variant="outline" onClick={prevStep} disabled={currentStep === 1}><ChevronLeft className="h-4 w-4 mr-2" />Previous</Button><div className="flex space-x-3">{currentStep < 4 && (<Button onClick={nextStep} disabled={!isStepValid(currentStep)}>Next<ChevronRight className="h-4 w-4 ml-2" /></Button>)}{currentStep === 4 && (<Button onClick={createSession} disabled={!isStepValid(4)}><Zap className="h-4 w-4 mr-2" />Create Session</Button>)}</div></div>
    </div>
  );
}