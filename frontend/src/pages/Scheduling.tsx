import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { Play, Square, Settings, Terminal, CheckCircle, XCircle, Zap, History, Eye, Loader2 } from 'lucide-react';
import { useAppStore } from '../store';
import { useJobStatusSocket, useJobHistoryData } from '../hooks/useApi';
import { toast } from 'sonner';
import { api } from '../services/api';
import { ScrollArea } from '../components/ui/scroll-area';
import { cn } from '../utils/utils';
import { formatDistanceToNow } from 'date-fns';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';

export function Scheduling() {
  const {
    activeSessionId,
    startSchedulingJob,
    cancelSchedulingJob,
    configurations,
    activeConfigurationId,
    setConfigurations,
    schedulingStatus,
    fetchAndSetJobResult,
    setCurrentPage,
  } = useAppStore();

  const [selectedConfig, setSelectedConfig] = useState<string | undefined>(undefined);
  const logsEndRef = useRef<HTMLDivElement>(null);
  
  const { jobs, isLoading: isHistoryLoading, refetch: refetchHistory } = useJobHistoryData();

  useEffect(() => {
    setSelectedConfig(activeConfigurationId ?? undefined);
  }, [activeConfigurationId]);

  useEffect(() => {
    const fetchSystemConfigs = async () => {
        try {
          const response = await api.getSystemConfigurationList();
          const systemConfigs = response.data || [];
          setConfigurations(systemConfigs);

          const defaultConfig = systemConfigs.find(c => c.is_default);
          if (defaultConfig) {
            setSelectedConfig(defaultConfig.id);
          } else if (systemConfigs.length > 0) {
            setSelectedConfig(systemConfigs[0].id);
          }

        } catch (err) {
          console.error("Failed to load system configurations:", err);
          toast.error("Failed to load system configurations from backend.");
        }
    };
    fetchSystemConfigs();
  }, [setConfigurations]);

  useJobStatusSocket(schedulingStatus.jobId);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [schedulingStatus.logs]);
  
  // Refetch history when a job is no longer running
  useEffect(() => {
    if (!schedulingStatus.isRunning && schedulingStatus.jobId) {
      refetchHistory();
    }
  }, [schedulingStatus.isRunning, schedulingStatus.jobId, refetchHistory]);

  const handleStartJob = () => {
    if (!activeSessionId) {
      toast.error("No active session selected. Please set one up first.");
      return;
    }
    if (!selectedConfig) {
      toast.error("Please select a constraint configuration to run the job.");
      return;
    }
    startSchedulingJob(selectedConfig);
  };

  const handleCancelJob = () => {
    if (schedulingStatus.jobId) {
      cancelSchedulingJob(schedulingStatus.jobId);
    }
  };

  const handleViewTimetable = (jobId: string) => {
    toast.promise(
      async () => {
        await fetchAndSetJobResult(jobId);
        setCurrentPage('timetable');
      },
      {
        loading: 'Loading timetable data...',
        success: 'Timetable loaded successfully!',
        error: 'Failed to load the selected timetable.',
      }
    );
  };

  const getStatusIndicator = () => {
    if (schedulingStatus.isRunning) {
      return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
    }
    if (schedulingStatus.phase === 'completed') {
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    }
    if (['failed', 'cancelled', 'error'].includes(schedulingStatus.phase)) {
      return <XCircle className="h-5 w-5 text-red-500" />;
    }
    return <Zap className="h-5 w-5 text-gray-400" />;
  };

  const getLogLineClass = (log: string) => {
    if (log.startsWith('[ERROR]')) return 'text-destructive';
    if (log.startsWith('[SUCCESS]')) return 'text-green-600 dark:text-green-400';
    if (log.startsWith('[INFO]')) return 'text-blue-600 dark:text-blue-400';
    if (log.startsWith('[WARNING]')) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-muted-foreground';
  };
  
  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'completed': return 'default';
      case 'failed':
      case 'cancelled': return 'destructive';
      default: return 'secondary';
    }
  };

  return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div><h2 className="text-xl font-semibold">Exam Scheduling</h2><p className="text-muted-foreground">Initiate and monitor the automated scheduling solver</p></div>
          <div className="flex items-center gap-2">
            {!schedulingStatus.isRunning ? (
              <AlertDialog>
                <AlertDialogTrigger asChild><Button size="lg" className="bg-green-600 hover:bg-green-700" disabled={!activeSessionId || !selectedConfig}><Play className="h-4 w-4 mr-2" />Start New Job</Button></AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader><AlertDialogTitle>Start Scheduling Job?</AlertDialogTitle><AlertDialogDescription>This will start automated timetable generation using the '{configurations.find(c => c.id === selectedConfig)?.name || 'selected'}' configuration. This may take several minutes.</AlertDialogDescription></AlertDialogHeader>
                  <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={handleStartJob} className="bg-green-600 hover:bg-green-700">Start Scheduling</AlertDialogAction></AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            ) : (
              <AlertDialog>
                <AlertDialogTrigger asChild><Button variant="destructive" size="sm"><Square className="h-4 w-4 mr-2" />Cancel Job</Button></AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader><AlertDialogTitle>Cancel Running Job?</AlertDialogTitle><AlertDialogDescription>This will stop the current scheduling process. Progress will be lost.</AlertDialogDescription></AlertDialogHeader>
                  <AlertDialogFooter><AlertDialogCancel>Keep Running</AlertDialogCancel><AlertDialogAction onClick={handleCancelJob} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">Cancel Job</AlertDialogAction></AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
        </div>

        <Card>
          <CardHeader><CardTitle>Job Configuration</CardTitle><CardDescription>Select the constraint configuration to use for scheduling.</CardDescription></CardHeader>
          <CardContent>
              <div className="space-y-2">
                <Label htmlFor="config-select">Constraint Configuration</Label>
                <Select value={selectedConfig ?? ""} onValueChange={setSelectedConfig} disabled={schedulingStatus.isRunning}>
                  <SelectTrigger id="config-select"><SelectValue placeholder="Select a configuration..." /></SelectTrigger>
                  <SelectContent>
                    {configurations.map(config => (
                      <SelectItem key={config.id} value={config.id}>{config.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
          </CardContent>
        </Card>

        {(schedulingStatus.isRunning || schedulingStatus.logs.length > 0) && (
          <Card className="bg-secondary text-secondary-foreground">
            <CardHeader>
              <div className="flex items-center gap-3">
                {getStatusIndicator()}
                <div>
                  <CardTitle className="text-lg">Job Monitor</CardTitle>
                  <CardDescription className="text-muted-foreground">Real-time status of the active scheduling job.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                  <div className="flex justify-between items-center text-sm font-medium text-secondary-foreground">
                    <span className="capitalize">Status: {schedulingStatus.phase.replace(/_/g, ' ')}</span>
                    <span className="font-bold text-lg">{Math.round(schedulingStatus.progress)}%</span>
                  </div>
                  <Progress value={schedulingStatus.progress} className="[&>div]:bg-green-500" />
              </div>

              <div className="space-y-3">
                <Label className="flex items-center gap-2 text-base"><Terminal className="h-5 w-5" /> Live Logs</Label>
                <ScrollArea className="h-64 w-full rounded-md bg-background p-4 border">
                  <div className="text-sm font-mono whitespace-pre-wrap break-all">
                    {schedulingStatus.logs.map((log, index) => (
                      <p key={index} className={cn("leading-relaxed", getLogLineClass(log))}>
                        <span className="mr-2">{`> `}</span>{log}
                      </p>
                    ))}
                    <div ref={logsEndRef} />
                  </div>
                </ScrollArea>
              </div>
            </CardContent>
          </Card>
        )}
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center"><History className="h-5 w-5 mr-2" />Job History</CardTitle>
            <CardDescription>Review of past and ongoing scheduling jobs for this session.</CardDescription>
          </CardHeader>
          <CardContent>
            {isHistoryLoading ? (
              <div className="flex justify-center items-center h-40"><Loader2 className="h-8 w-8 animate-spin text-muted-foreground" /></div>
            ) : jobs.length === 0 ? (
              <p className="text-center text-muted-foreground py-10">No job history found for this session.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Initiated</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow key={job.id}>
                      <TableCell>
                        <Badge variant={getStatusBadgeVariant(job.status)} className="capitalize">{job.status}</Badge>
                      </TableCell>
                      <TableCell>{formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}</TableCell>
                      <TableCell>
                        {job.started_at && job.completed_at
                          ? `${(Math.abs(new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()) / 60000).toFixed(2)} min`
                          : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewTimetable(job.id)}
                          disabled={job.status !== 'completed'}
                        >
                          <Eye className="h-4 w-4 mr-2" />
                          View Timetable
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
  );
}