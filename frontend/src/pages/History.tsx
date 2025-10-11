// frontend/src/pages/History.tsx
import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Calendar } from '../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { 
  History as HistoryIcon, 
  Search, 
  Filter, 
  Calendar as CalendarIcon,
  User,
  Settings,
  Database,
  Users,
  FileText,
  Activity,
  Download,
  Eye
} from 'lucide-react';
import { useAppStore } from '../store';
import { DateRange } from 'react-day-picker';
// Note: Using native Date formatting instead of date-fns for simplicity

const getEntityIcon = (entityType: string) => {
    switch (entityType) {
      // FIX: Use CalendarIcon for the icon, not the full Calendar component which caused the UI bug.
      case 'exam': return <CalendarIcon className="h-4 w-4 text-blue-500" />;
      case 'constraint': return <Settings className="h-4 w-4 text-purple-500" />;
      case 'user': return <User className="h-4 w-4 text-green-500" />;
      case 'session': return <Database className="h-4 w-4 text-orange-500" />;
      case 'schedule': return <Activity className="h-4 w-4 text-red-500" />;
      case 'system': return <Settings className="h-4 w-4 text-gray-500" />;
      default: return <FileText className="h-4 w-4 text-gray-500" />;
    }
};

const getActionColor = (action: string) => {
    if (action.toLowerCase().includes('create')) return 'bg-green-100 text-green-800';
    if (action.toLowerCase().includes('update') || action.toLowerCase().includes('edit')) return 'bg-blue-100 text-blue-800';
    if (action.toLowerCase().includes('delete') || action.toLowerCase().includes('remove')) return 'bg-red-100 text-red-800';
    if (action.toLowerCase().includes('approve')) return 'bg-green-100 text-green-800';
    if (action.toLowerCase().includes('deny') || action.toLowerCase().includes('reject')) return 'bg-red-100 text-red-800';
    return 'bg-gray-100 text-gray-800';
};

const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    if (diffInMinutes < 10080) return `${Math.floor(diffInMinutes / 1440)}d ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

// PERFORMANCE FIX: Memoize the list item component to prevent re-rendering every
// item when the parent component updates (e.g., when typing in the search filter).
const HistoryItem = React.memo(({ entry }: { entry: any }) => {
  return (
    <div className="flex items-start gap-4 pb-4 border-b last:border-b-0">
      <div className="mt-1 flex-shrink-0">
        {getEntityIcon(entry.entityType)}
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge 
                variant="outline" 
                className={`text-xs ${getActionColor(entry.action)}`}
              >
                {entry.action}
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {entry.entityType}
              </Badge>
            </div>
            
            <p className="text-sm mt-1">
              <span className="font-medium">{entry.userName}</span>
              {' '}performed: {entry.action}
              {entry.entityId && (
                <span className="text-muted-foreground">
                  {' '}(ID: {entry.entityId})
                </span>
              )}
            </p>
            
            {Object.keys(entry.details).length > 0 && (
              <details className="mt-2">
                <summary className="text-sm text-muted-foreground cursor-pointer hover:text-foreground">
                  View details
                </summary>
                <div className="mt-2 p-3 bg-muted rounded-md text-sm overflow-x-auto">
                  <pre className="whitespace-pre-wrap font-mono text-xs min-w-max">
                    {JSON.stringify(entry.details, null, 2)}
                  </pre>
                </div>
              </details>
            )}
            
            {entry.changes && (
              <details className="mt-2">
                <summary className="text-sm text-muted-foreground cursor-pointer hover:text-foreground">
                  View changes
                </summary>
                <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h5 className="text-sm font-medium text-red-600 mb-1">Before</h5>
                    <div className="p-3 bg-red-50 rounded-md text-sm overflow-x-auto">
                      <pre className="whitespace-pre-wrap font-mono text-xs min-w-max">
                        {JSON.stringify(entry.changes.before, null, 2)}
                      </pre>
                    </div>
                  </div>
                  <div>
                    <h5 className="text-sm font-medium text-green-600 mb-1">After</h5>
                    <div className="p-3 bg-green-50 rounded-md text-sm overflow-x-auto">
                      <pre className="whitespace-pre-wrap font-mono text-xs min-w-max">
                        {JSON.stringify(entry.changes.after, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              </details>
            )}
          </div>
          
          <div className="text-right flex-shrink-0">
            <span className="text-sm text-muted-foreground">
              {formatTimestamp(entry.timestamp)}
            </span>
            <p className="text-xs text-muted-foreground mt-1">
              {new Date(entry.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'})}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
});


export function History() {
  const { history } = useAppStore();
  
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEntityType, setSelectedEntityType] = useState<string>('all');
  const [selectedUser, setSelectedUser] = useState<string>('all');
  const [dateRange, setDateRange] = useState<DateRange | undefined>(undefined);
  const [showFilters, setShowFilters] = useState(false);

  // Get unique values for filters
  const entityTypes = useMemo(() => {
    const types = new Set(history.map(entry => entry.entityType));
    return Array.from(types);
  }, [history]);

  const users = useMemo(() => {
    const userSet = new Set(history.map(entry => entry.userName));
    return Array.from(userSet);
  }, [history]);

  // Filter history entries
  const filteredHistory = useMemo(() => {
    return history.filter(entry => {
      // Search term filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        const matchesSearch = 
          entry.action.toLowerCase().includes(searchLower) ||
          entry.userName.toLowerCase().includes(searchLower) ||
          entry.entityType.toLowerCase().includes(searchLower) ||
          JSON.stringify(entry.details).toLowerCase().includes(searchLower);
        
        if (!matchesSearch) return false;
      }

      // Entity type filter
      if (selectedEntityType !== 'all' && entry.entityType !== selectedEntityType) {
        return false;
      }

      // User filter
      if (selectedUser !== 'all' && entry.userName !== selectedUser) {
        return false;
      }

      // Date range filter
      if (dateRange?.from) {
        const entryDate = new Date(entry.timestamp);
        if (dateRange.from && entryDate < dateRange.from) return false;
        
        if (dateRange.to) {
          const toDate = new Date(dateRange.to);
          toDate.setHours(23, 59, 59, 999); // Set to the end of the day to make it inclusive
          if (entryDate > toDate) return false;
        }
      }

      return true;
    });
  }, [history, searchTerm, selectedEntityType, selectedUser, dateRange]);

  const exportHistory = () => {
    const csvContent = [
      ['Timestamp', 'User', 'Action', 'Entity Type', 'Entity ID', 'Details'].join(','),
      ...filteredHistory.map(entry => [
        entry.timestamp,
        entry.userName,
        entry.action,
        entry.entityType,
        entry.entityId || '',
        JSON.stringify(entry.details)
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `history-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Activity History</h2>
          <p className="text-muted-foreground">
            View and track all system activities and changes
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button onClick={exportHistory} variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
          <Button 
            onClick={() => setShowFilters(!showFilters)} 
            variant="outline" 
            size="sm"
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <HistoryIcon className="h-8 w-8 text-blue-600" />
              <div>
                <p className="text-sm text-muted-foreground">Total Activities</p>
                <p className="text-2xl font-semibold">{history.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Users className="h-8 w-8 text-green-600" />
              <div>
                <p className="text-sm text-muted-foreground">Active Users</p>
                <p className="text-2xl font-semibold">{users.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Activity className="h-8 w-8 text-purple-600" />
              <div>
                <p className="text-sm text-muted-foreground">Today's Activities</p>
                <p className="text-2xl font-semibold">
                  {history.filter(entry => {
                    const entryDate = new Date(entry.timestamp);
                    const today = new Date();
                    return entryDate.toDateString() === today.toDateString();
                  }).length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Database className="h-8 w-8 text-orange-600" />
              <div>
                <p className="text-sm text-muted-foreground">Entity Types</p>
                <p className="text-2xl font-semibold">{entityTypes.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Filters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Search</label>
                <div className="relative">
                  <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input
                    placeholder="Search activities..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Entity Type</label>
                <Select value={selectedEntityType} onValueChange={setSelectedEntityType}>
                  <SelectTrigger>
                    <SelectValue placeholder="All types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    {entityTypes.map(type => (
                      <SelectItem key={type} value={type}>
                        {type.charAt(0).toUpperCase() + type.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">User</label>
                <Select value={selectedUser} onValueChange={setSelectedUser}>
                  <SelectTrigger>
                    <SelectValue placeholder="All users" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Users</SelectItem>
                    {users.map(user => (
                      <SelectItem key={user} value={user}>
                        {user}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Date Range</label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="w-full justify-start text-left">
                      <CalendarIcon className="h-4 w-4 mr-2" />
                      {dateRange?.from ? (
                        dateRange.to ? (
                          `${dateRange.from.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${dateRange.to.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
                        ) : (
                          dateRange.from.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                        )
                      ) : (
                        'Pick a date range'
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0 z-50" align="start">
                    <Calendar
                      initialFocus
                      mode="range"
                      defaultMonth={dateRange?.from}
                      selected={dateRange}
                      onSelect={setDateRange}
                      numberOfMonths={2}
                    />
                  </PopoverContent>
                </Popover>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={() => {
                  setSearchTerm('');
                  setSelectedEntityType('all');
                  setSelectedUser('all');
                  setDateRange(undefined);
                }}
                variant="outline"
                size="sm"
              >
                Clear Filters
              </Button>
              <span className="text-sm text-muted-foreground self-center">
                Showing {filteredHistory.length} of {history.length} activities
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* History List */}
      <Card>
        <CardHeader>
          <CardTitle>Activity Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {filteredHistory.length === 0 ? (
            <div className="py-8 text-center">
              <HistoryIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3>No Activities Found</h3>
              <p className="text-muted-foreground">
                {history.length === 0 
                  ? 'No activities have been recorded yet.'
                  : 'No activities match your current filters.'
                }
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredHistory.map((entry) => (
                <HistoryItem key={entry.id} entry={entry} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}