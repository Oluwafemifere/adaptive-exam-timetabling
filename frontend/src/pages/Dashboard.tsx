// frontend/src/pages/Dashboard.tsx
import { useEffect, useState } from 'react';
import { 
  Calendar, 
  AlertTriangle, 
  Upload,
  PlayCircle,
  Loader2,
  ClipboardList,
  Activity,
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
import { useDashboardData, useAllReportsData } from '../hooks/useApi'
import { formatDistanceToNow } from 'date-fns';
import { AdminChangeRequest, AdminConflictReport } from '../store/types';

const formatTimeAgo = (dateString: string | undefined | null) => {
  if (!dateString) return 'N/A';
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true });
  } catch (e) {
    return 'N/A';
  }
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
    fetchSessionJobs,
    allConflictReports,
    allChangeRequests
  } = useAppStore()

  // Fetch KPI, Hotspots, Activity data
  const { isLoading: isDashboardLoading, error: dashboardError } = useDashboardData();
  // Fetch Pending Reports data
  const { isLoading: isReportsLoading } = useAllReportsData({ statuses: ['pending'] });
  
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    const init = async () => {
      // 1. Ensure app is initialized (session/user loaded)
      if (!activeSessionId) {
        await initializeApp();
      }
      
      // 2. Get current session ID from store after initialization attempt
      const currentSessionId = useAppStore.getState().activeSessionId;
      
      // 3. If session exists, fetch historical jobs for the "Latest Job" widget
      if (currentSessionId) {
        fetchSessionJobs(currentSessionId);
      }
      
      setIsInitializing(false);
    };
    init();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]); // rely on activeSessionId changes to trigger data fetches

  const latestJob = sessionJobs && sessionJobs.length > 0 ? sessionJobs[0] : null;

  // Combine and sort pending reports/requests for the UI
  const pendingItems = [
    ...(allConflictReports || []).filter(r => r.status === 'pending').map(r => ({ ...r, uiType: 'Conflict Report' as const })),
    ...(allChangeRequests || []).filter(r => r.status === 'pending').map(r => ({ ...r, uiType: 'Change Request' as const }))
  ].sort((a, b) => new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime());

  const isLoading = isDashboardLoading || isReportsLoading;
  // Data is considered missing if not loading, not initializing, and no KPIs are returned.
  const isDataMissing = !isLoading && !isInitializing && !dashboardKpis && activeSessionId;
  const noActiveSession = !isLoading && !isInitializing && !activeSessionId;
  
  const getActivityIcon = (activityAction: string) => {
    const action = activityAction.toLowerCase();
    if (action.includes('move') || action.includes('edit') || action.includes('configuration')) return Settings;
    if (action.includes('generate') || action.includes('publish')) return CheckCircle;
    if (action.includes('lock')) return AlertTriangle;
    if (action.includes('upload') || action.includes('import')) return Upload;
    if (action.includes('optimiz')) return PlayCircle;
    return History;
  }

  if (isInitializing) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
        <h2 className="text-xl font-semibold">Loading Dashboard</h2>
        <p className="text-muted-foreground mt-2">Syncing with active session data...</p>
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
  
  if (dashboardError) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] text-center">
        <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold text-destructive">Failed to Load Dashboard Data</h2>
        <p className="text-muted-foreground mt-2">{dashboardError.message}</p>
        <Button onClick={() => window.location.reload()} variant="outline" className="mt-4">Retry</Button>
      </div>
    )
  }

  if (noActiveSession) {
    return (
        <div className="flex items-center justify-center h-[calc(100vh-200px)]">
          <Card className="w-full max-w-lg text-center p-8">
            <CardHeader>
              <CardTitle>No Active Session</CardTitle>
              <CardDescription>Please create or select an academic session to view the dashboard.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={() => setCurrentPage('session-setup')}>Go to Session Setup</Button>
            </CardContent>
          </Card>
        </div>
      );
  }

  if (isDataMissing) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <Card className="w-full max-w-lg text-center p-8">
          <CardHeader>
            <CardTitle>Welcome to the Exam Scheduler</CardTitle>
            <CardDescription>No data found for the active session.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="mb-6 text-muted-foreground">Please upload required data (students, courses, rooms) to begin.</p>
            <Button onClick={() => setCurrentPage('upload')}><Upload className="h-4 w-4 mr-2" />Go to Upload Page</Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  
  return (
    <div className="space-y-6 fade-in">
      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Exams Scheduled</p>
              <p className="text-3xl font-bold text-foreground">{dashboardKpis?.total_exams_scheduled.toLocaleString() ?? 0}</p>
              <p className="text-xs text-muted-foreground mt-1">For active session</p>
            </div>
            <div className="p-3 bg-blue-100 dark:bg-blue-900/50 rounded-full"><Calendar className="h-6 w-6 text-blue-600 dark:text-blue-300" /></div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Unresolved Conflicts</p>
              <div className="flex items-baseline space-x-1">
                <p className="text-3xl font-bold text-foreground">
                    {(dashboardKpis?.unresolved_hard_conflicts ?? 0) + (dashboardKpis?.total_soft_conflicts ?? 0)}
                </p>
              </div>
               <p className="text-xs text-muted-foreground mt-1">
                <span className={(dashboardKpis?.unresolved_hard_conflicts ?? 0) > 0 ? "text-red-500 font-medium" : ""}>
                    {dashboardKpis?.unresolved_hard_conflicts ?? 0} Hard
                </span> 
                {' / '} 
                {dashboardKpis?.total_soft_conflicts ?? 0} Soft
               </p>
            </div>
            <div className={cn("p-3 rounded-full", (dashboardKpis?.unresolved_hard_conflicts ?? 0) > 0 ? "bg-red-100 dark:bg-red-900/50" : "bg-yellow-100 dark:bg-yellow-900/50")}>
              <AlertTriangle className={cn("h-6 w-6", (dashboardKpis?.unresolved_hard_conflicts ?? 0) > 0 ? "text-red-600 dark:text-red-300" : "text-yellow-600 dark:text-yellow-300")} />
            </div>
          </div>
        </Card>
        
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Room Utilization</p>
              <p className="text-3xl font-bold text-foreground">{dashboardKpis?.overall_room_utilization.toFixed(1) ?? 0}%</p>
              <p className="text-xs text-muted-foreground mt-1">Average across timetable</p>
            </div>
            <div className={`p-3 rounded-full ${ (dashboardKpis?.overall_room_utilization ?? 0) > 90 ? 'bg-red-100 dark:bg-red-900/50' : 'bg-green-100 dark:bg-green-900/50'}`}>
                <Server className={`h-6 w-6 ${ (dashboardKpis?.overall_room_utilization ?? 0) > 90 ? 'text-red-600 dark:text-red-300' : 'text-green-600 dark:text-green-300'}`} />
            </div>
          </div>
        </Card>

        <Card className="p-6 cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => setCurrentPage('requests')}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Action Required</p>
              <p className="text-3xl font-bold text-foreground">{reportSummaryCounts?.total ?? pendingItems.length}</p>
              <p className="text-xs text-muted-foreground mt-1">Pending reports & requests</p>
            </div>
            <div className="p-3 bg-purple-100 dark:bg-purple-900/50 rounded-full"><ClipboardList className="h-6 w-6 text-purple-600 dark:text-purple-300" /></div>
          </div>
        </Card>
      </div>

      {/* Dashboard Widgets */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Conflict Hotspots */}
        <Card className="lg:col-span-4 flex flex-col">
          <CardHeader><CardTitle className="flex items-center text-base"><AlertTriangle className="h-4 w-4 mr-2 text-yellow-500" />Conflict Hotspots</CardTitle><CardDescription>Times with highest conflict density</CardDescription></CardHeader>
          <CardContent className="flex-1">
            {conflictHotspots.length > 0 ? (
                <div className="space-y-3">
                {conflictHotspots.slice(0, 5).map((hotspot, index) => (
                    <div key={index} className="flex items-center justify-between p-2.5 bg-muted/40 border rounded-md text-sm">
                    <div className="flex items-center space-x-3">
                        <div className="font-medium">{hotspot.timeslot}</div>
                    </div>
                    <Badge variant={hotspot.conflict_count > 10 ? 'destructive' : 'secondary'}>{hotspot.conflict_count}</Badge>
                    </div>
                ))}
                </div>
            ) : (
                <div className="h-full flex items-center justify-center text-center text-sm text-muted-foreground">
                    No significant conflict hotspots detected.
                </div>
            )}
            {conflictHotspots.length > 0 && (
                <Button variant="link" className="w-full mt-2 h-auto p-0 text-xs" onClick={() => setCurrentPage('timetable')}>View in Timetable</Button>
            )}
          </CardContent>
        </Card>

        {/* Latest Job Run */}
        <Card className="lg:col-span-4 flex flex-col">
          <CardHeader><CardTitle className="flex items-center text-base"><Clock className="h-4 w-4 mr-2 text-blue-500" />Latest Scheduling Job</CardTitle><CardDescription>Most recent generation attempt</CardDescription></CardHeader>
          <CardContent className="flex-1 flex flex-col">
            {latestJob ? (
              <div className="space-y-4 flex-1">
                <div className="flex items-center justify-between p-3 border rounded-md bg-card text-sm">
                  <span className="text-muted-foreground">Status</span>
                  <Badge variant={latestJob.status === 'completed' ? 'default' : latestJob.status === 'failed' ? 'destructive' : 'secondary'} className="capitalize">
                    {latestJob.status}
                  </Badge>
                </div>
                 <div className="flex items-center justify-between p-3 border rounded-md bg-card text-sm">
                  <span className="text-muted-foreground">Run</span>
                  <span className="font-medium">{formatTimeAgo(latestJob.created_at)}</span>
                </div>
                 <div className="flex items-center justify-between p-3 border rounded-md bg-card text-sm">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="font-medium">{latestJob.progress_percentage?.toFixed(0) ?? 'N/A'}%</span>
                </div>
                <div className="mt-auto pt-2">
                    <Button className="w-full" variant="outline" onClick={() => setCurrentPage('scheduling')}>Go to Scheduler History</Button>
                </div>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <p className="text-sm text-muted-foreground mb-4">No timetable jobs found for this session.</p>
                <Button size="sm" onClick={() => setCurrentPage('scheduling')}><PlayCircle className="h-4 w-4 mr-2" /> Run Generator</Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card className="lg:col-span-4 flex flex-col max-h-[400px]">
          <CardHeader className="pb-3"><CardTitle className="flex items-center text-base"><Activity className="h-4 w-4 mr-2 text-green-500" />Recent Activity</CardTitle></CardHeader>
          <CardContent className="flex-1 overflow-hidden pt-0">
            <div className="space-y-4 h-full overflow-y-auto pr-2 pt-1 no-scrollbar">
              {recentActivity.length > 0 ? recentActivity.map((activity) => {
                  const Icon = getActivityIcon(activity.action);
                  return (
                    <div key={activity.id} className="flex items-start space-x-3 text-sm">
                      <div className="p-1.5 rounded-full bg-muted shrink-0 mt-0.5">
                        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0 pb-3 border-b last:border-0 border-border/50">
                        <p className="font-medium text-foreground truncate">{activity.action.replace(/_/g, ' ')}</p>
                        <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground">
                          <span className="truncate max-w-[60%]">{activity.userName}</span>
                          <span className="whitespace-nowrap ml-2">{formatTimeAgo(activity.timestamp)}</span>
                        </div>
                        {activity.entityType && <p className="text-xs mt-0.5 text-muted-foreground/70 capitalize">On: {activity.entityType}</p>}
                      </div>
                    </div>
                  );
                }) : (
                    <div className="h-full flex items-center justify-center text-sm text-muted-foreground">No recent activity recorded.</div>
                )}
            </div>
          </CardContent>
        </Card>

        {/* Pending Approvals (Full Width) */}
        <Card className="lg:col-span-12">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center text-lg"><FileWarning className="h-5 w-5 mr-2 text-orange-500" />Pending Approvals</CardTitle>
                        <CardDescription>Actionable reports and requests awaiting review</CardDescription>
                    </div>
                    {pendingItems.length > 0 && <Button size="sm" variant="ghost" onClick={() => setCurrentPage('requests')}>View All</Button>}
                </div>
            </CardHeader>
            <CardContent>
                {pendingItems.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {pendingItems.slice(0, 6).map((item, index) => (
                            <div key={index} className="flex items-start p-3 border rounded-lg bg-card hover:bg-accent/50 transition-colors">
                                <div className="flex-1 min-w-0 mr-4">
                                    <div className="flex items-center space-x-2 mb-1">
                                        <Badge variant={item.uiType === 'Conflict Report' ? 'destructive' : 'secondary'} className="text-[10px] px-1.5 py-0">{item.uiType}</Badge>
                                        <span className="text-xs text-muted-foreground">{formatTimeAgo(item.submitted_at)}</span>
                                    </div>
                                    
                                    {item.uiType === 'Conflict Report' ? (
                                        // Type assertion needed because we combined generic arrays
                                        <>
                                            <p className="text-sm font-medium truncate">
                                                {(item as AdminConflictReport).exam_details?.course_code} - {(item as AdminConflictReport).student?.last_name}
                                            </p>
                                            <p className="text-xs text-muted-foreground line-clamp-1" title={(item as AdminConflictReport).description}>
                                                {(item as AdminConflictReport).description || 'No description provided.'}
                                            </p>
                                        </>
                                    ) : (
                                        <>
                                            <p className="text-sm font-medium truncate">
                                               {(item as AdminChangeRequest).assignment_details?.course_code} - {(item as AdminChangeRequest).staff?.last_name}
                                            </p>
                                            <p className="text-xs text-muted-foreground line-clamp-1" title={(item as AdminChangeRequest).reason}>
                                                Rsn: {(item as AdminChangeRequest).reason}
                                            </p>
                                        </>
                                    )}
                                </div>
                                <Button variant="outline" size="sm" className="h-8 text-xs shrink-0" onClick={() => setCurrentPage('requests')}>Review</Button>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-6 border-2 border-dashed rounded-lg">
                        <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2 opacity-80" />
                        <p className="font-medium">All Clear!</p>
                        <p className="text-sm text-muted-foreground">There are no pending reports or requests.</p>
                    </div>
                )}
            </CardContent>
        </Card>
      </div>
    </div>
  )
}