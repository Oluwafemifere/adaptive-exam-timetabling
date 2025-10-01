// frontend/src/pages/Scheduling.tsx

import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Square, 
  Settings, 
  Activity, 
  Clock,
  CheckCircle,
  AlertTriangle,
  BarChart3,
  Loader2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Slider } from '../components/ui/slider';
import { Badge } from '../components/ui/badge';
import { Label } from '../components/ui/label';
import { Separator } from '../components/ui/separator';
import { useAppStore } from '../store';
// FIX: Import the new hook for fetching sessions
import { useScheduling, useJobSocket, useAcademicSessions } from '../hooks/useApi';
import { Input } from '../components/ui/input';
import { cn } from '../components/ui/utils';
import { toast } from 'sonner';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

// ... (ConstraintSlider and PhaseIndicator components remain the same)
interface ConstraintSliderProps {
  label: string
  description: string
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
  step?: number
}

function ConstraintSlider({ label, description, value, onChange, min = 0, max = 1, step = 0.1 }: ConstraintSliderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <Label className="font-medium">{label}</Label>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
        <Badge variant="outline" className="min-w-16 justify-center">
          {value.toFixed(1)}
        </Badge>
      </div>
      <Slider
        value={[value]}
        onValueChange={([newValue]) => onChange(newValue)}
        min={min}
        max={max}
        step={step}
        className="w-full"
      />
    </div>
  )
}

interface PhaseIndicatorProps {
  phase: string
  isActive: boolean
  isCompleted: boolean
  duration?: string
}

function PhaseIndicator({ phase, isActive, isCompleted, duration }: PhaseIndicatorProps) {
  return (
    <div className={cn(
      "flex items-center space-x-3 p-4 rounded-lg border",
      isActive && "bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800",
      isCompleted && "bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800",
      !isActive && !isCompleted && "bg-gray-50 border-gray-200 dark:bg-gray-800/20 dark:border-gray-700"
    )}>
      <div className={cn(
        "w-3 h-3 rounded-full",
        isActive && "bg-blue-500 animate-pulse",
        isCompleted && "bg-green-500",
        !isActive && !isCompleted && "bg-gray-400"
      )} />
      <div className="flex-1">
        <p className={cn(
          "font-medium",
          isActive && "text-blue-900 dark:text-blue-200",
          isCompleted && "text-green-900 dark:text-green-200",
          !isActive && !isCompleted && "text-gray-600 dark:text-gray-300"
        )}>
          {phase}
        </p>
        {duration && (
          <p className="text-sm text-gray-500 dark:text-gray-400">{duration}</p>
        )}
      </div>
      {isActive && <Activity className="h-4 w-4 text-blue-500 animate-pulse" />}
      {isCompleted && <CheckCircle className="h-4 w-4 text-green-500" />}
    </div>
  )
}


export function Scheduling() {
  const { schedulingStatus, settings, updateSettings, setCurrentPage } = useAppStore();
  const { startScheduling, cancelScheduling } = useScheduling();
  
  // FIX: Fetch academic sessions dynamically instead of using a hardcoded value
  const { data: availableSessions, isLoading: isLoadingSessions } = useAcademicSessions();
  const [selectedSession, setSelectedSession] = useState<string | undefined>(undefined);
  const [scheduleStartDate, setScheduleStartDate] = useState<string>('');
  const [scheduleEndDate, setScheduleEndDate] = useState<string>('');

  useJobSocket(schedulingStatus.jobId || null);

  const handleConstraintWeightChange = (constraint: string, value: number) => {
    updateSettings({
      constraintWeights: {
        ...settings.constraintWeights,
        [constraint]: value,
      },
    });
  };

  useEffect(() => {
    if (selectedSession && availableSessions) {
      const session = availableSessions.find(s => s.id === selectedSession);
      if (session) {
        setScheduleStartDate(session.start_date.split('T')[0]);
        setScheduleEndDate(session.end_date.split('T')[0]);
      }
    }
  }, [selectedSession, availableSessions]);

  const handleStartScheduling = () => {
    if (!selectedSession) {
      toast.error("Please select an academic session to schedule.");
      return;
    }
    if (!scheduleStartDate || !scheduleEndDate) {
      toast.error("Please provide both a start and end date for scheduling.");
      return;
    }
    startScheduling.mutate({
      session_id: selectedSession,
      start_date: scheduleStartDate,
      end_date: scheduleEndDate,
      options: {
        timeLimit: 300,
        populationSize: 50,
        constraints: settings.constraintWeights,
      },
    });
  };
  
  const handleCancelScheduling = () => {
    if (schedulingStatus.jobId) {
      cancelScheduling.mutate(schedulingStatus.jobId);
    } else {
      toast.error("No active job to cancel.");
    }
  };

  const phases = [
  { phase: 'Initial Placement (CP-SAT)', isActive: schedulingStatus.phase === 'cp-sat', isCompleted: ['genetic-algorithm', 'completed'].includes(schedulingStatus.phase) },
  { phase: 'Optimization (GA)', isActive: schedulingStatus.phase === 'genetic-algorithm', isCompleted: schedulingStatus.phase === 'completed' }
];

  
  const metrics = schedulingStatus.metrics || {};
  const isJobFinished = ['completed', 'failed', 'cancelled'].includes(schedulingStatus.phase);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Constraint Configuration */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center"><Settings className="h-5 w-5 mr-2" /> Constraint Weights</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {Object.entries(settings.constraintWeights).map(([key, value]) => (
                 <ConstraintSlider 
                    key={key}
                    label={key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                    description={`Weight for ${key.toLowerCase()} constraint`}
                    value={value} 
                    onChange={(v) => handleConstraintWeightChange(key, v)} 
                />
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Progress Tracking */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader><CardTitle>Scheduling Configuration</CardTitle></CardHeader>
            <CardContent>
              {isLoadingSessions ? (
                <div className="flex items-center space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Loading sessions...</span>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="academic-session">Academic Session</Label>
                    <Select value={selectedSession} onValueChange={setSelectedSession}>
                      <SelectTrigger id="academic-session">
                        <SelectValue placeholder="Choose a session to schedule..." />
                      </SelectTrigger>
                      <SelectContent>
                        {availableSessions?.map((session) => (
                          <SelectItem key={session.id} value={session.id}>
                            {session.name} ({new Date(session.start_date).getFullYear()})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="start-date">Start Date</Label>
                      <Input id="start-date" type="date" value={scheduleStartDate} onChange={(e) => setScheduleStartDate(e.target.value)} />
                    </div>
                    <div>
                      <Label htmlFor="end-date">End Date</Label>
                      <Input id="end-date" type="date" value={scheduleEndDate} onChange={(e) => setScheduleEndDate(e.target.value)} />
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center"><Clock className="h-5 w-5 mr-2" /> Scheduling Progress</div>
                {schedulingStatus.isRunning && <Badge variant="default" className="animate-pulse bg-blue-600">Running</Badge>}
                {!schedulingStatus.isRunning && schedulingStatus.jobId && (
                  <Badge variant={isJobFinished ? (schedulingStatus.phase === 'completed' ? 'default' : 'destructive') : 'secondary'}>
                    {schedulingStatus.phase.charAt(0).toUpperCase() + schedulingStatus.phase.slice(1)}
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Overall Progress</span>
                    <span className="text-sm text-muted-foreground">{Math.round(schedulingStatus.progress)}%</span>
                  </div>
                  <Progress value={schedulingStatus.progress} className="h-2" />
                </div>
                <Separator />
                <div className="space-y-3">
                  {phases.map((phase, index) => <PhaseIndicator key={index} {...phase} />)}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="flex items-center"><BarChart3 className="h-5 w-5 mr-2" /> Live Solver Metrics</CardTitle></CardHeader>
            <CardContent>
              {/* Metrics content here */}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Controls</CardTitle></CardHeader>
            <CardContent>
              <div className="flex items-center space-x-4">
                <Button onClick={handleStartScheduling} disabled={startScheduling.isPending || !selectedSession || !scheduleStartDate || !scheduleEndDate || schedulingStatus.isRunning} className="min-w-32">
                  <Play className="h-4 w-4 mr-2" />
                  Start Scheduling
                </Button>
                <Button variant="destructive" onClick={handleCancelScheduling} disabled={cancelScheduling.isPending || !schedulingStatus.isRunning}>
                  <Square className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
              </div>
              
              {schedulingStatus.phase === 'completed' && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg dark:bg-green-900/20 dark:border-green-800">
                  <div className="flex items-center">
                    <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                    <div>
                      <p className="font-medium text-green-800 dark:text-green-200">Scheduling Completed!</p>
                      <p className="text-sm text-green-600 dark:text-green-400">The new timetable has been generated.</p>
                      <Button variant="link" className="p-0 h-auto mt-1" onClick={() => setCurrentPage('timetable')}>
                        View Timetable &rarr;
                      </Button>
                    </div>
                  </div>
                </div>
              )}
              
              {['failed', 'error'].includes(schedulingStatus.phase) && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg dark:bg-red-900/20 dark:border-red-800">
                  <div className="flex items-center">
                    <AlertTriangle className="h-5 w-5 text-red-500 mr-3" />
                    <div>
                      <p className="font-medium text-red-800 dark:text-red-200">Scheduling Failed</p>
                      <p className="text-sm text-red-600 dark:text-red-400">{metrics.error_message || 'An unknown error occurred.'}</p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}