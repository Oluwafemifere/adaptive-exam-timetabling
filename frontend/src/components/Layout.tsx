import React, { useState, useEffect } from 'react'
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
  WifiOff,
  Sliders,
  GitCompare,
  BarChart3,
  Zap,
  User,
  Bell,
  History,
  Undo2,
  Redo2,
  ChevronDown,
  LogOut,
  Sun,
  Moon,
  PlayCircle,
  Search,
  Command,
  HelpCircle
} from 'lucide-react'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from './ui/dropdown-menu'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip'
import { GlobalSearch } from './GlobalSearch'
import { KeyboardShortcuts } from './KeyboardShortcuts'
import { useAppStore } from '../store'
import { useAuth } from '../hooks/useAuth'
import { cn } from './ui/utils'

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
    name: 'Scheduling', 
    href: 'scheduling', 
    icon: PlayCircle,
    description: 'Start and monitor scheduling jobs'
  },
  { 
    name: 'Timetable', 
    href: 'timetable', 
    icon: Calendar,
    description: 'View and edit schedule'
  },
  { 
    name: 'Constraints', 
    href: 'constraints', 
    icon: Sliders,
    description: 'Configure rules and weights'
  },
  { 
    name: 'Scenarios', 
    href: 'scenarios', 
    icon: GitCompare,
    description: 'Compare solutions'
  },
  { 
    name: 'Analytics', 
    href: 'analytics', 
    icon: BarChart3,
    description: 'Conflict analysis and visualizations'
  },
  { 
    name: 'Session Setup', 
    href: 'session-setup', 
    icon: Zap,
    description: 'Configure academic session'
  },
  { 
    name: 'User Management', 
    href: 'user-management', 
    icon: User,
    description: 'Manage users and permissions'
  },
]

export function Layout({ children }: LayoutProps) {
  const { 
    currentPage, 
    setCurrentPage, 
    conflicts, 
    systemStatus,
    schedulingStatus,
    notifications,
    user,
    settings,
    updateSettings
  } = useAppStore()
  
  const { logout } = useAuth()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [globalSearchOpen, setGlobalSearchOpen] = useState(false)
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  const activeConflicts = conflicts.filter(c => c.type === 'hard').length
  const isSchedulingActive = schedulingStatus.isRunning
  const unreadNotifications = notifications.filter(n => !n.isRead).length
  
  const toggleTheme = () => {
    updateSettings({ 
      theme: settings.theme === 'light' ? 'dark' : 'light' 
    })
  }

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Global search shortcut (Ctrl/Cmd + K)
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setGlobalSearchOpen(true)
      }
      
      // Keyboard shortcuts help (?)
      if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault()
        setShortcutsOpen(true)
      }
      
      // Quick navigation shortcuts
      if ((e.ctrlKey || e.metaKey) && e.shiftKey) {
        switch (e.key) {
          case 'D':
            e.preventDefault()
            setCurrentPage('dashboard')
            break
          case 'T':
            e.preventDefault()
            setCurrentPage('timetable')
            break
          case 'S':
            e.preventDefault()
            setCurrentPage('scheduling')
            break
          case 'C':
            e.preventDefault()
            setCurrentPage('constraints')
            break
          case 'A':
            e.preventDefault()
            setCurrentPage('analytics')
            break
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [setCurrentPage])

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background text-foreground flex">
        {/* Sidebar */}
        <div className="w-64 bg-card shadow-sm border-r border-border flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-border">
            <h1 className="text-xl font-semibold text-foreground">
              Adaptive Exam Timetabler
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Fall 2025
            </p>
          </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = currentPage === item.href
            
            return (
              <Tooltip key={item.name}>
                <TooltipTrigger asChild>
                  <Button
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
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p>{item.description}</p>
                </TooltipContent>
              </Tooltip>
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
            
            {systemStatus.dataSyncProgress > 0 && systemStatus.dataSyncProgress < 100 && (
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

            {/* Top Header Controls */}
            <div className="flex items-center space-x-4">
              {/* Global Search */}
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setGlobalSearchOpen(true)}
                className="flex items-center gap-2 min-w-48"
              >
                <Search className="h-4 w-4" />
                <span className="text-muted-foreground">Search...</span>
                <div className="ml-auto flex items-center gap-1">
                  <kbd className="pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
                    <span className="text-xs">{navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}</span>K
                  </kbd>
                </div>
              </Button>

              {/* History */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => setCurrentPage('history')}
                  >
                    <History className="h-4 w-4 mr-2" />
                    History
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>View activity history</p>
                </TooltipContent>
              </Tooltip>

              {/* Notifications */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-8 w-8 p-0 relative"
                    onClick={() => setCurrentPage('notifications')}
                  >
                    <Bell className="h-4 w-4" />
                    {unreadNotifications > 0 && (
                      <Badge variant="destructive" className="absolute -top-1 -right-1 h-4 w-4 p-0 text-xs">
                        {unreadNotifications}
                      </Badge>
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{unreadNotifications > 0 ? `${unreadNotifications} unread notifications` : 'Notifications'}</p>
                </TooltipContent>
              </Tooltip>

              {/* Theme Toggle */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-8 w-8 p-0"
                    onClick={toggleTheme}
                  >
                    {settings.theme === 'light' ? (
                      <Moon className="h-4 w-4" />
                    ) : (
                      <Sun className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Switch to {settings.theme === 'light' ? 'dark' : 'light'} mode</p>
                </TooltipContent>
              </Tooltip>

              {/* Help / Keyboard Shortcuts */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-8 w-8 p-0"
                    onClick={() => setShortcutsOpen(true)}
                  >
                    <HelpCircle className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Keyboard shortcuts (?)</p>
                </TooltipContent>
              </Tooltip>

              {/* User Profile */}
              <DropdownMenu open={userMenuOpen} onOpenChange={setUserMenuOpen}>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="flex items-center space-x-2 h-auto px-3 py-2">
                    <div className="text-right">
                      <div className="text-sm font-medium">{user?.name || 'Admin User'}</div>
                      <div className="text-xs text-muted-foreground">{user?.email || 'admin@university.edu'}</div>
                    </div>
                    <ChevronDown className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem onClick={() => setCurrentPage('dashboard')}>
                    <LayoutDashboard className="h-4 w-4 mr-2" />
                    Dashboard
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setCurrentPage('notifications')}>
                    <Bell className="h-4 w-4 mr-2" />
                    Notifications
                    {unreadNotifications > 0 && (
                      <Badge variant="secondary" className="ml-auto h-5 w-5 p-0 text-xs">
                        {unreadNotifications}
                      </Badge>
                    )}
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setCurrentPage('history')}>
                    <History className="h-4 w-4 mr-2" />
                    Activity History
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={toggleTheme}>
                    {settings.theme === 'light' ? (
                      <Moon className="h-4 w-4 mr-2" />
                    ) : (
                      <Sun className="h-4 w-4 mr-2" />
                    )}
                    {settings.theme === 'light' ? 'Dark Mode' : 'Light Mode'}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={logout} 
                    className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950 focus:text-red-700 focus:bg-red-50 dark:focus:bg-red-950"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
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

        {/* Global Search Modal */}
        <GlobalSearch
          isOpen={globalSearchOpen}
          onClose={() => setGlobalSearchOpen(false)}
          onNavigate={(page, itemId) => {
            setCurrentPage(page)
            setGlobalSearchOpen(false)
          }}
        />
        
        {/* Keyboard Shortcuts Modal */}
        <KeyboardShortcuts
          isOpen={shortcutsOpen}
          onClose={() => setShortcutsOpen(false)}
        />
      </div>
    </TooltipProvider>
  )
}