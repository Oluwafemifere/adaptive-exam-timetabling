import React, { useEffect, useState } from 'react';
import { 
  Calendar, 
  AlertTriangle, 
  CheckCircle, 
  Building2, 
  Users, 
  Clock,
  Upload,
  FileDown,
  Settings,
  PlayCircle,
  Loader2,
  TrendingUp,
  TrendingDown,
  Activity,
  MapPin,
  UserX,
  Bell,
  History
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { cn } from '../components/ui/utils'
import { useAppStore } from '../store'
import { useKPIData } from '../hooks/useApi'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ElementType
  status?: 'good' | 'warning' | 'error'
  className?: string
}

function KPICard({ title, value, subtitle, icon: Icon, status, className }: KPICardProps) {
  return (
    <Card className={cn("h-32", className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-2xl font-semibold">{value}</p>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <div className={cn(
            "p-3 rounded-full",
            status === 'good' && "bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-300",
            status === 'warning' && "bg-amber-100 text-amber-600 dark:bg-amber-900/50 dark:text-amber-300", 
            status === 'error' && "bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-300",
            !status && "bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-300"
          )}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function Dashboard() {
  const { setCurrentPage, initializeApp, activeSessionId, exams, conflicts } = useAppStore()
  const { data: kpiData, isLoading, error } = useKPIData()
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

  const isDataMissing = !isLoading && (!kpiData || kpiData.total_exams === 0);

  // Mock data for new dashboard features
  const mockData = {
    totalExamsScheduled: exams?.length || 142,
    unresolvedHardConflicts: conflicts?.filter(c => c.type === 'hard').length || 0,
    totalSoftConflicts: conflicts?.filter(c => c.type === 'soft').length || 12,
    roomUtilization: 78.5,
    
    conflictHotspots: [
      { day: 'Mon', time: '9:00', conflicts: 5, severity: 'high' },
      { day: 'Tue', time: '14:00', conflicts: 3, severity: 'medium' },
      { day: 'Wed', time: '9:00', conflicts: 7, severity: 'high' },
      { day: 'Thu', time: '11:00', conflicts: 2, severity: 'low' },
      { day: 'Fri', time: '16:00', conflicts: 4, severity: 'medium' },
    ],
    
    bottlenecks: [
      { type: 'exam', name: 'CS301 - Database Systems', issues: 8, reason: 'Room capacity exceeded' },
      { type: 'room', name: 'Hall A - Main Building', issues: 6, reason: 'Over-allocated' },
      { type: 'exam', name: 'MATH201 - Calculus II', issues: 5, reason: 'Student conflicts' },
      { type: 'room', name: 'Lab B - CS Building', issues: 4, reason: 'Equipment constraints' },
      { type: 'exam', name: 'PHY101 - Physics I', issues: 3, reason: 'Invigilator unavailable' },
    ],
    
    recentActivity: [
      { id: 1, action: 'Manually moved exam CS101 to Room B102', user: 'Jane Doe', time: '2 mins ago', type: 'edit' },
      { id: 2, action: 'Solver generated new scenario "Balanced Load"', user: 'System', time: '15 mins ago', type: 'system' },
      { id: 3, action: 'Locked exam MATH301 in preferred slot', user: 'John Smith', time: '1 hour ago', type: 'constraint' },
      { id: 4, action: 'Uploaded new room capacity data', user: 'Alice Brown', time: '2 hours ago', type: 'upload' },
      { id: 5, action: 'Started partial re-optimization for Computer Science', user: 'Mike Wilson', time: '3 hours ago', type: 'optimization' },
    ]
  };

  const quickActions = [
    { title: 'Generate Schedule', description: 'Start automated timetabling', icon: PlayCircle, action: () => setCurrentPage('scheduling'), variant: 'default' as const },
    { title: 'View Conflicts', description: 'Review scheduling conflicts', icon: AlertTriangle, action: () => setCurrentPage('timetable'), variant: 'destructive' as const },
    { title: 'Upload Data', description: 'Import CSV files', icon: Upload, action: () => setCurrentPage('upload'), variant: 'secondary' as const },
    { title: 'Export Results', description: 'Download reports', icon: FileDown, action: () => setCurrentPage('reports'), variant: 'outline' as const },
  ]
  
  if (isInitializing) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-200px)] text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
        <h2 className="text-xl font-semibold">Initializing Application</h2>
        <p className="text-muted-foreground mt-2">Fetching active academic session...</p>
      </div>
    );
  }

  if (isLoading && !isInitializing) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="h-32"><CardContent className="p-6"></CardContent></Card>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <Card className="lg:col-span-8 h-64"></Card>
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
            <CardDescription>
              To begin, you need to upload your academic session data.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="mb-6 text-muted-foreground">
              Please upload the required CSV files for students, courses, registrations, and rooms.
            </p>
            <Button onClick={() => setCurrentPage('upload')}>
              <Upload className="h-4 w-4 mr-2" />
              Go to Upload Page
            </Button>
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
              <p className="text-3xl font-bold text-foreground">{mockData.totalExamsScheduled}</p>
              <p className="text-xs text-muted-foreground flex items-center mt-1">
                <TrendingUp className="h-3 w-3 mr-1 text-green-500" />
                +12 from last week
              </p>
            </div>
            <div className="p-3 bg-blue-100 dark:bg-blue-900/50 rounded-full">
              <Calendar className="h-6 w-6 text-blue-600 dark:text-blue-300" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Unresolved Hard Conflicts</p>
              <p className="text-3xl font-bold text-foreground">{mockData.unresolvedHardConflicts}</p>
              <Badge variant={mockData.unresolvedHardConflicts === 0 ? "default" : "destructive"} className="mt-1">
                {mockData.unresolvedHardConflicts === 0 ? "All Clear" : "Needs Attention"}
              </Badge>
            </div>
            <div className={cn(
              "p-3 rounded-full",
              mockData.unresolvedHardConflicts === 0 
                ? "bg-green-100 dark:bg-green-900/50" 
                : "bg-red-100 dark:bg-red-900/50"
            )}>
              <AlertTriangle className={cn(
                "h-6 w-6",
                mockData.unresolvedHardConflicts === 0 
                  ? "text-green-600 dark:text-green-300" 
                  : "text-red-600 dark:text-red-300"
              )} />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Soft Conflicts</p>
              <p className="text-3xl font-bold text-foreground">{mockData.totalSoftConflicts}</p>
              <p className="text-xs text-muted-foreground flex items-center mt-1">
                <TrendingDown className="h-3 w-3 mr-1 text-red-500" />
                -3 from yesterday
              </p>
            </div>
            <div className="p-3 bg-yellow-100 dark:bg-yellow-900/50 rounded-full">
              <AlertTriangle className="h-6 w-6 text-yellow-600 dark:text-yellow-300" />
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Overall Room Utilization</p>
              <p className="text-3xl font-bold text-foreground">{mockData.roomUtilization}%</p>
              <p className="text-xs text-muted-foreground">Across all venues</p>
            </div>
            <div className="p-3 bg-purple-100 dark:bg-purple-900/50 rounded-full">
              <Building2 className="h-6 w-6 text-purple-600 dark:text-purple-300" />
            </div>
          </div>
        </Card>
      </div>

      {/* Dashboard Widgets */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Conflict Hotspot Widget */}
        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle className="flex items-center">
              <AlertTriangle className="h-5 w-5 mr-2" />
              Conflict Hotspots
            </CardTitle>
            <CardDescription>
              Time slots with the highest conflict density
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockData.conflictHotspots.map((hotspot, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="text-sm font-medium">
                      {hotspot.day} {hotspot.time}
                    </div>
                    <Badge variant={
                      hotspot.severity === 'high' ? 'destructive' : 
                      hotspot.severity === 'medium' ? 'secondary' : 'outline'
                    }>
                      {hotspot.conflicts} conflicts
                    </Badge>
                  </div>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setCurrentPage('timetable')}
                  >
                    View
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Bottleneck List */}
        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle className="flex items-center">
              <UserX className="h-5 w-5 mr-2" />
              Top Bottlenecks
            </CardTitle>
            <CardDescription>
              Items causing the most scheduling issues
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockData.bottlenecks.map((bottleneck, index) => (
                <div key={index} className="flex items-start space-x-3 p-3 bg-muted/50 rounded-lg">
                  <div className={cn(
                    "p-1 rounded-full mt-0.5",
                    bottleneck.type === 'exam' ? 'bg-blue-100 dark:bg-blue-900/50' : 'bg-green-100 dark:bg-green-900/50'
                  )}>
                    {bottleneck.type === 'exam' ? (
                      <Calendar className="h-3 w-3 text-blue-600 dark:text-blue-300" />
                    ) : (
                      <MapPin className="h-3 w-3 text-green-600 dark:text-green-300" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{bottleneck.name}</p>
                    <p className="text-xs text-muted-foreground">{bottleneck.reason}</p>
                  </div>
                  <Badge variant="destructive">{bottleneck.issues}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity Feed */}
        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="h-5 w-5 mr-2" />
              Recent Activity
            </CardTitle>
            <CardDescription>
              Latest actions and system events
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockData.recentActivity.map((activity) => (
                <div key={activity.id} className="flex items-start space-x-3 p-3 bg-muted/50 rounded-lg">
                  <div className={cn(
                    "p-1 rounded-full mt-0.5",
                    activity.type === 'edit' && 'bg-blue-100 dark:bg-blue-900/50',
                    activity.type === 'system' && 'bg-green-100 dark:bg-green-900/50',
                    activity.type === 'constraint' && 'bg-yellow-100 dark:bg-yellow-900/50',
                    activity.type === 'upload' && 'bg-purple-100 dark:bg-purple-900/50',
                    activity.type === 'optimization' && 'bg-red-100 dark:bg-red-900/50'
                  )}>
                    {activity.type === 'edit' && <Settings className="h-3 w-3 text-blue-600 dark:text-blue-300" />}
                    {activity.type === 'system' && <CheckCircle className="h-3 w-3 text-green-600 dark:text-green-300" />}
                    {activity.type === 'constraint' && <AlertTriangle className="h-3 w-3 text-yellow-600 dark:text-yellow-300" />}
                    {activity.type === 'upload' && <Upload className="h-3 w-3 text-purple-600 dark:text-purple-300" />}
                    {activity.type === 'optimization' && <PlayCircle className="h-3 w-3 text-red-600 dark:text-red-300" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{activity.action}</p>
                    <div className="flex items-center space-x-2 mt-1">
                      <p className="text-xs text-muted-foreground">{activity.user}</p>
                      <span className="text-xs text-muted-foreground">•</span>
                      <p className="text-xs text-muted-foreground">{activity.time}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}