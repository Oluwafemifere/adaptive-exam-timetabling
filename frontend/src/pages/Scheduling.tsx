import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { Play, Square, AlertTriangle, Settings, Calendar, Users, Loader2, Terminal } from 'lucide-react';
import { useAppStore } from '../store';
import { useJobStatusSocket } from '../hooks/useApi';
import { toast } from 'sonner';
import { api } from '../services/api';
import { ScrollArea } from '../components/ui/scroll-area'; // Import ScrollArea

export function Scheduling() {
  const { 
    activeSessionId, 
    startSchedulingJob, 
    cancelSchedulingJob,
    configurations,
    activeConfigurationId,
    setConfigurations,
    schedulingStatus, // Get the full status object
  } = useAppStore();
  
  const [selectedConfig, setSelectedConfig] = useState<string | undefined>(undefined);

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
                {/* --- FIX: Controlled component --- */}
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
      
        {/* --- ADDITION: Job Status & Logs --- */}
        {(schedulingStatus.isRunning || schedulingStatus.logs.length > 0) && (
          <Card>
            <CardHeader>
              <CardTitle>Job Monitor</CardTitle>
              <CardDescription>Real-time status of the active scheduling job.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="flex-1 space-y-2">
                    <div className="flex justify-between text-sm font-medium">
                      <span>Status: <span className="capitalize">{schedulingStatus.phase.replace(/_/g, ' ')}</span></span>
                      <span>{Math.round(schedulingStatus.progress)}%</span>
                    </div>
                    <Progress value={schedulingStatus.progress} />
                </div>
                {schedulingStatus.isRunning && <Loader2 className="h-6 w-6 animate-spin text-primary" />}
              </div>
              
              <div className="space-y-2">
                <Label className="flex items-center gap-2"><Terminal className="h-4 w-4" /> Live Logs</Label>
                <ScrollArea className="h-48 w-full rounded-md border bg-muted p-4">
                  <div className="text-sm font-mono whitespace-pre-wrap break-all">
                    {schedulingStatus.logs.map((log, index) => (
                      <p key={index} className="leading-relaxed">{log}</p>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
  );
}