// src/pages/Dashboard.tsx
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
  Loader2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
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
  const { setCurrentPage, initializeApp, activeSessionId } = useAppStore()
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <KPICard title="Total Exams" value={kpiData?.total_exams || 0} subtitle="Across all courses" icon={Calendar} status="good" />
        <KPICard title="Failed Jobs" value={kpiData?.scheduling_status?.failed_jobs || 0} subtitle="Requiring attention" icon={AlertTriangle} status={(kpiData?.scheduling_status?.failed_jobs || 0) === 0 ? "good" : "error"} />
        <KPICard title="Courses" value={kpiData?.total_courses || 0} subtitle="Included in this session" icon={CheckCircle} />
        <KPICard title="Rooms Used" value={kpiData?.total_rooms_used || 0} subtitle="Across all venues" icon={Building2} />
        <KPICard title="Total Students" value={(kpiData?.total_students_registered || 0).toLocaleString()} subtitle="Total enrollment" icon={Users} />
        <KPICard title="Running Jobs" value={kpiData?.scheduling_status?.running_jobs || 0} subtitle="Currently processing" icon={Clock} status={(kpiData?.scheduling_status?.running_jobs || 0) > 0 ? "warning" : "good"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <Card className="lg:col-span-8">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="h-5 w-5 mr-2" /> Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {quickActions.map((action, index) => {
                const Icon = action.icon;
                return (
                  <Button 
                    key={index} 
                    variant={action.variant} 
                    className="h-auto p-4 flex flex-col items-start text-left space-y-2" 
                    onClick={action.action}
                  >
                    <div className="flex items-center w-full">
                      <Icon className="h-5 w-5 mr-2" />
                      <span className="font-medium">{action.title}</span>
                    </div>
                    <span className={cn("text-sm font-normal", action.variant === 'default' ? 'text-primary-foreground/80' : 'text-muted-foreground')}>
                      {action.description}
                    </span>
                  </Button>
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
