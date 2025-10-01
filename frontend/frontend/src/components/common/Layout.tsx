import React from 'react'
import { 
  LayoutDashboard, 
  Upload, 
  Calendar, 
  Settings, 
  FileText,
  Clock,
  Activity,
  AlertTriangle,
  CheckCircle,
  WifiOff
} from 'lucide-react'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { useAppStore } from '../../store'
import { cn } from '../ui/utils'

interface LayoutProps {
  children: React.ReactNode
}

const navigation = [
  { 
    name: 'Dashboard', 
    href: 'dashboard', 
    icon: LayoutDashboard,
    description: 'Overview and KPIs'
  },
  { 
    name: 'Upload', 
    href: 'upload', 
    icon: Upload,
    description: 'Import data files'
  },
  { 
    name: 'Scheduling', 
    href: 'scheduling', 
    icon: Clock,
    description: 'Generate timetables'
  },
  { 
    name: 'Timetable', 
    href: 'timetable', 
    icon: Calendar,
    description: 'View and edit schedule'
  },
  { 
    name: 'Reports', 
    href: 'reports', 
    icon: FileText,
    description: 'Generate reports'
  },
  { 
    name: 'Settings', 
    href: 'settings', 
    icon: Settings,
    description: 'System configuration'
  },
]

export function Layout({ children }: LayoutProps) {
  const { 
    currentPage, 
    setCurrentPage, 
    conflicts, 
    systemStatus,
    schedulingStatus 
  } = useAppStore()

  const activeConflicts = conflicts.filter(c => c.type === 'hard').length
  const isSchedulingActive = schedulingStatus.isRunning

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      {/* Sidebar */}
      <div className="w-64 bg-card shadow-sm border-r border-border flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-border">
          <h1 className="text-xl font-semibold text-foreground">
            Exam Timetabling
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Adaptive Scheduling System
          </p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = currentPage === item.href
            
            return (
              <Button
                key={item.name}
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start text-left h-auto p-3",
                  isActive && "bg-primary/10 text-primary"
                )}
                onClick={() => setCurrentPage(item.href)}
              >
                <Icon className="h-4 w-4 mr-3 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium">{item.name}</div>
                  <div className="text-xs text-muted-foreground truncate">
                    {item.description}
                  </div>
                </div>
                {item.href === 'timetable' && activeConflicts > 0 && (
                  <Badge variant="destructive" className="ml-2">
                    {activeConflicts}
                  </Badge>
                )}
                {item.href === 'scheduling' && isSchedulingActive && (
                  <div className="ml-2 w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                )}
              </Button>
            )
          })}
        </nav>

        {/* System Status Footer */}
        <div className="p-4 border-t border-border">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Constraint Engine</span>
              <div className="flex items-center">
                {systemStatus.constraintEngine === 'active' ? (
                  <CheckCircle className="h-3 w-3 text-green-500 mr-1" />
                ) : systemStatus.constraintEngine === 'error' ? (
                  <AlertTriangle className="h-3 w-3 text-red-500 mr-1" />
                ) : (
                  <WifiOff className="h-3 w-3 text-gray-400 mr-1" />
                )}
                <span className={cn(
                  "text-xs capitalize",
                  systemStatus.constraintEngine === 'active' && "text-green-600",
                  systemStatus.constraintEngine === 'error' && "text-red-600",
                  systemStatus.constraintEngine === 'idle' && "text-muted-foreground"
                )}>
                  {systemStatus.constraintEngine}
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Auto Resolution</span>
              <Badge variant={systemStatus.autoResolution ? "default" : "secondary"} className="text-xs">
                {systemStatus.autoResolution ? "On" : "Off"}
              </Badge>
            </div>
            
            {systemStatus.dataSyncProgress > 0 && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Data Sync</span>
                  <span>{Math.round(systemStatus.dataSyncProgress)}%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-1">
                  <div 
                    className="bg-primary h-1 rounded-full transition-all duration-300" 
                    style={{ width: `${systemStatus.dataSyncProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="bg-card border-b border-border px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-foreground capitalize">
                {currentPage.replace('-', ' ')}
              </h2>
              <p className="text-sm text-muted-foreground">
                {navigation.find(item => item.href === currentPage)?.description}
              </p>
            </div>

            {/* Real-time Status Indicators */}
            <div className="flex items-center space-x-4">
              {isSchedulingActive && (
                <div className="flex items-center text-sm text-green-600">
                  <Activity className="h-4 w-4 mr-2 animate-pulse" />
                  Scheduling in progress...
                </div>
              )}
              
              {activeConflicts > 0 && (
                <Badge variant="destructive" className="flex items-center">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  {activeConflicts} Conflicts
                </Badge>
              )}

              <div className="text-sm text-muted-foreground">
                Last updated: {new Date().toLocaleTimeString()}
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto bg-background">
          <div className="p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}