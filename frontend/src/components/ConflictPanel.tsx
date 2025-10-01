import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from './ui/dialog';
import { Progress } from './ui/progress';
import { Separator } from './ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  CheckCircle, 
  Zap, 
  Download, 
  Eye, 
  Calendar,
  MapPin,
  Users,
  Clock,
  RefreshCw,
  Lock,
  Unlock
} from 'lucide-react';
import { Conflict } from '../store/types';
import { useAppStore } from '../store';
import { toast } from 'sonner';

interface ConflictPanelProps {
  conflicts: Conflict[];
  onResolveConflict?: (conflictId: string) => void;
  onAutoResolve?: () => void;
  onExportReport?: () => void;
  onViewConflict?: (conflictId: string) => void;
}

export function ConflictPanel({ 
  conflicts = [], 
  onResolveConflict, 
  onAutoResolve, 
  onExportReport,
  onViewConflict 
}: ConflictPanelProps) {
  const [autoResolving, setAutoResolving] = useState(false);
  const [autoResolveProgress, setAutoResolveProgress] = useState(0);
  const [showConflictDetails, setShowConflictDetails] = useState<string | null>(null);
  const { exams, user, addHistoryEntry } = useAppStore();

  const safeConflicts = conflicts || [];
  const hardConflicts = safeConflicts.filter(c => c.type === 'hard');
  const softConflicts = safeConflicts.filter(c => c.type === 'soft');

  const conflictsByPriority = {
    high: safeConflicts.filter(c => c.severity === 'high'),
    medium: safeConflicts.filter(c => c.severity === 'medium'),
    low: safeConflicts.filter(c => c.severity === 'low')
  };

  const autoResolvableCount = safeConflicts.filter(c => c.autoResolvable).length;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high': return AlertTriangle;
      case 'medium': return AlertCircle;
      case 'low': return Info;
      default: return Info;
    }
  };

  const handleAutoResolve = async () => {
    if (!onAutoResolve) return;

    setAutoResolving(true);
    setAutoResolveProgress(0);

    // Simulate auto-resolve progress
    const interval = setInterval(() => {
      setAutoResolveProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setAutoResolving(false);
          onAutoResolve();
          addHistoryEntry({
            action: 'Auto-resolved conflicts',
            entityType: 'schedule',
            userId: user?.id || '',
            userName: user?.name || '',
            details: {
              resolvedCount: autoResolvableCount,
              totalConflicts: safeConflicts.length
            }
          });
          toast.success(`Auto-resolved ${autoResolvableCount} conflicts`);
          return 100;
        }
        return prev + 5;
      });
    }, 100);
  };

  const handleExportReport = () => {
    if (!onExportReport) return;

    // Create CSV content
    const csvContent = [
      ['Type', 'Severity', 'Message', 'Affected Exams', 'Auto-Resolvable'].join(','),
      ...safeConflicts.map(conflict => [
        conflict.type,
        conflict.severity,
        `"${conflict.message}"`,
        conflict.examIds.length,
        conflict.autoResolvable ? 'Yes' : 'No'
      ].join(','))
    ].join('\n');

    // Download the report
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conflict-report-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    addHistoryEntry({
      action: 'Exported conflict report',
      entityType: 'schedule',
      userId: user?.id || '',
      userName: user?.name || '',
      details: {
        totalConflicts: safeConflicts.length,
        hardConflicts: hardConflicts.length,
        softConflicts: softConflicts.length
      }
    });

    toast.success('Conflict report exported successfully');
  };

  const getConflictDetails = (conflictId: string) => {
    const conflict = safeConflicts.find(c => c.id === conflictId);
    if (!conflict) return null;

    const affectedExams = exams.filter(exam => conflict.examIds.includes(exam.id));
    return { conflict, affectedExams };
  };

  if (safeConflicts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            Conflict Management
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-4" />
            <h3 className="font-medium text-lg mb-2">No Conflicts Found</h3>
            <p className="text-muted-foreground">
              All exams are properly scheduled without conflicts.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            Conflict Management
            <Badge variant="destructive" className="ml-2">
              {safeConflicts.length}
            </Badge>
          </CardTitle>
          <div className="flex items-center gap-2">
            {autoResolvableCount > 0 && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={handleAutoResolve}
                      disabled={autoResolving}
                      size="sm"
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {autoResolving ? (
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Zap className="h-4 w-4 mr-2" />
                      )}
                      Auto Resolve ({autoResolvableCount})
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Automatically resolve {autoResolvableCount} resolvable conflicts</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
            <Button
              onClick={handleExportReport}
              variant="outline"
              size="sm"
            >
              <Download className="h-4 w-4 mr-2" />
              Export Report
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Auto-resolve progress */}
        {autoResolving && (
          <Alert>
            <RefreshCw className="h-4 w-4 animate-spin" />
            <AlertDescription>
              <div className="space-y-2">
                <span>Auto-resolving conflicts...</span>
                <Progress value={autoResolveProgress} className="h-2" />
              </div>
            </AlertDescription>
          </Alert>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-8 w-8 text-red-600" />
                <div>
                  <p className="text-sm text-muted-foreground">Hard Conflicts</p>
                  <p className="text-2xl font-semibold">{hardConflicts.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-8 w-8 text-yellow-600" />
                <div>
                  <p className="text-sm text-muted-foreground">Soft Conflicts</p>
                  <p className="text-2xl font-semibold">{softConflicts.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Zap className="h-8 w-8 text-blue-600" />
                <div>
                  <p className="text-sm text-muted-foreground">Auto-Resolvable</p>
                  <p className="text-2xl font-semibold">{autoResolvableCount}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-8 w-8 text-red-600" />
                <div>
                  <p className="text-sm text-muted-foreground">High Priority</p>
                  <p className="text-2xl font-semibold">{conflictsByPriority.high.length}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Conflict List by Priority */}
        <div className="space-y-4">
          {(['high', 'medium', 'low'] as const).map(priority => {
            const priorityConflicts = conflictsByPriority[priority];
            if (priorityConflicts.length === 0) return null;

            const Icon = getSeverityIcon(priority);

            return (
              <div key={priority}>
                <div className="flex items-center gap-2 mb-3">
                  <Icon className="h-4 w-4" />
                  <h4 className="font-medium capitalize">{priority} Priority Conflicts</h4>
                  <Badge variant="secondary">{priorityConflicts.length}</Badge>
                </div>
                <div className="space-y-2">
                  {priorityConflicts.slice(0, 5).map(conflict => (
                    <div
                      key={conflict.id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
                    >
                      <div className="flex items-start gap-3 flex-1">
                        <div className={`w-3 h-3 rounded-full ${getSeverityColor(conflict.severity)} mt-1`} />
                        <div className="flex-1">
                          <p className="text-sm font-medium">{conflict.message}</p>
                          <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {conflict.examIds.length} exam{conflict.examIds.length !== 1 ? 's' : ''}
                            </span>
                            {conflict.autoResolvable && (
                              <span className="flex items-center gap-1 text-blue-600">
                                <Zap className="h-3 w-3" />
                                Auto-resolvable
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setShowConflictDetails(conflict.id)}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl">
                            <DialogHeader>
                              <DialogTitle className="flex items-center gap-2">
                                <Icon className="h-5 w-5" />
                                Conflict Details
                              </DialogTitle>
                              <DialogDescription>
                                View detailed information about this scheduling conflict and affected exams.
                              </DialogDescription>
                            </DialogHeader>
                            <ConflictDetailsDialog conflictId={conflict.id} />
                          </DialogContent>
                        </Dialog>
                        {onResolveConflict && (
                          <Button
                            onClick={() => onResolveConflict(conflict.id)}
                            variant="outline"
                            size="sm"
                            disabled={autoResolving}
                          >
                            Resolve
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                  {priorityConflicts.length > 5 && (
                    <p className="text-sm text-muted-foreground text-center">
                      ... and {priorityConflicts.length - 5} more
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function ConflictDetailsDialog({ conflictId }: { conflictId: string }) {
  const { conflicts, exams } = useAppStore();
  const safeConflicts = conflicts || [];
  const conflict = safeConflicts.find(c => c.id === conflictId);
  
  if (!conflict) return null;

  const affectedExams = exams.filter(exam => conflict.examIds.includes(exam.id));

  return (
    <div className="space-y-4">
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          <div className="space-y-2">
            <p><strong>Type:</strong> {conflict.type} conflict</p>
            <p><strong>Severity:</strong> {conflict.severity}</p>
            <p><strong>Auto-resolvable:</strong> {conflict.autoResolvable ? 'Yes' : 'No'}</p>
          </div>
        </AlertDescription>
      </Alert>

      <div>
        <h4 className="font-medium mb-2">Description</h4>
        <p className="text-sm text-muted-foreground">{conflict.message}</p>
      </div>

      <div>
        <h4 className="font-medium mb-3">Affected Exams ({affectedExams.length})</h4>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {affectedExams.map(exam => (
            <div key={exam.id} className="flex items-center justify-between p-3 border rounded">
              <div>
                <p className="font-medium">{exam.courseCode} - {exam.courseName}</p>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {exam.date}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {exam.startTime} - {exam.endTime}
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {exam.room}
                  </span>
                  <span className="flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    {exam.expectedStudents}
                  </span>
                </div>
              </div>
              <Badge variant="outline">
                {exam.departments.join(', ')}
              </Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}