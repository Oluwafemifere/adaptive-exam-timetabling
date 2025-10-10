// frontend/src/pages/Dashboard.tsx
import { useEffect, useState } from 'react';
import { 
  Calendar, 
  AlertTriangle, 
  Building2, 
  Upload,
  PlayCircle,
  Loader2,
  Users,
  Library,
  ClipboardList,
  Activity,
  MapPin,
  UserX,
  History,
  CheckCircle,
  Settings,
  Server,
  Clock,
  FileWarning
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { cn } from '../components/ui/utils'
import { useAppStore } from '../store'
import { useDashboardData } from '../hooks/useApi'
import { formatDistanceToNow } from 'date-fns';

const formatTimeAgo = (dateString: string) => {
  if (!dateString) return 'N/A';
  return formatDistanceToNow(new Date(dateString), { addSuffix: true });
};


export function Dashboard() {
  const { 
    setCurrentPage, 
    initializeApp, 
    activeSessionId, 
    dashboardKpis, 
    conflictHotspots, 
    recentActivity,
    reportSummaryCounts,
    sessionJobs,
    allConflictReports,
    allChangeRequests
  } = useAppStore()
  const { isLoading, error } = useDashboardData();
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const init = async () => {
      if (!activeSessionId) {
        await initializeApp();
      }
      setIsInitializing(false);
    };
    init();
  }, [initializeApp, activeSessionId]);

  const latestJob = sessionJobs?.[0];
  const pendingItems = [
    ...(allConflictReports || []).filter(r => r.status === 'pending').map(r => ({ ...r, type: 'Conflict Report' as const })),
    ...(allChangeRequests || []).filter(r => r.status === 'pending').map(r => ({ ...r, type: 'Change Request' as const }))
  ].sort((a, b) => new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime());


  const isDataMissing = !isLoading && !isInitializing && !dashboardKpis;
  
  const getActivityIcon = (activityAction: string) => {
    const action = activityAction.toLowerCase();
    if (action.includes('move') || action.includes('edit')) return Settings;
    if (action.includes('generate') || action.includes('system')) return CheckCircle;
    if (action.includes('lock')) return AlertTriangle;
    if (action.includes('upload')) return Upload;
    if (action.includes('optimiz')) return PlayCircle;
    return History;
  }

  if (isInitializing) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
        <h2 className="text-xl font-semibold">Initializing Application</h2>
        <p className="text-muted-foreground mt-2">Fetching active academic session...</p>
      </div>
    );
  }

  if (isLoading && !dashboardKpis) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => ( <Card key={i} className="h-32"><CardContent className="p-6"></CardContent></Card> ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <Card className="lg:col-span-4 h-96"></Card>
          <Card className="lg:col-span-4 h-96"></Card>
          <Card className="lg:col-span-4 h-96"></Card>
        </div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] text-center">
        <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold text-destructive">Failed to Load Dashboard Data</h2>
        <p className="text-muted-foreground mt-2">{error.message}</p>
        <Button onClick={() => window.location.reload()} className="mt-4">Retry</Button>
      </div>
    )
  }

  if (isDataMissing) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <Card className="w-full max-w-lg text-center p-8">
          <CardHeader>
            <CardTitle>Welcome to the Exam Scheduler</CardTitle>
            <CardDescription>To begin, you need to upload your academic session data.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="mb-6 text-muted-foreground">Please upload the required CSV files for students, courses, registrations, and rooms.</p>
            <Button onClick={() => setCurrentPage('upload')}><Upload className="h-4 w-4 mr-2" />Go to Upload Page</Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Exams Scheduled</p>
              <p className="text-3xl font-bold text-foreground">{dashboardKpis?.total_exams_scheduled ?? 0}</p>
              <p className="text-xs text-muted-foreground mt-1">For the active session</p>
            </div>
            <div className="p-3 bg-blue-100 dark:bg-blue-900/50 rounded-full"><Calendar className="h-6 w-6 text-blue-600 dark:text-blue-300" /></div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Unresolved Conflicts</p>
              <p className="text-3xl font-bold text-foreground">{(dashboardKpis?.unresolved_hard_conflicts ?? 0) + (dashboardKpis?.total_soft_conflicts ?? 0)}</p>
               <p className="text-xs text-muted-foreground mt-1">{dashboardKpis?.unresolved_hard_conflicts ?? 0} Hard / {dashboardKpis?.total_soft_conflicts ?? 0} Soft</p>
            </div>
            <div className={cn("p-3 rounded-full", (dashboardKpis?.unresolved_hard_conflicts ?? 0) > 0 ? "bg-red-100 dark:bg-red-900/50" : "bg-yellow-100 dark:bg-yellow-900/50")}>
              <AlertTriangle className={cn("h-6 w-6", (dashboardKpis?.unresolved_hard_conflicts ?? 0) > 0 ? "text-red-600 dark:text-red-300" : "text-yellow-600 dark:text-yellow-300")} />
            </div>
          </div>
        </Card>
        
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Data Health Summary</p>
              <p className="text-2xl font-bold text-foreground">5,210 <span className="text-sm font-medium text-muted-foreground">Students</span></p>
              <p className="text-2xl font-bold text-foreground">435 <span className="text-sm font-medium text-muted-foreground">Courses</span></p>
            </div>
            <div className="p-3 bg-green-100 dark:bg-green-900/50 rounded-full"><Server className="h-6 w-6 text-green-600 dark:text-green-300" /></div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Action Required</p>
              <p className="text-3xl font-bold text-foreground">{reportSummaryCounts?.total ?? 0}</p>
              <p className="text-xs text-muted-foreground mt-1">Pending reports & requests</p>
            </div>
            <div className="p-3 bg-purple-100 dark:bg-purple-900/50 rounded-full"><ClipboardList className="h-6 w-6 text-purple-600 dark:text-purple-300" /></div>
          </div>
        </Card>
      </div>

      {/* Dashboard Widgets */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <Card className="lg:col-span-4">
          <CardHeader><CardTitle className="flex items-center"><AlertTriangle className="h-5 w-5 mr-2" />Conflict Hotspots</CardTitle><CardDescription>Time slots with the highest conflict density</CardDescription></CardHeader>
          <CardContent>
            <div className="space-y-3">
              {conflictHotspots.slice(0, 5).map((hotspot, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center space-x-3"><div className="text-sm font-medium">{hotspot.timeslot}</div><Badge variant={hotspot.conflict_count > 5 ? 'destructive' : hotspot.conflict_count > 3 ? 'secondary' : 'outline'}>{hotspot.conflict_count} conflicts</Badge></div>
                  <Button variant="ghost" size="sm" onClick={() => setCurrentPage('timetable')}>View</Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-4">
          <CardHeader><CardTitle className="flex items-center"><Clock className="h-5 w-5 mr-2" />Latest Job Run</CardTitle><CardDescription>Status of the most recent timetable generation</CardDescription></CardHeader>
          <CardContent>
            {latestJob ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <p className="font-semibold">Status</p>
                  <Badge variant={latestJob.status === 'completed' ? 'default' : 'destructive'}>{latestJob.status}</Badge>
                </div>
                 <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <p className="font-semibold">Completed</p>
                  <p className="text-sm text-muted-foreground">{formatTimeAgo(latestJob.created_at)}</p>
                </div>
                 <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <p className="font-semibold">Room Utilization</p>
                  <p className="text-sm font-bold">{dashboardKpis?.overall_room_utilization.toFixed(1) ?? 0}%</p>
                </div>
                <Button className="w-full" onClick={() => setCurrentPage('scheduler')}>Go to Scheduler</Button>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-muted-foreground">No timetable jobs have been run for this session yet.</p>
                <Button className="mt-4" onClick={() => setCurrentPage('scheduler')}>Run First Job</Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-4 flex flex-col">
          <CardHeader><CardTitle className="flex items-center"><Activity className="h-5 w-5 mr-2" />Recent Activity</CardTitle><CardDescription>Latest actions and system events</CardDescription></CardHeader>
          <CardContent className="flex-1 overflow-hidden">
            <div className="space-y-3 h-full overflow-y-auto max-h-[20rem] pr-2">
              {recentActivity.map((activity) => {
                  const Icon = getActivityIcon(activity.action);
                  return (
                    <div key={activity.id} className="flex items-start space-x-3 p-3 bg-muted/50 rounded-lg">
                      <div className="p-1 rounded-full mt-0.5 bg-gray-100 dark:bg-gray-800">
                        <Icon className="h-3 w-3 text-gray-600 dark:text-gray-300" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{activity.action}</p>
                        <div className="flex items-center space-x-2 mt-1">
                          <p className="text-xs text-muted-foreground truncate">{activity.userName}</p>
                          <span className="text-xs text-muted-foreground">•</span>
                          <p className="text-xs text-muted-foreground flex-shrink-0">{formatTimeAgo(activity.timestamp)}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-12">
            <CardHeader><CardTitle className="flex items-center"><FileWarning className="h-5 w-5 mr-2" />Pending Approvals</CardTitle><CardDescription>Actionable reports and requests awaiting review</CardDescription></CardHeader>
            <CardContent>
                {pendingItems.length > 0 ? (
                    <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
                        {pendingItems.map((item, index) => (
                            <div key={index} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                                <div className="flex items-center space-x-3 min-w-0">
                                    <Badge variant={item.type === 'Conflict Report' ? 'destructive' : 'secondary'}>{item.type}</Badge>
                                    <div className="min-w-0 flex-1">
                                        {item.type === 'Conflict Report' ? (
                                            <>
                                                <p className="text-sm font-medium truncate">
                                                    {`Student: ${item.student.first_name} ${item.student.last_name}`}
                                                </p>
                                                <p className="text-xs text-muted-foreground truncate">{item.description}</p>
                                            </>
                                        ) : (
                                            <>
                                                <p className="text-sm font-medium truncate">
                                                   {`Staff: ${item.staff.first_name} ${item.staff.last_name}`}
                                                </p>
                                                <p className="text-xs text-muted-foreground truncate">{item.reason}</p>
                                            </>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center space-x-4">
                                  <p className="text-xs text-muted-foreground flex-shrink-0">{formatTimeAgo(item.submitted_at)}</p>
                                  <Button variant="ghost" size="sm" onClick={() => setCurrentPage('requests')}>Review</Button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-8">
                        <CheckCircle className="h-10 w-10 text-green-500 mx-auto mb-2" />
                        <p className="text-muted-foreground font-semibold">All Clear!</p>
                        <p className="text-sm text-muted-foreground">There are no pending reports or requests.</p>
                    </div>
                )}
            </CardContent>
        </Card>
      </div>
    </div>
  )
}