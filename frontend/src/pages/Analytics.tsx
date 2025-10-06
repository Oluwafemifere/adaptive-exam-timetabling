// frontend/src/pages/Analytics.tsx
import React, { useState } from 'react';
import { 
  BarChart3, 
  Search, 
  Filter,
  TrendingUp,
  AlertTriangle,
  Calendar,
  MapPin,
  Users,
  Clock,
  Eye,
  Download,
  PlayCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { cn } from '../components/ui/utils'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '../components/ui/table'
import { useAppStore } from '../store'

interface ConflictData {
  day: string;
  time: string;
  conflicts: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  types: {
    student: number;
    room: number;
    staff: number;
  };
}

interface BottleneckItem {
  id: string;
  type: 'course' | 'room' | 'student';
  name: string;
  identifier: string;
  hardConflicts: number;
  softConflicts: number;
  totalIssues: number;
  details: string[];
}

export function Analytics() {
  const { setCurrentPage, exams } = useAppStore(); // MODIFICATION: Get exams from store
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'course' | 'room' | 'student'>('all');
  const [selectedCell, setSelectedCell] = useState<ConflictData | null>(null);

  // Mock heatmap data - represents conflicts per time slot
  const heatmapData: ConflictData[] = [
    // Monday
    { day: 'Mon', time: '09:00', conflicts: 12, severity: 'high', types: { student: 8, room: 2, staff: 2 } },
    { day: 'Mon', time: '11:00', conflicts: 5, severity: 'medium', types: { student: 3, room: 1, staff: 1 } },
    { day: 'Mon', time: '14:00', conflicts: 8, severity: 'medium', types: { student: 5, room: 2, staff: 1 } },
    { day: 'Mon', time: '16:00', conflicts: 2, severity: 'low', types: { student: 1, room: 1, staff: 0 } },
    
    // Tuesday
    { day: 'Tue', time: '09:00', conflicts: 15, severity: 'critical', types: { student: 10, room: 3, staff: 2 } },
    { day: 'Tue', time: '11:00', conflicts: 7, severity: 'medium', types: { student: 4, room: 2, staff: 1 } },
    { day: 'Tue', time: '14:00', conflicts: 3, severity: 'low', types: { student: 2, room: 1, staff: 0 } },
    { day: 'Tue', time: '16:00', conflicts: 6, severity: 'medium', types: { student: 4, room: 1, staff: 1 } },
    
    // Wednesday
    { day: 'Wed', time: '09:00', conflicts: 9, severity: 'high', types: { student: 6, room: 2, staff: 1 } },
    { day: 'Wed', time: '11:00', conflicts: 4, severity: 'low', types: { student: 3, room: 1, staff: 0 } },
    { day: 'Wed', time: '14:00', conflicts: 11, severity: 'high', types: { student: 7, room: 3, staff: 1 } },
    { day: 'Wed', time: '16:00', conflicts: 1, severity: 'low', types: { student: 1, room: 0, staff: 0 } },
    
    // Thursday
    { day: 'Thu', time: '09:00', conflicts: 6, severity: 'medium', types: { student: 4, room: 1, staff: 1 } },
    { day: 'Thu', time: '11:00', conflicts: 8, severity: 'medium', types: { student: 5, room: 2, staff: 1 } },
    { day: 'Thu', time: '14:00', conflicts: 2, severity: 'low', types: { student: 2, room: 0, staff: 0 } },
    { day: 'Thu', time: '16:00', conflicts: 4, severity: 'low', types: { student: 3, room: 1, staff: 0 } },
    
    // Friday
    { day: 'Fri', time: '09:00', conflicts: 3, severity: 'low', types: { student: 2, room: 1, staff: 0 } },
    { day: 'Fri', time: '11:00', conflicts: 7, severity: 'medium', types: { student: 5, room: 1, staff: 1 } },
    { day: 'Fri', time: '14:00', conflicts: 5, severity: 'medium', types: { student: 3, room: 2, staff: 0 } },
    { day: 'Fri', time: '16:00', conflicts: 9, severity: 'high', types: { student: 6, room: 2, staff: 1 } },
  ];

  // Mock bottleneck data
  const bottleneckData: BottleneckItem[] = [
    {
      id: '1',
      type: 'course',
      name: 'CS301 - Database Systems',
      identifier: 'CS301',
      hardConflicts: 5,
      softConflicts: 8,
      totalIssues: 13,
      details: ['Room capacity exceeded', 'Student scheduling conflicts', 'Invigilator unavailable']
    },
    {
      id: '2',
      type: 'room',
      name: 'Hall A - Main Building',
      identifier: 'HALL-A',
      hardConflicts: 3,
      softConflicts: 6,
      totalIssues: 9,
      details: ['Over-allocated during peak hours', 'Equipment requirements not met']
    },
    {
      id: '3',
      type: 'course',
      name: 'MATH201 - Calculus II',
      identifier: 'MATH201',
      hardConflicts: 4,
      softConflicts: 4,
      totalIssues: 8,
      details: ['Large enrollment vs. available rooms', 'Back-to-back exam conflicts']
    },
    {
      id: '4',
      type: 'student',
      name: 'Group: Computer Science Year 3',
      identifier: 'CS-Y3',
      hardConflicts: 2,
      softConflicts: 5,
      totalIssues: 7,
      details: ['Multiple exams on same day', 'Travel time between venues']
    },
    {
      id: '5',
      type: 'room',
      name: 'Lab B - CS Building',
      identifier: 'LAB-B',
      hardConflicts: 1,
      softConflicts: 5,
      totalIssues: 6,
      details: ['Limited computer workstations', 'Network connectivity issues']
    },
    {
      id: '6',
      type: 'course',
      name: 'PHY101 - Physics I',
      identifier: 'PHY101',
      hardConflicts: 2,
      softConflicts: 3,
      totalIssues: 5,
      details: ['Equipment setup time requirements', 'Special room requirements']
    }
  ];

  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
  const times = ['09:00', '11:00', '14:00', '16:00'];

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-600';
      case 'high': return 'bg-red-400';
      case 'medium': return 'bg-yellow-400';
      case 'low': return 'bg-green-400';
      default: return 'bg-gray-200';
    }
  };

  const getTypeIcon = (type: 'course' | 'room' | 'student') => {
    switch (type) {
      case 'course': return Calendar;
      case 'room': return MapPin;
      case 'student': return Users;
    }
  };

  const filteredBottlenecks = bottleneckData.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.identifier.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = selectedFilter === 'all' || item.type === selectedFilter;
    return matchesSearch && matchesFilter;
  });

  const totalConflicts = heatmapData.reduce((sum, item) => sum + item.conflicts, 0);
  const criticalSlots = heatmapData.filter(item => item.severity === 'critical').length;
  const peakConflictTime = heatmapData.reduce((max, item) => 
    item.conflicts > max.conflicts ? item : max
  );
  
  // --- MODIFICATION START: Add empty state for the whole page ---
  if (heatmapData.length === 0 && bottleneckData.length === 0) {
    return (
       <div className="flex items-center justify-center h-[calc(100vh-200px)]">
        <Card className="w-full max-w-lg text-center p-8">
          <CardHeader>
            <div className="mx-auto bg-primary/10 rounded-full p-4 w-fit">
              <BarChart3 className="h-12 w-12 text-primary" />
            </div>
            <CardTitle className="mt-4">No Data to Analyze</CardTitle>
            <CardDescription>
              Conflict analysis and bottleneck reports will appear here once a timetable has been generated.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="mb-6 text-muted-foreground">
              Generate a schedule to populate this dashboard with analytical data.
            </p>
            <Button onClick={() => setCurrentPage('scheduling')}>
              <PlayCircle className="h-4 w-4 mr-2" />
              Go to Scheduling Page
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }
  // --- MODIFICATION END ---


  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Conflict Analysis & Visualization</h1>
          <p className="text-muted-foreground">Understand scheduling challenges and bottlenecks</p>
        </div>
        <Button>
          <Download className="h-4 w-4 mr-2" />
          Export Analysis
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-full">
                <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Conflicts</p>
                <p className="text-lg font-semibold">{totalConflicts}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-full">
                <Clock className="h-4 w-4 text-red-600 dark:text-red-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Critical Slots</p>
                <p className="text-lg font-semibold">{criticalSlots}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-yellow-100 dark:bg-yellow-900/50 rounded-full">
                <TrendingUp className="h-4 w-4 text-yellow-600 dark:text-yellow-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Peak Conflict</p>
                <p className="text-lg font-semibold">{peakConflictTime.day} {peakConflictTime.time}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/50 rounded-full">
                <BarChart3 className="h-4 w-4 text-blue-600 dark:text-blue-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Avg per Slot</p>
                <p className="text-lg font-semibold">{(totalConflicts / heatmapData.length).toFixed(1)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Conflict Heatmap */}
        <Card className="lg:col-span-8">
          <CardHeader>
            <CardTitle className="flex items-center">
              <BarChart3 className="h-5 w-5 mr-2" />
              Interactive Timetable Heatmap
            </CardTitle>
            <CardDescription>
              Click on any time slot to see detailed conflict information
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Legend */}
              <div className="flex items-center space-x-4 text-sm">
                <span className="text-muted-foreground">Conflict Density:</span>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 bg-green-400 rounded"></div>
                  <span>Low (1-3)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 bg-yellow-400 rounded"></div>
                  <span>Medium (4-7)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 bg-red-400 rounded"></div>
                  <span>High (8-12)</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 bg-red-600 rounded"></div>
                  <span>Critical (13+)</span>
                </div>
              </div>

              {/* Heatmap Grid */}
              <div className="border rounded-lg overflow-hidden">
                <div className="grid grid-cols-6 bg-muted/50">
                  <div className="p-3 font-medium text-center">Time / Day</div>
                  {days.map(day => (
                    <div key={day} className="p-3 font-medium text-center border-l">
                      {day}
                    </div>
                  ))}
                </div>
                {times.map(time => (
                  <div key={time} className="grid grid-cols-6 border-t">
                    <div className="p-3 font-medium text-center bg-muted/30">
                      {time}
                    </div>
                    {days.map(day => {
                      const cellData = heatmapData.find(d => d.day === day && d.time === time);
                      return (
                        <div
                          key={`${day}-${time}`}
                          className={cn(
                            "p-3 text-center border-l cursor-pointer hover:opacity-80 transition-opacity",
                            cellData ? getSeverityColor(cellData.severity) : "bg-gray-100"
                          )}
                          onClick={() => setSelectedCell(cellData || null)}
                        >
                          <div className="text-white font-medium">
                            {cellData?.conflicts || 0}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>

              {/* Selected Cell Details */}
              {selectedCell && (
                <Card className="bg-muted/50">
                  <CardContent className="p-4">
                    <h4 className="font-medium mb-2">
                      {selectedCell.day} {selectedCell.time} - Conflict Details
                    </h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Student Conflicts:</span>
                        <span className="ml-2 font-medium">{selectedCell.types.student}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Room Conflicts:</span>
                        <span className="ml-2 font-medium">{selectedCell.types.room}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Staff Conflicts:</span>
                        <span className="ml-2 font-medium">{selectedCell.types.staff}</span>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t">
                      <Button 
                        size="sm" 
                        onClick={() => setCurrentPage('timetable')}
                      >
                        <Eye className="h-3 w-3 mr-1" />
                        View in Timetable
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Bottleneck Inspector */}
        <Card className="lg:col-span-4">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Users className="h-5 w-5 mr-2" />
              Bottleneck Inspector
            </CardTitle>
            <CardDescription>
              Items causing the most scheduling issues
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Search and Filter */}
            <div className="space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search courses, rooms, students..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="flex space-x-2">
                {(['all', 'course', 'room', 'student'] as const).map(filter => (
                  <Button
                    key={filter}
                    variant={selectedFilter === filter ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedFilter(filter)}
                  >
                    {filter === 'all' ? 'All' : filter.charAt(0).toUpperCase() + filter.slice(1)}
                  </Button>
                ))}
              </div>
            </div>

            {/* Bottleneck List */}
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {filteredBottlenecks.map((item) => {
                const Icon = getTypeIcon(item.type);
                return (
                  <Card key={item.id} className="p-3">
                    <div className="flex items-start space-x-3">
                      <div className={cn(
                        "p-1 rounded-full mt-0.5",
                        item.type === 'course' && 'bg-blue-100 dark:bg-blue-900/50',
                        item.type === 'room' && 'bg-green-100 dark:bg-green-900/50',
                        item.type === 'student' && 'bg-purple-100 dark:bg-purple-900/50'
                      )}>
                        <Icon className={cn(
                          "h-3 w-3",
                          item.type === 'course' && 'text-blue-600 dark:text-blue-300',
                          item.type === 'room' && 'text-green-600 dark:text-green-300',
                          item.type === 'student' && 'text-purple-600 dark:text-purple-300'
                        )} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className="text-sm font-medium truncate">{item.name}</h4>
                          <Badge variant="destructive" className="text-xs">
                            {item.totalIssues}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground mb-2">
                          Hard: {item.hardConflicts} • Soft: {item.softConflicts}
                        </div>
                        <div className="space-y-1">
                          {item.details.slice(0, 2).map((detail, index) => (
                            <div key={index} className="text-xs text-muted-foreground">
                              • {detail}
                            </div>
                          ))}
                          {item.details.length > 2 && (
                            <div className="text-xs text-muted-foreground">
                              +{item.details.length - 2} more issues
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}