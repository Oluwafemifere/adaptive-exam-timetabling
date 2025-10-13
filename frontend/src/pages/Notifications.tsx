// frontend/src/pages/Notifications.tsx
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { 
  Bell, 
  AlertTriangle, 
  FileEdit, 
  Eye,
  Loader2,
  Filter,
  RefreshCw
} from 'lucide-react';
import { useAppStore } from '../store';
import { toast } from 'sonner';
import { useAllReportsData } from '../hooks/useApi';
import { AdminConflictReport, AdminChangeRequest } from '../store/types';
import { Alert, AlertDescription } from '../components/ui/alert';

const formatTimeAgo = (dateString: string) => {
  if (!dateString) return 'N/A';
  const now = new Date();
  const date = new Date(dateString);
  const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
  
  if (diffInMinutes < 1) return 'Just now';
  if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
  if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
  return `${Math.floor(diffInMinutes / 1440)}d ago`;
};

const ConflictReportDetails = ({ report }: { report: AdminConflictReport }) => (
  <div className="space-y-4 text-sm">
    <div><Label>Student</Label><p>{report.student.first_name} {report.student.last_name} ({report.student.matric_number})</p></div>
    <div><Label>Course</Label><p>{report.exam_details.course_code} - {report.exam_details.course_title}</p></div>
    <div><Label>Description</Label><p className="p-2 bg-muted rounded-md">{report.description || 'No description provided.'}</p></div>
    <div><Label>Submitted</Label><p>{new Date(report.submitted_at).toLocaleString()}</p></div>
    <div className="flex justify-end gap-2 pt-4">
      <Button variant="outline">Mark as Reviewed</Button>
      <Button>Resolve Issue</Button>
    </div>
  </div>
);

const ChangeRequestDetails = ({ request }: { request: AdminChangeRequest }) => (
  <div className="space-y-4 text-sm">
    <div><Label>Staff</Label><p>{request.staff.first_name} {request.staff.last_name} ({request.staff.staff_number})</p></div>
    <div><Label>Assignment</Label><p>{request.assignment_details.course_code} on {request.assignment_details.exam_date} in {request.assignment_details.room_code}</p></div>
    <div><Label>Reason</Label><p>{request.reason}</p></div>
    {request.description && <div><Label>Description</Label><p className="p-2 bg-muted rounded-md">{request.description}</p></div>}
    <div><Label>Submitted</Label><p>{new Date(request.submitted_at).toLocaleString()}</p></div>
    <div className="flex justify-end gap-2 pt-4">
      <Button variant="destructive">Deny Request</Button>
      <Button className="bg-green-600 hover:bg-green-700">Approve Request</Button>
    </div>
  </div>
);

export function Notifications() {
  const { reportSummaryCounts, allConflictReports, allChangeRequests } = useAppStore();
  const [statuses, setStatuses] = useState<string[]>([]);
  const { isLoading, error, refetch } = useAllReportsData();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<AdminConflictReport | AdminChangeRequest | null>(null);
  
  const handleApplyFilters = () => {
    refetch({ statuses: statuses.length > 0 ? statuses : undefined });
    toast.info('Filters applied');
  };

  const handleClearFilters = () => {
    setStatuses([]);
    refetch();
    toast.info('Filters cleared');
  };

  const openModal = (item: AdminConflictReport | AdminChangeRequest) => {
    setSelectedItem(item);
    setIsModalOpen(true);
  };

  return (
    <>
      {/* The Dialog component is now separate from the layout flow */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>
              {selectedItem && 'student' in selectedItem ? 'Conflict Report Details' : 'Change Request Details'}
            </DialogTitle>
            <DialogDescription>
              Review the item details below and take the appropriate action.
            </DialogDescription>
          </DialogHeader>
          {selectedItem && (
            'student' in selectedItem
              ? <ConflictReportDetails report={selectedItem as AdminConflictReport} />
              : <ChangeRequestDetails request={selectedItem as AdminChangeRequest} />
          )}
        </DialogContent>
      </Dialog>
      
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">Reports & Requests</h2>
            <p className="text-muted-foreground">
              Manage student conflict reports and staff change requests.
            </p>
          </div>
          <Button onClick={() => refetch()} variant="outline" size="sm" disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Bell className="h-8 w-8 text-blue-600" />
                <div>
                  <p className="text-sm text-muted-foreground">Total Items</p>
                  <p className="text-2xl font-semibold">{reportSummaryCounts?.total ?? '...'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-8 w-8 text-orange-600" />
                <div>
                  <p className="text-sm text-muted-foreground">Pending / Unread</p>
                  <p className="text-2xl font-semibold">{reportSummaryCounts?.unread ?? '...'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <FileEdit className="h-8 w-8 text-purple-600" />
                <div>
                  <p className="text-sm text-muted-foreground">Urgent Action</p>
                  <p className="text-2xl font-semibold">{reportSummaryCounts?.urgent_action_required ?? '...'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filter Controls */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2"><Filter className="h-5 w-5" />Filter Reports</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col md:flex-row gap-4 items-center">
            <div className="w-full md:w-64">
              <Label>Status</Label>
              <Select value={statuses.join(',')} onValueChange={(value) => setStatuses(value ? value.split(',') : [])}>
                <SelectTrigger><SelectValue placeholder="Filter by status..." /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="denied">Denied</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 self-end">
              <Button onClick={handleApplyFilters} disabled={isLoading}>Apply Filters</Button>
              <Button onClick={handleClearFilters} variant="outline" disabled={isLoading}>Clear</Button>
            </div>
          </CardContent>
        </Card>

        {isLoading ? (
          <div className="flex justify-center items-center py-16"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
        ) : error ? (
          <Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertDescription>{error.message}</AlertDescription></Alert>
        ) : (
          <Tabs defaultValue="conflicts" className="space-y-4">
            <TabsList>
              <TabsTrigger value="conflicts">Conflict Reports ({allConflictReports.length})</TabsTrigger>
              <TabsTrigger value="requests">Change Requests ({allChangeRequests.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="conflicts">
              <Card>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader><TableRow><TableHead>Student</TableHead><TableHead>Course</TableHead><TableHead>Status</TableHead><TableHead>Submitted</TableHead><TableHead>Actions</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {allConflictReports.map((report: AdminConflictReport) => (
                      <TableRow key={report.id}>
                        <TableCell>
                          <div className="font-medium">{report.student.first_name} {report.student.last_name}</div>
                          <div className="text-sm text-muted-foreground">{report.student.matric_number}</div>
                        </TableCell>
                        <TableCell>{report.exam_details.course_code}</TableCell>
                        <TableCell><Badge variant={report.status === 'pending' ? 'destructive' : 'secondary'}>{report.status}</Badge></TableCell>
                        <TableCell>{formatTimeAgo(report.submitted_at)}</TableCell>
                        {/* --- FIX: Button now just calls openModal --- */}
                        <TableCell><Button variant="outline" size="sm" onClick={() => openModal(report)}><Eye className="h-4 w-4 mr-2" />View</Button></TableCell>
                      </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </Card>
            </TabsContent>

            <TabsContent value="requests">
               <Card>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Staff</TableHead>
                            <TableHead>Course</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Submitted</TableHead>
                            <TableHead>Reason</TableHead>
                            <TableHead>Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                      {allChangeRequests.map((request: AdminChangeRequest) => (
                      <TableRow key={request.id}>
                        <TableCell>
                          <div className="font-medium">{request.staff.first_name} {request.staff.last_name}</div>
                          <div className="text-sm text-muted-foreground">{request.staff.staff_number}</div>
                        </TableCell>
                        <TableCell>{request.assignment_details.course_code}</TableCell>
                        <TableCell><Badge variant={request.status === 'pending' ? 'destructive' : request.status === 'approved' ? 'default' : 'secondary'}>{request.status}</Badge></TableCell>
                        <TableCell>{formatTimeAgo(request.submitted_at)}</TableCell>
                        <TableCell>{request.reason}</TableCell>
                        <TableCell><Button variant="outline" size="sm" onClick={() => openModal(request)}><Eye className="h-4 w-4 mr-2" />View</Button></TableCell>
                      </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </>
  );
}