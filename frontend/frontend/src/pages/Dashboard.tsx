import React from 'react'
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
  PlayCircle
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Progress } from '../components/ui/progress'
import { useAppStore } from '../store'
import { useKPIData } from '../hooks/useApi'
import { cn } from '../components/ui/utils'

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
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-semibold">{value}</p>
            {subtitle && (
              <p className="text-xs text-gray-500">{subtitle}</p>
            )}
          </div>
          <div className={cn(
            "p-3 rounded-full",
            status === 'good' && "bg-green-100 text-green-600",
            status === 'warning' && "bg-amber-100 text-amber-600", 
            status === 'error' && "bg-red-100 text-red-600",
            !status && "bg-blue-100 text-blue-600"
          )}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface ActivityItem {
  id: string
  type: 'upload' | 'schedule' | 'conflict' | 'export'
  message: string
  timestamp: string
  status: 'success' | 'warning' | 'error'
}

function ActivityFeed() {
  // Mock activity data - would come from API
  const activities: ActivityItem[] = [
    {
      id: '1',
      type: 'schedule',
      message: 'Timetable generation completed successfully',
      timestamp: '2 minutes ago',
      status: 'success'
    },
    {
      id: '2',
      type: 'conflict',
      message: 'Resolved room capacity conflict for MATH101',
      timestamp: '5 minutes ago',
      status: 'warning'
    },
    {
      id: '3',
      type: 'upload',
      message: 'Student registration data uploaded',
      timestamp: '12 minutes ago',
      status: 'success'
    },
    {
      id: '4',
      type: 'export',
      message: 'Exam schedule exported to PDF',
      timestamp: '18 minutes ago',
      status: 'success'
    },
  ]

  const getActivityIcon = (type: string) => {
    const iconProps = { className: "h-4 w-4" }
    
    switch (type) {
      case 'upload':
        return <Upload {...iconProps} />
      case 'schedule':
        return <Calendar {...iconProps} />
      case 'conflict':
        return <AlertTriangle {...iconProps} />
      case 'export':
        return <FileDown {...iconProps} />
      default:
        return <Clock {...iconProps} />
    }
  }

  return (
    <Card className="col-span-4">
      <CardHeader>
        <CardTitle className="flex items-center">
          <Clock className="h-5 w-5 mr-2" />
          Recent Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {activities.map((activity) => (
            <div key={activity.id} className="flex items-start space-x-3">
              <div className={cn(
                "p-2 rounded-full",
                activity.status === 'success' && "bg-green-100 text-green-600",
                activity.status === 'warning' && "bg-amber-100 text-amber-600",
                activity.status === 'error' && "bg-red-100 text-red-600"
              )}>
                {getActivityIcon(activity.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">
                  {activity.message}
                </p>
                <p className="text-xs text-gray-500">
                  {activity.timestamp}
                </p>
              </div>
              <Badge variant={
                activity.status === 'success' ? 'default' :
                activity.status === 'warning' ? 'secondary' : 'destructive'
              }>
                {activity.status}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function Dashboard() {
  const { setCurrentPage, kpiData } = useAppStore()
  const { data: kpiDataFromAPI, isLoading } = useKPIData()

  // Use API data if available, otherwise fall back to store data
  const currentKPIData = kpiDataFromAPI || kpiData

  const quickActions = [
    {
      title: 'Generate Schedule',
      description: 'Start automated timetabling',
      icon: PlayCircle,
      action: () => setCurrentPage('scheduling'),
      variant: 'default' as const,
    },
    {
      title: 'View Conflicts',
      description: 'Review scheduling conflicts',
      icon: AlertTriangle,
      action: () => setCurrentPage('timetable'),
      variant: 'destructive' as const,
    },
    {
      title: 'Upload Data',
      description: 'Import CSV files',
      icon: Upload,
      action: () => setCurrentPage('upload'),
      variant: 'secondary' as const,
    },
    {
      title: 'Export Results',
      description: 'Download reports',
      icon: FileDown,
      action: () => setCurrentPage('reports'),
      variant: 'outline' as const,
    },
  ]

  if (isLoading || !currentKPIData) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="h-32 animate-pulse">
              <CardContent className="p-6">
                <div className="bg-gray-200 h-4 w-24 rounded mb-2"></div>
                <div className="bg-gray-200 h-8 w-16 rounded mb-1"></div>
                <div className="bg-gray-200 h-3 w-20 rounded"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <KPICard
          title="Scheduled Exams"
          value={currentKPIData.scheduledExams}
          subtitle="Total examinations"
          icon={Calendar}
          status="good"
        />
        
        <KPICard
          title="Active Conflicts"
          value={currentKPIData.activeConflicts}
          subtitle="Requiring attention"
          icon={AlertTriangle}
          status={currentKPIData.activeConflicts === 0 ? "good" : "error"}
        />
        
        <KPICard
          title="Constraint Satisfaction"
          value={`${currentKPIData.constraintSatisfactionRate}%`}
          subtitle="System compliance"
          icon={CheckCircle}
          status={currentKPIData.constraintSatisfactionRate > 90 ? "good" : "warning"}
        />
        
        <KPICard
          title="Room Utilization"
          value={`${currentKPIData.roomUtilization}%`}
          subtitle="Facility efficiency"
          icon={Building2}
          status={currentKPIData.roomUtilization > 70 ? "good" : "warning"}
        />
        
        <KPICard
          title="Students Affected"
          value={currentKPIData.studentsAffected.toLocaleString()}
          subtitle="Total enrollment"
          icon={Users}
          status="good"
        />
        
        <KPICard
          title="Processing Time"
          value={`${currentKPIData.processingTime}s`}
          subtitle="Last generation"
          icon={Clock}
          status={currentKPIData.processingTime < 5 ? "good" : "warning"}
        />
      </div>

      {/* Quick Actions and Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Quick Actions */}
        <Card className="lg:col-span-8">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Settings className="h-5 w-5 mr-2" />
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {quickActions.map((action, index) => {
                const Icon = action.icon
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
                    <span className="text-sm text-gray-600 font-normal">
                      {action.description}
                    </span>
                  </Button>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Activity Feed */}
        <ActivityFeed />
      </div>

      {/* System Health Overview */}
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Constraint Engine</span>
                <Badge variant="default">Active</Badge>
              </div>
              <Progress value={95} className="h-2" />
              <p className="text-xs text-gray-500">95% availability this week</p>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Data Quality</span>
                <Badge variant="default">Good</Badge>
              </div>
              <Progress value={88} className="h-2" />
              <p className="text-xs text-gray-500">88% validation success rate</p>
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">Response Time</span>
                <Badge variant="default">Optimal</Badge>
              </div>
              <Progress value={92} className="h-2" />
              <p className="text-xs text-gray-500">92% under 3s response time</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}