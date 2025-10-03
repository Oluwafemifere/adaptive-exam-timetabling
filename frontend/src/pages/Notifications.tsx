// frontend/src/pages/Notifications.tsx
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { 
  Bell, 
  BellOff, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  FileEdit, 
  Settings, 
  Eye,
  Trash2,
  Check
} from 'lucide-react';
import { useAppStore } from '../store';
import { toast } from 'sonner';

export function Notifications() {
  const { 
    notifications, 
    conflictReports, 
    changeRequests,
    markNotificationAsRead,
    clearNotifications,
    updateConflictReportStatus,
    updateChangeRequestStatus,
    addHistoryEntry,
    user
  } = useAppStore();

  const [selectedConflictReport, setSelectedConflictReport] = useState<string | null>(null);
  const [selectedChangeRequest, setSelectedChangeRequest] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState('');

  const unreadCount = notifications.filter(n => !n.isRead).length;
  const actionRequiredCount = notifications.filter(n => n.actionRequired && !n.isRead).length;

  const handleMarkAsRead = (id: string) => {
    markNotificationAsRead(id);
    toast.success('Notification marked as read');
  };

  const handleMarkAllAsRead = () => {
    notifications.forEach(n => {
      if (!n.isRead) {
        markNotificationAsRead(n.id);
      }
    });
    toast.success('All notifications marked as read');
  };

  const handleClearAll = () => {
    clearNotifications();
    toast.success('All notifications cleared');
  };

  const handleResolveConflictReport = (reportId: string, status: 'reviewed' | 'resolved', notes?: string) => {
    updateConflictReportStatus(reportId, status);
    
    addHistoryEntry({
      action: `${status === 'reviewed' ? 'Reviewed' : 'Resolved'} conflict report`,
      entityType: 'exam',
      entityId: reportId,
      userId: user?.id || '',
      userName: user?.name || '',
      details: {
        status,
        notes,
        reportId
      }
    });

    toast.success(`Conflict report ${status}`);
    setSelectedConflictReport(null);
    setReviewNotes('');
  };

  const handleResolveChangeRequest = (requestId: string, status: 'approved' | 'denied', notes?: string) => {
    updateChangeRequestStatus(requestId, status);
    
    addHistoryEntry({
      action: `${status === 'approved' ? 'Approved' : 'Denied'} change request`,
      entityType: 'exam',
      entityId: requestId,
      userId: user?.id || '',
      userName: user?.name || '',
      details: {
        status,
        notes,
        requestId
      }
    });

    toast.success(`Change request ${status}`);
    setSelectedChangeRequest(null);
    setReviewNotes('');
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'conflict_report':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'change_request':
        return <FileEdit className="h-4 w-4 text-blue-500" />;
      case 'job_completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'job_failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'system_alert':
        return <Settings className="h-4 w-4 text-orange-500" />;
      default:
        return <Bell className="h-4 w-4 text-gray-500" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'low': return 'bg-gray-100 text-gray-800 border-gray-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const now = new Date();
    const date = new Date(dateString);
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    return `${Math.floor(diffInMinutes / 1440)}d ago`;
  };

  const sortedNotifications = [...notifications].sort((a, b) => {
    // Unread first, then by priority, then by date
    if (a.isRead !== b.isRead) return a.isRead ? 1 : -1;
    
    const priorityOrder = { urgent: 4, high: 3, medium: 2, low: 1 };
    const aPriority = priorityOrder[a.priority as keyof typeof priorityOrder] || 0;
    const bPriority = priorityOrder[b.priority as keyof typeof priorityOrder] || 0;
    
    if (aPriority !== bPriority) return bPriority - aPriority;
    
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Notifications</h2>
          <p className="text-muted-foreground">
            Manage notifications and action items
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <Button onClick={handleMarkAllAsRead} variant="outline" size="sm">
              <Check className="h-4 w-4 mr-2" />
              Mark All Read
            </Button>
          )}
          <Button onClick={handleClearAll} variant="outline" size="sm">
            <Trash2 className="h-4 w-4 mr-2" />
            Clear All
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Bell className="h-8 w-8 text-blue-600" />
              <div>
                <p className="text-sm text-muted-foreground">Total Notifications</p>
                <p className="text-2xl font-semibold">{notifications.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <BellOff className="h-8 w-8 text-orange-600" />
              <div>
                <p className="text-sm text-muted-foreground">Unread</p>
                <p className="text-2xl font-semibold">{unreadCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-red-600" />
              <div>
                <p className="text-sm text-muted-foreground">Action Required</p>
                <p className="text-2xl font-semibold">{actionRequiredCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All ({notifications.length})</TabsTrigger>
          <TabsTrigger value="unread">Unread ({unreadCount})</TabsTrigger>
          <TabsTrigger value="action">Action Required ({actionRequiredCount})</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {sortedNotifications.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center">
                <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3>No Notifications</h3>
                <p className="text-muted-foreground">
                  You're all caught up! New notifications will appear here.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {sortedNotifications.map((notification) => (
                <Card 
                  key={notification.id} 
                  className={`transition-all hover:shadow-md ${
                    !notification.isRead ? 'border-l-4 border-l-blue-500 bg-blue-50/30' : ''
                  }`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">
                        {getNotificationIcon(notification.type)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <h4 className={`font-medium ${!notification.isRead ? 'text-blue-900' : ''}`}>
                              {notification.title}
                            </h4>
                            <p className="text-sm text-muted-foreground mt-1">
                              {notification.message}
                            </p>
                          </div>
                          
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <Badge 
                              variant="outline" 
                              className={`text-xs ${getPriorityColor(notification.priority)}`}
                            >
                              {notification.priority}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {formatTimeAgo(notification.createdAt)}
                            </span>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2 mt-3">
                          {!notification.isRead && (
                            <Button 
                              onClick={() => handleMarkAsRead(notification.id)}
                              variant="outline" 
                              size="sm"
                            >
                              <Eye className="h-3 w-3 mr-1" />
                              Mark Read
                            </Button>
                          )}
                          
                          {notification.actionRequired && notification.relatedId && (
                            <>
                              {notification.type === 'conflict_report' && (
                                <Dialog>
                                  <DialogTrigger asChild>
                                    <Button 
                                      onClick={() => setSelectedConflictReport(notification.relatedId!)}
                                      size="sm"
                                    >
                                      Review Conflict
                                    </Button>
                                  </DialogTrigger>
                                  <DialogContent className="max-w-md">
                                    <DialogHeader>
                                      <DialogTitle>Review Conflict Report</DialogTitle>
                                      <DialogDescription>
                                        Review the conflict report details and take appropriate action.
                                      </DialogDescription>
                                    </DialogHeader>
                                    <div className="space-y-4">
                                      {selectedConflictReport && (
                                        <>
                                          {(() => {
                                            const report = conflictReports.find(r => r.id === selectedConflictReport);
                                            return report ? (
                                              <div className="space-y-3">
                                                <div className="p-3 bg-muted rounded-md">
                                                  <p className="text-sm"><strong>Course:</strong> {report.courseCode}</p>
                                                  <p className="text-sm"><strong>Student ID:</strong> {report.studentId}</p>
                                                  <p className="text-sm"><strong>Description:</strong></p>
                                                  <p className="text-sm text-muted-foreground">{report.description}</p>
                                                </div>
                                                
                                                <div>
                                                  <Label>Review Notes (Optional)</Label>
                                                  <Textarea
                                                    value={reviewNotes}
                                                    onChange={(e) => setReviewNotes(e.target.value)}
                                                    placeholder="Add notes about your review..."
                                                    rows={3}
                                                  />
                                                </div>
                                                
                                                <div className="flex gap-2">
                                                  <Button 
                                                    onClick={() => handleResolveConflictReport(report.id, 'reviewed', reviewNotes)}
                                                    className="flex-1"
                                                  >
                                                    Mark Reviewed
                                                  </Button>
                                                  <Button 
                                                    onClick={() => handleResolveConflictReport(report.id, 'resolved', reviewNotes)}
                                                    variant="outline"
                                                    className="flex-1"
                                                  >
                                                    Resolve
                                                  </Button>
                                                </div>
                                              </div>
                                            ) : null;
                                          })()}
                                        </>
                                      )}
                                    </div>
                                  </DialogContent>
                                </Dialog>
                              )}
                              
                              {notification.type === 'change_request' && (
                                <Dialog>
                                  <DialogTrigger asChild>
                                    <Button 
                                      onClick={() => setSelectedChangeRequest(notification.relatedId!)}
                                      size="sm"
                                    >
                                      Review Request
                                    </Button>
                                  </DialogTrigger>
                                  <DialogContent className="max-w-md">
                                    <DialogHeader>
                                      <DialogTitle>Review Change Request</DialogTitle>
                                      <DialogDescription>
                                        Review the staff change request and decide whether to approve or deny it.
                                      </DialogDescription>
                                    </DialogHeader>
                                    <div className="space-y-4">
                                      {selectedChangeRequest && (
                                        <>
                                          {(() => {
                                            const request = changeRequests.find(r => r.id === selectedChangeRequest);
                                            return request ? (
                                              <div className="space-y-3">
                                                <div className="p-3 bg-muted rounded-md">
                                                  <p className="text-sm"><strong>Course:</strong> {request.courseCode}</p>
                                                  <p className="text-sm"><strong>Staff ID:</strong> {request.staffId}</p>
                                                  <p className="text-sm"><strong>Reason:</strong> {request.reason}</p>
                                                  {request.description && (
                                                    <>
                                                      <p className="text-sm"><strong>Description:</strong></p>
                                                      <p className="text-sm text-muted-foreground">{request.description}</p>
                                                    </>
                                                  )}
                                                </div>
                                                
                                                <div>
                                                  <Label>Review Notes (Optional)</Label>
                                                  <Textarea
                                                    value={reviewNotes}
                                                    onChange={(e) => setReviewNotes(e.target.value)}
                                                    placeholder="Add notes about your decision..."
                                                    rows={3}
                                                  />
                                                </div>
                                                
                                                <div className="flex gap-2">
                                                  <Button 
                                                    onClick={() => handleResolveChangeRequest(request.id, 'approved', reviewNotes)}
                                                    className="flex-1 bg-green-600 hover:bg-green-700"
                                                  >
                                                    Approve
                                                  </Button>
                                                  <Button 
                                                    onClick={() => handleResolveChangeRequest(request.id, 'denied', reviewNotes)}
                                                    variant="destructive"
                                                    className="flex-1"
                                                  >
                                                    Deny
                                                  </Button>
                                                </div>
                                              </div>
                                            ) : null;
                                          })()}
                                        </>
                                      )}
                                    </div>
                                  </DialogContent>
                                </Dialog>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="unread" className="space-y-4">
          <div className="space-y-3">
            {sortedNotifications.filter(n => !n.isRead).map((notification) => (
              <Card 
                key={notification.id} 
                className="transition-all hover:shadow-md border-l-4 border-l-blue-500 bg-blue-50/30"
              >
                {/* Same notification card content as above */}
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {getNotificationIcon(notification.type)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <h4 className="font-medium text-blue-900">
                            {notification.title}
                          </h4>
                          <p className="text-sm text-muted-foreground mt-1">
                            {notification.message}
                          </p>
                        </div>
                        
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${getPriorityColor(notification.priority)}`}
                          >
                            {notification.priority}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatTimeAgo(notification.createdAt)}
                          </span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 mt-3">
                        <Button 
                          onClick={() => handleMarkAsRead(notification.id)}
                          variant="outline" 
                          size="sm"
                        >
                          <Eye className="h-3 w-3 mr-1" />
                          Mark Read
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="action" className="space-y-4">
          <div className="space-y-3">
            {sortedNotifications.filter(n => n.actionRequired && !n.isRead).map((notification) => (
              <Card 
                key={notification.id} 
                className="transition-all hover:shadow-md border-l-4 border-l-red-500 bg-red-50/30"
              >
                {/* Same notification card content as above */}
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">
                      {getNotificationIcon(notification.type)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <h4 className="font-medium text-red-900">
                            {notification.title}
                          </h4>
                          <p className="text-sm text-muted-foreground mt-1">
                            {notification.message}
                          </p>
                        </div>
                        
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <Badge 
                            variant="outline" 
                            className={`text-xs ${getPriorityColor(notification.priority)}`}
                          >
                            {notification.priority}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatTimeAgo(notification.createdAt)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}