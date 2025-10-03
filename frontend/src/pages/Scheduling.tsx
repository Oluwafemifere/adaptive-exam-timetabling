// frontend/src/pages/Scheduling.tsx
import React, { useState } from 'react';
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

export function Scheduling() {
  const { exams, conflicts, schedulingStatus, activeSessionId, startSchedulingJob, cancelSchedulingJob } = useAppStore();
  
  const [selectedSession, setSelectedSession] = useState<string | undefined>(activeSessionId ?? undefined);
  const [selectedConfig, setSelectedConfig] = useState<string>('default');

  useJobStatusPoller(schedulingStatus.jobId);

  const handleStartJob = () => {
    if (!selectedSession) {
      // This case should be prevented by disabling the button
      return;
    }
    // In a real implementation, you'd pass selectedSession and selectedConfig
    startSchedulingJob(/* { sessionId: selectedSession, configId: selectedConfig } */);
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
              <AlertDialogTrigger asChild><Button size="lg" className="bg-green-600 hover:bg-green-700" disabled={!selectedSession}><Play className="h-4 w-4 mr-2" />Start New Job</Button></AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader><AlertDialogTitle>Start Scheduling Job?</AlertDialogTitle><AlertDialogDescription>This will start the automated timetable generation for the selected session and configuration. This may take several minutes.</AlertDialogDescription></AlertDialogHeader>
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
            <Select value={selectedSession} onValueChange={setSelectedSession} disabled={schedulingStatus.isRunning}>
              <SelectTrigger id="session-select"><SelectValue placeholder="Select a session..." /></SelectTrigger>
              <SelectContent>
                {/* Mocking sessions as they are not in the store yet */}
                <SelectItem value="a1b2c3d4-e5f6-7890-1234-567890abcdef">Fall 2025</SelectItem>
                <SelectItem value="b2c3d4e5-f6a7-8901-2345-67890abcdef1">Spring 2026</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="config-select">Constraint Configuration</Label>
            <Select value={selectedConfig} onValueChange={setSelectedConfig} disabled={schedulingStatus.isRunning}>
              <SelectTrigger id="config-select"><SelectValue placeholder="Select a configuration..." /></SelectTrigger>
              <SelectContent>
                <SelectItem value="default">Default</SelectItem>
                <SelectItem value="fast-solve">Fast Solve</SelectItem>
                <SelectItem value="high-quality">High Quality</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {schedulingStatus.isRunning && (
        <Card>
          <CardHeader><CardTitle className="text-lg flex items-center justify-between"><span>Job Status</span><Badge variant="secondary" className="capitalize"><Loader2 className="h-4 w-4 mr-2 animate-spin" />{schedulingStatus.phase}</Badge></CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div><div className="flex justify-between text-sm mb-2"><span>Overall Progress</span><span>{Math.round(schedulingStatus.progress)}%</span></div><Progress value={schedulingStatus.progress} /></div>
            <div className="text-xs text-muted-foreground">Job ID: {schedulingStatus.jobId}</div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList><TabsTrigger value="overview">Overview</TabsTrigger><TabsTrigger value="constraints">Constraints</TabsTrigger></TabsList>
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card><CardContent className="p-4 flex items-center gap-3"><Calendar className="h-8 w-8 text-blue-600" /><div><p className="text-sm text-muted-foreground">Exams to Schedule</p><p className="text-2xl font-semibold">{exams.length}</p></div></CardContent></Card>
            <Card><CardContent className="p-4 flex items-center gap-3"><Users className="h-8 w-8 text-purple-600" /><div><p className="text-sm text-muted-foreground">Total Students</p><p className="text-2xl font-semibold">{exams.reduce((sum, exam) => sum + exam.expectedStudents, 0)}</p></div></CardContent></Card>
            <Card><CardContent className="p-4 flex items-center gap-3"><AlertTriangle className="h-8 w-8 text-red-600" /><div><p className="text-sm text-muted-foreground">Initial Conflicts</p><p className="text-2xl font-semibold">{conflicts.length}</p></div></CardContent></Card>
          </div>
        </TabsContent>
        <TabsContent value="constraints">
            <Card>
                <CardHeader><CardTitle className="flex items-center gap-2"><Settings className="h-5 w-5" />Active Configuration</CardTitle></CardHeader>
                <CardContent><p className="text-sm text-muted-foreground">The scheduler will use the <span className="font-medium text-foreground">{selectedConfig}</span> configuration. You can adjust weights and rules in the Constraints page.</p></CardContent>
            </Card>
        </TabsContent>
      </Tabs>
      </div>
  );
}