import React, { useState, useEffect } from 'react'
import { 
  Calendar, 
  Filter, 
  Download, 
  RefreshCw,
  Eye,
  EyeOff,
  Settings
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Switch } from '../components/ui/switch'
import { Label } from '../components/ui/label'
import { TimetableCalendar } from '../components/scheduling/TimetableCalendar'
import { ConflictResolutionPanel } from '../components/scheduling/ConflictResolutionPanel'
import { useAppStore } from '../store'
import { useTimetable, useConflicts, useUpdateExamSlot } from '../hooks/useApi'
import { cn } from '../components/ui/utils'

interface FilterState {
  department: string
  instructor: string
  room: string
  conflictsOnly: boolean
}

// Generate date range for the next 4 weeks (example)
const generateDateRange = () => {
  const dates = []
  const start = new Date()
  start.setDate(start.getDate() + 1) // Start from tomorrow
  
  for (let i = 0; i < 28; i++) {
    const date = new Date(start)
    date.setDate(start.getDate() + i)
    // Only include weekdays
    if (date.getDay() !== 0 && date.getDay() !== 6) {
      dates.push(date.toISOString().split('T')[0])
    }
  }
  return dates
}

const TIME_SLOTS = ['09:00', '12:00', '15:00', '18:00']

export function Timetable() {
  const { exams, conflicts } = useAppStore()
  const { data: timetableData, isLoading: isLoadingTimetable, refetch } = useTimetable()
  const { data: conflictsData, isLoading: isLoadingConflicts } = useConflicts()
  const updateExamSlot = useUpdateExamSlot()

  const [filters, setFilters] = useState<FilterState>({
    department: 'all',
    instructor: 'all',
    room: 'all',
    conflictsOnly: false
  })
  
  const [showConflictPanel, setShowConflictPanel] = useState(true)
  const [viewMode, setViewMode] = useState<'week' | 'month'>('week')
  const [dateRange] = useState(generateDateRange())

  // Use API data if available, otherwise fall back to store data
  const currentExams = timetableData || exams
  const currentConflicts = conflictsData || conflicts

  // Filter exams based on current filters
  const filteredExams = currentExams.filter(exam => {
    if (filters.department !== 'all' && !exam.courseCode.startsWith(filters.department)) {
      return false
    }
    if (filters.instructor !== 'all' && exam.instructor !== filters.instructor) {
      return false
    }
    if (filters.room !== 'all' && exam.room !== filters.room) {
      return false
    }
    if (filters.conflictsOnly) {
      const hasConflict = currentConflicts.some(conflict => 
        conflict.examIds.includes(exam.id)
      )
      if (!hasConflict) return false
    }
    return true
  })

  // Get unique values for filter dropdowns
  const departments = [...new Set(currentExams.map(exam => exam.courseCode.substring(0, 4)))]
  const instructors = [...new Set(currentExams.map(exam => exam.instructor))]
  const rooms = [...new Set(currentExams.map(exam => exam.room))]

  const handleExamMove = async (examId: string, newDate: string, newTimeSlot: string) => {
    try {
      await updateExamSlot.mutateAsync({
        examId,
        newSlot: { date: newDate, timeSlot: newTimeSlot }
      })
      refetch() // Refresh the timetable data
    } catch (error) {
      console.error('Failed to move exam:', error)
    }
  }

  const handleAutoResolveAll = () => {
    // This would trigger auto-resolution of all resolvable conflicts
    console.log('Auto-resolving all conflicts...')
  }

  const handleExportTimetable = () => {
    // Mock export functionality
    const data = {
      exams: filteredExams,
      conflicts: currentConflicts,
      exported: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `timetable-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoadingTimetable || isLoadingConflicts) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-lg font-medium">Loading Timetable...</p>
        </div>
      </div>
    )
  }

  const hardConflicts = currentConflicts.filter(c => c.type === 'hard').length
  const softConflicts = currentConflicts.filter(c => c.type === 'soft').length

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center">
              <Calendar className="h-5 w-5 mr-2" />
              Exam Timetable
            </CardTitle>
            <div className="flex items-center space-x-2">
              <Badge variant={hardConflicts > 0 ? "destructive" : "default"}>
                {hardConflicts} Hard Conflicts
              </Badge>
              <Badge variant={softConflicts > 0 ? "secondary" : "default"}>
                {softConflicts} Soft Conflicts
              </Badge>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="pt-0">
          <div className="flex flex-wrap items-center gap-4">
            {/* Filters */}
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Filter className="h-4 w-4 text-gray-500" />
                <Label className="text-sm font-medium">Filters:</Label>
              </div>
              
              <Select 
                value={filters.department} 
                onValueChange={(value) => setFilters(prev => ({ ...prev, department: value }))}
              >
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Department" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Departments</SelectItem>
                  {departments.map(dept => (
                    <SelectItem key={dept} value={dept}>{dept}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select 
                value={filters.instructor} 
                onValueChange={(value) => setFilters(prev => ({ ...prev, instructor: value }))}
              >
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Instructor" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Instructors</SelectItem>
                  {instructors.map(instructor => (
                    <SelectItem key={instructor} value={instructor}>{instructor}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select 
                value={filters.room} 
                onValueChange={(value) => setFilters(prev => ({ ...prev, room: value }))}
              >
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Room" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Rooms</SelectItem>
                  {rooms.map(room => (
                    <SelectItem key={room} value={room}>{room}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* View Options */}
            <div className="flex items-center space-x-4 ml-auto">
              <div className="flex items-center space-x-2">
                <Switch
                  id="conflicts-only"
                  checked={filters.conflictsOnly}
                  onCheckedChange={(checked) => setFilters(prev => ({ ...prev, conflictsOnly: checked }))}
                />
                <Label htmlFor="conflicts-only" className="text-sm">Conflicts Only</Label>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowConflictPanel(!showConflictPanel)}
              >
                {showConflictPanel ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
                {showConflictPanel ? 'Hide' : 'Show'} Conflicts
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={handleExportTimetable}
              >
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Timetable View */}
      <div className="flex gap-6">
        {/* Timetable Calendar */}
        <div className="flex-1">
          <Card className="overflow-hidden">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Calendar View</h3>
                <div className="flex items-center space-x-2 text-sm text-gray-500">
                  <span>{filteredExams.length} exams scheduled</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => refetch()}
                    disabled={isLoadingTimetable}
                  >
                    <RefreshCw className={cn("h-4 w-4", isLoadingTimetable && "animate-spin")} />
                  </Button>
                </div>
              </div>
            </CardHeader>
            
            <CardContent className="p-0">
              <TimetableCalendar
                exams={filteredExams}
                onExamMove={handleExamMove}
                conflicts={currentConflicts}
                dateRange={dateRange.slice(0, viewMode === 'week' ? 5 : 20)}
                timeSlots={TIME_SLOTS}
              />
            </CardContent>
          </Card>
        </div>

        {/* Conflict Resolution Panel */}
        {showConflictPanel && (
          <ConflictResolutionPanel
            conflicts={currentConflicts}
            onAutoResolveAll={handleAutoResolveAll}
            className="flex-shrink-0"
          />
        )}
      </div>

      {/* Instructions */}
      <Card>
        <CardContent className="pt-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">How to use the Timetable:</h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• <strong>Drag & Drop:</strong> Click and drag exam blocks to move them to different time slots</li>
              <li>• <strong>Conflicts:</strong> Red borders indicate hard conflicts, yellow borders indicate soft conflicts</li>
              <li>• <strong>Stacking:</strong> Multiple exams in the same time slot will stack vertically</li>
              <li>• <strong>Capacity:</strong> Color-coded capacity bars show room utilization</li>
              <li>• <strong>Auto-resolve:</strong> Use the conflict panel to automatically fix resolvable conflicts</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}