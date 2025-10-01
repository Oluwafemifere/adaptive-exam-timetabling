import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip';
import { Separator } from '../components/ui/separator';
import { 
  Play, 
  Pause, 
  Square, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Settings,
  Database,
  Users,
  Calendar,
  Clock,
  MapPin,
  TrendingUp,
  Eye
} from 'lucide-react';
import { useAppStore } from '../store';
import { toast } from 'sonner';

export function Scheduling() {
  const { 
    exams, 
    conflicts, 
    schedulingStatus, 
    systemStatus,
    activeSessionId,
    startSchedulingJob,
    pauseSchedulingJob,
    resumeSchedulingJob,
    cancelSchedulingJob,
    setCurrentPage,
    addHistoryEntry,
    user
  } = useAppStore();

  const [showFailureDialog, setShowFailureDialog] = useState(false);
  const [failureReason, setFailureReason] = useState<string>('');

  // Auto-redirect on successful completion
  useEffect(() => {
    if (schedulingStatus.phase === 'completed' && schedulingStatus.progress === 100) {
      toast.success('Scheduling completed! Redirecting to timetable view...');
      setTimeout(() => {
        setCurrentPage('timetable');
      }, 2000);
    }
  }, [schedulingStatus.phase, schedulingStatus.progress, setCurrentPage]);

  // Handle job failure
  useEffect(() => {
    if (schedulingStatus.phase === 'failed') {
      setFailureReason(schedulingStatus.metrics.error_message || 'Unknown error occurred');
      setShowFailureDialog(true);
    }
  }, [schedulingStatus.phase, schedulingStatus.metrics.error_message]);

  const handleStartJob = async () => {
    if (!activeSessionId) {
      toast.error('No active session found. Please configure a session first.');
      return;
    }

    try {
      addHistoryEntry({
        action: 'Started scheduling job',
        entityType: 'schedule',
        entityId: activeSessionId,
        userId: user?.id || '',
        userName: user?.name || '',
        details: {
          sessionId: activeSessionId,
          examCount: exams.length,
          conflictCount: conflicts.length
        }
      });

      await startSchedulingJob(activeSessionId);
    } catch (error) {
      toast.error('Failed to start scheduling job');
      console.error(error);
    }
  };

  const handlePauseJob = () => {
    pauseSchedulingJob();
    toast.info('Scheduling job paused');
  };

  const handleResumeJob = () => {
    resumeSchedulingJob();
    toast.info('Scheduling job resumed');
  };

  const handleCancelJob = () => {
    cancelSchedulingJob();
    toast.warning('Scheduling job cancelled');
    addHistoryEntry({
      action: 'Cancelled scheduling job',
      entityType: 'schedule',
      entityId: schedulingStatus.jobId || '',
      userId: user?.id || '',
      userName: user?.name || '',
      details: {
        jobId: schedulingStatus.jobId,
        progress: schedulingStatus.progress
      }
    });
  };

  const getPhaseLabel = (phase: string) => {
    switch (phase) {
      case 'cp-sat': return 'Constraint Programming';
      case 'genetic-algorithm': return 'Genetic Algorithm';
      case 'completed': return 'Completed';
      case 'failed': return 'Failed';
      case 'cancelled': return 'Cancelled';
      default: return 'Idle';
    }
  };

  const getPhaseColor = (phase: string) => {
    switch (phase) {
      case 'cp-sat': return 'bg-blue-500';
      case 'genetic-algorithm': return 'bg-purple-500';
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'cancelled': return 'bg-gray-500';
      default: return 'bg-gray-300';
    }
  };

  return (
    <TooltipProvider>
      <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Exam Scheduling</h2>
          <p className="text-muted-foreground">
            Review configurations and start the scheduling process
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {!schedulingStatus.isRunning ? (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button 
                  size="lg"
                  className="bg-green-600 hover:bg-green-700"
                  disabled={exams.length === 0}
                >
                  <Play className="h-4 w-4 mr-2" />
                  Start Job
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Start Scheduling Job?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will start the automatic timetable generation process. It may take several 
                    minutes to complete depending on the complexity of your constraints and the number of exams.
                    <br /><br />
                    <strong>Current data:</strong>
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>{exams.length} exams to schedule</li>
                      <li>{conflicts.length} existing conflicts</li>
                      <li>{new Set(exams.map(e => e.room)).size} unique rooms</li>
                    </ul>
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleStartJob} className="bg-green-600 hover:bg-green-700">
                    Start Scheduling
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          ) : (
            <div className="flex gap-2">
              {schedulingStatus.canPause && (
                <Button onClick={handlePauseJob} variant="outline" size="sm">
                  <Pause className="h-4 w-4 mr-2" />
                  Pause
                </Button>
              )}
              {schedulingStatus.canResume && (
                <Button onClick={handleResumeJob} variant="outline" size="sm">
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Resume
                </Button>
              )}
              {schedulingStatus.canCancel && (
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="destructive" size="sm">
                      <Square className="h-4 w-4 mr-2" />
                      Cancel
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Cancel Scheduling Job?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will stop the current scheduling process. All progress will be lost 
                        and you'll need to start a new job to generate a timetable.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Keep Running</AlertDialogCancel>
                      <AlertDialogAction onClick={handleCancelJob} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                        Cancel Job
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Job Status */}
      {schedulingStatus.isRunning && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Job Status</CardTitle>
              <Badge variant="secondary" className="flex items-center gap-1">
                <div className={`w-2 h-2 rounded-full ${getPhaseColor(schedulingStatus.phase)}`} />
                {getPhaseLabel(schedulingStatus.phase)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>Progress</span>
                <span>{Math.round(schedulingStatus.progress)}%</span>
              </div>
              <Progress value={schedulingStatus.progress} className="h-2" />
            </div>
            
            {schedulingStatus.metrics.processed_exams !== undefined && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-muted-foreground">Processed</div>
                  <div className="font-medium">
                    {schedulingStatus.metrics.processed_exams} / {schedulingStatus.metrics.total_exams}
                  </div>
                </div>
                {schedulingStatus.metrics.generation && (
                  <div>
                    <div className="text-muted-foreground">Generation</div>
                    <div className="font-medium">{schedulingStatus.metrics.generation}</div>
                  </div>
                )}
                {schedulingStatus.metrics.fitness_score && (
                  <div>
                    <div className="text-muted-foreground">Fitness Score</div>
                    <div className="font-medium">{schedulingStatus.metrics.fitness_score}%</div>
                  </div>
                )}
                {schedulingStatus.startTime && (
                  <div>
                    <div className="text-muted-foreground">Runtime</div>
                    <div className="font-medium">
                      {Math.floor((Date.now() - new Date(schedulingStatus.startTime).getTime()) / 1000)}s
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="data">Data Summary</TabsTrigger>
          <TabsTrigger value="constraints">Constraints</TabsTrigger>
          <TabsTrigger value="system">System Status</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Calendar className="h-8 w-8 text-blue-600" />
                  <div>
                    <p className="text-sm text-muted-foreground">Total Exams</p>
                    <p className="text-2xl font-semibold">{exams.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-8 w-8 text-red-600" />
                  <div>
                    <p className="text-sm text-muted-foreground">Conflicts</p>
                    <p className="text-2xl font-semibold">{conflicts.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <MapPin className="h-8 w-8 text-green-600" />
                  <div>
                    <p className="text-sm text-muted-foreground">Unique Rooms</p>
                    <p className="text-2xl font-semibold">
                      {new Set(exams.map(e => e.room)).size}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Users className="h-8 w-8 text-purple-600" />
                  <div>
                    <p className="text-sm text-muted-foreground">Total Students</p>
                    <p className="text-2xl font-semibold">
                      {exams.reduce((sum, exam) => sum + exam.expectedStudents, 0)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Session Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Active Session
              </CardTitle>
            </CardHeader>
            <CardContent>
              {activeSessionId ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Session ID:</span>
                    <Badge variant="outline">{activeSessionId}</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Status:</span>
                    <Badge variant="default">Active</Badge>
                  </div>
                </div>
              ) : (
                <Alert>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    No active session found. Please configure a session before scheduling.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="data" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  Exam Distribution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(
                    exams.reduce((acc: Record<string, number>, exam) => {
                      exam.departments.forEach(dept => {
                        acc[dept] = (acc[dept] || 0) + 1;
                      });
                      return acc;
                    }, {})
                  ).map(([dept, count]) => (
                    <div key={dept} className="flex justify-between items-center">
                      <span className="text-sm">{dept}</span>
                      <Badge variant="secondary">{count}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Duration Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Average Duration</span>
                    <Badge variant="outline">
                      {Math.round(exams.reduce((sum, e) => sum + e.duration, 0) / exams.length || 0)}min
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Shortest Exam</span>
                    <Badge variant="outline">
                      {Math.min(...exams.map(e => e.duration))}min
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Longest Exam</span>
                    <Badge variant="outline">
                      {Math.max(...exams.map(e => e.duration))}min
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="constraints" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Constraint Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-3">Hard Constraints</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      No exam time overlaps
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      Room capacity not exceeded
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      Instructor availability
                    </div>
                  </div>
                </div>
                <div>
                  <h4 className="font-medium mb-3">Soft Constraints</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-blue-600" />
                      Minimize student conflicts
                    </div>
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-blue-600" />
                      Balanced room utilization
                    </div>
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-blue-600" />
                      Preferred time slots
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="system" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>System Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-3 h-3 rounded-full ${
                      systemStatus.constraintEngine === 'active' ? 'bg-green-500' : 
                      systemStatus.constraintEngine === 'error' ? 'bg-red-500' : 'bg-gray-500'
                    }`} />
                    <span className="font-medium">Constraint Engine</span>
                  </div>
                  <p className="text-sm text-muted-foreground capitalize">
                    {systemStatus.constraintEngine}
                  </p>
                </div>
                
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-3 h-3 rounded-full ${
                      systemStatus.autoResolution ? 'bg-green-500' : 'bg-gray-500'
                    }`} />
                    <span className="font-medium">Auto Resolution</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {systemStatus.autoResolution ? 'Enabled' : 'Disabled'}
                  </p>
                </div>
                
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium">Data Sync</span>
                  </div>
                  <div className="space-y-1">
                    <Progress value={systemStatus.dataSyncProgress} className="h-2" />
                    <p className="text-sm text-muted-foreground">
                      {systemStatus.dataSyncProgress}% complete
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Failure Dialog */}
      <Dialog open={showFailureDialog} onOpenChange={setShowFailureDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <XCircle className="h-5 w-5" />
              Scheduling Failed
            </DialogTitle>
            <DialogDescription>
              The scheduling process could not complete successfully. Review the issues below and take the suggested actions.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                The scheduling job could not find a feasible solution with the current constraints.
              </AlertDescription>
            </Alert>
            
            <div>
              <h4 className="font-medium mb-2">Possible Reasons:</h4>
              <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                <li>Room capacity constraints too restrictive</li>
                <li>Instructor availability conflicts</li>
                <li>Too many exams scheduled in limited time slots</li>
                <li>Conflicting student enrollments</li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-medium mb-2">Suggested Actions:</h4>
              <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                <li>Review and adjust constraint weights</li>
                <li>Add more available rooms or time slots</li>
                <li>Check instructor availability</li>
                <li>Consider splitting large exams</li>
              </ul>
            </div>
            
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                onClick={() => setCurrentPage('constraints')}
                className="flex-1"
              >
                <Settings className="h-4 w-4 mr-2" />
                Adjust Constraints
              </Button>
              <Button 
                variant="outline" 
                onClick={() => setCurrentPage('analytics')}
                className="flex-1"
              >
                <Eye className="h-4 w-4 mr-2" />
                View Analytics
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      </div>
    </TooltipProvider>
  );
}