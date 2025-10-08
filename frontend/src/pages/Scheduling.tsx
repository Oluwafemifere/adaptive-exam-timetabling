// frontend/src/pages/Scheduling.tsx
import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { Play, Square, AlertTriangle, Settings, Calendar, Users, Loader2 } from 'lucide-react';
import { useAppStore } from '../store';
import { useJobStatusPoller } from '../hooks/useApi';
import { toast } from 'sonner';
import { api } from '../services/api';

export function Scheduling() {
  const { 
    exams, 
    conflicts, 
    schedulingStatus, 
    activeSessionId, 
    startSchedulingJob, 
    cancelSchedulingJob,
    configurations,
    activeConfigurationId,
    setConfigurations,

  } = useAppStore();
  
  // Local state for the selected configuration, synced with the global store
  const [selectedConfig, setSelectedConfig] = useState<string | undefined>(undefined);

  useEffect(() => {
    // Keep local selection in sync with the global active configuration
    setSelectedConfig(activeConfigurationId ?? undefined);
  }, [activeConfigurationId]);

 useEffect(() => {
    // This effect runs only once to fetch the correct list for this page
    const fetchSystemConfigs = async () => {
        try {
          // Call the new, correct API endpoint for this page's purpose
          const response = await api.getAllSystemConfigurations();
          const systemConfigs = response.data || [];
          setConfigurations(systemConfigs); // Populate the store/dropdown
          
          // Find the default and set it as the initial selection
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

  useJobStatusPoller(schedulingStatus.jobId);

  const handleStartJob = () => {
    if (!activeSessionId) {
      toast.error("No active session selected. Please set one up first.");
      return;
    }
    if (!selectedConfig) {
      toast.error("Please select a constraint configuration to run the job.");
      return;
    }
    // The actual API call is now handled inside the Zustand action
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
              <AlertDialogTrigger asChild><Button size="lg" className="bg-green-600 hover:bg-green-700" disabled={!activeSessionId}><Play className="h-4 w-4 mr-2" />Start New Job</Button></AlertDialogTrigger>
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
        <CardHeader><CardTitle>Job Configuration</CardTitle><CardDescription>Select the academic session and constraint configuration to use for scheduling.</CardDescription></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <Label htmlFor="session-select">Academic Session</Label>
            <Select value={activeSessionId ?? ""} disabled>
              <SelectTrigger id="session-select"><SelectValue placeholder="No active session..." /></SelectTrigger>
              <SelectContent>
                {activeSessionId && <SelectItem value={activeSessionId}>Active Session</SelectItem>}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="config-select">Constraint Configuration</Label>
            <Select value={selectedConfig} onValueChange={setSelectedConfig} disabled={schedulingStatus.isRunning}>
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
      
      {/* ... (Rest of the component remains the same) ... */}
      </div>
  );
}