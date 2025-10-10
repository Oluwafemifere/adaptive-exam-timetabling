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
import { TopBottleneck } from '../store/types'; // Import the correct type

// --- START OF FIX ---
// The local 'BottleneckItem' interface was incorrect and has been removed.
// The component now relies on the 'TopBottleneck' type from the store.
// --- END OF FIX ---

export function Analytics() {
  const { setCurrentPage, conflictHotspots, topBottlenecks } = useAppStore(); 
  const [searchTerm, setSearchTerm] = useState('');
  // --- START OF FIX ---
  // The filter state and available filters are updated to match the actual data types ('exam', 'room').
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'exam' | 'room'>('all');
  // --- END OF FIX ---
  const [selectedCell, setSelectedCell] = useState<{ day: string; time: string; hotspot: any } | null>(null);


  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
  const times = ['09:00', '11:00', '14:00', '16:00'];

  const getSeverityColor = (conflictCount: number) => {
    if (conflictCount >= 13) return 'bg-red-600';
    if (conflictCount >= 8) return 'bg-red-400';
    if (conflictCount >= 4) return 'bg-yellow-400';
    if (conflictCount > 0) return 'bg-green-400';
    return 'bg-gray-100 dark:bg-gray-800';
  };

  // --- START OF FIX ---
  // The getTypeIcon function is simplified to handle only the valid types.
  const getTypeIcon = (type: 'exam' | 'room') => {
    switch (type) {
      case 'exam': return Calendar;
      case 'room': return MapPin;
    }
  };
  // --- END OF FIX ---

  const filteredBottlenecks: TopBottleneck[] = (topBottlenecks || []).filter(item => {
    const matchesSearch = item.item.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = selectedFilter === 'all' || item.type === selectedFilter;
    return matchesSearch && matchesFilter;
  });

  const totalConflicts = (conflictHotspots || []).reduce((sum, item) => sum + item.conflict_count, 0);
  const criticalSlots = (conflictHotspots || []).filter(item => item.conflict_count >= 13).length;
  const peakConflictTime = (conflictHotspots || []).reduce((max, item) => 
    item.conflict_count > (max?.conflict_count || 0) ? item : max,
    null as any
  );
  
  if (conflictHotspots.length === 0 && topBottlenecks.length === 0) {
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
                <p className="text-lg font-semibold">{peakConflictTime?.timeslot || 'N/A'}</p>
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
                <p className="text-lg font-semibold">{(totalConflicts / (conflictHotspots.length || 1)).toFixed(1)}</p>
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
                      const hotspot = conflictHotspots.find(h => h.timeslot.includes(day) && h.timeslot.includes(time));
                      const conflictCount = hotspot?.conflict_count || 0;
                      return (
                        <div
                          key={`${day}-${time}`}
                          className={cn(
                            "p-3 text-center border-l cursor-pointer hover:opacity-80 transition-opacity",
                            getSeverityColor(conflictCount)
                          )}
                          onClick={() => hotspot && setSelectedCell({ day, time, hotspot })}
                        >
                          <div className={cn("font-medium", conflictCount > 0 ? "text-white" : "text-muted-foreground")}>
                            {conflictCount}
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
                      {selectedCell.hotspot.timeslot} - Conflict Details
                    </h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Total Conflicts:</span>
                        <span className="ml-2 font-medium">{selectedCell.hotspot.conflict_count}</span>
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
                  placeholder="Search by item name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              <div className="flex space-x-2">
                {/* --- START OF FIX --- */}
                {/* The filter array is corrected to remove the invalid 'staff' option. */}
                {(['all', 'exam', 'room'] as const).map(filter => (
                // --- END OF FIX ---
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
              {filteredBottlenecks.map((item, index) => {
                const Icon = getTypeIcon(item.type);
                return (
                  <Card key={index} className="p-3">
                    <div className="flex items-start space-x-3">
                      {/* --- START OF FIX --- */}
                      {/* The conditional classes for 'staff' are removed, resolving the TS error. */}
                      <div className={cn(
                        "p-1 rounded-full mt-0.5",
                        item.type === 'exam' && 'bg-blue-100 dark:bg-blue-900/50',
                        item.type === 'room' && 'bg-green-100 dark:bg-green-900/50',
                      )}>
                        <Icon className={cn(
                          "h-3 w-3",
                          item.type === 'exam' && 'text-blue-600 dark:text-blue-300',
                          item.type === 'room' && 'text-green-600 dark:text-green-300',
                        )} />
                      </div>
                      {/* --- END OF FIX --- */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className="text-sm font-medium truncate">{item.item}</h4>
                          <Badge variant="destructive" className="text-xs">
                            {item.issue_count}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground mb-2">
                          {item.reason}
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