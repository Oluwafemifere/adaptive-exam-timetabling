import React, { useState } from 'react';
import { 
  User, 
  Plus, 
  Search,
  Filter,
  MoreHorizontal,
  Edit,
  Trash2,
  Shield,
  ShieldCheck,
  UserCheck,
  UserX,
  Mail,
  Calendar,
  Eye
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Avatar, AvatarFallback } from '../components/ui/avatar'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '../components/ui/dropdown-menu'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '../components/ui/table'
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '../components/ui/dialog'
import { Label } from '../components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Switch } from '../components/ui/switch'
import { cn } from '../components/ui/utils'
import { toast } from 'sonner'

interface User {
  id: string;
  name: string;
  email: string;
  role: 'University Admin' | 'Department Admin' | 'Faculty Staff' | 'Viewer';
  department: string;
  status: 'active' | 'inactive' | 'pending';
  lastLogin: string;
  permissions: {
    canCreateSessions: boolean;
    canModifyTimetables: boolean;
    canViewReports: boolean;
    canManageUsers: boolean;
    canConfigureConstraints: boolean;
  };
  createdAt: string;
}

const AvatarInitials = ({ name }: { name: string }) => {
  const initials = name.split(' ').map(n => n[0]).join('').toUpperCase();
  return <span>{initials}</span>;
};

export function UserManagement() {
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  // Mock user data
  const [users] = useState<User[]>([
    {
      id: '1',
      name: 'Dr. Sarah Johnson',
      email: 'sarah.johnson@university.edu',
      role: 'University Admin',
      department: 'Administration',
      status: 'active',
      lastLogin: '2 hours ago',
      createdAt: '2024-01-15',
      permissions: {
        canCreateSessions: true,
        canModifyTimetables: true,
        canViewReports: true,
        canManageUsers: true,
        canConfigureConstraints: true,
      }
    },
    {
      id: '2',
      name: 'Prof. Michael Chen',
      email: 'michael.chen@university.edu',
      role: 'Department Admin',
      department: 'Computer Science',
      status: 'active',
      lastLogin: '1 day ago',
      createdAt: '2024-02-03',
      permissions: {
        canCreateSessions: false,
        canModifyTimetables: true,
        canViewReports: true,
        canManageUsers: false,
        canConfigureConstraints: true,
      }
    },
    {
      id: '3',
      name: 'Dr. Emily Rodriguez',
      email: 'emily.rodriguez@university.edu',
      role: 'Department Admin',
      department: 'Mathematics',
      status: 'active',
      lastLogin: '3 hours ago',
      createdAt: '2024-01-28',
      permissions: {
        canCreateSessions: false,
        canModifyTimetables: true,
        canViewReports: true,
        canManageUsers: false,
        canConfigureConstraints: true,
      }
    },
    {
      id: '4',
      name: 'James Wilson',
      email: 'james.wilson@university.edu',
      role: 'Faculty Staff',
      department: 'Physics',
      status: 'active',
      lastLogin: '1 week ago',
      createdAt: '2024-03-10',
      permissions: {
        canCreateSessions: false,
        canModifyTimetables: false,
        canViewReports: true,
        canManageUsers: false,
        canConfigureConstraints: false,
      }
    },
    {
      id: '5',
      name: 'Lisa Anderson',
      email: 'lisa.anderson@university.edu',
      role: 'Viewer',
      department: 'Biology',
      status: 'pending',
      lastLogin: 'Never',
      createdAt: '2024-03-15',
      permissions: {
        canCreateSessions: false,
        canModifyTimetables: false,
        canViewReports: true,
        canManageUsers: false,
        canConfigureConstraints: false,
      }
    },
    {
      id: '6',
      name: 'Robert Kim',
      email: 'robert.kim@university.edu',
      role: 'Faculty Staff',
      department: 'Chemistry',
      status: 'inactive',
      lastLogin: '2 months ago',
      createdAt: '2023-12-05',
      permissions: {
        canCreateSessions: false,
        canModifyTimetables: false,
        canViewReports: true,
        canManageUsers: false,
        canConfigureConstraints: false,
      }
    }
  ]);

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.department.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = roleFilter === 'all' || user.role === roleFilter;
    const matchesStatus = statusFilter === 'all' || user.status === statusFilter;
    
    return matchesSearch && matchesRole && matchesStatus;
  });

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'University Admin': return ShieldCheck;
      case 'Department Admin': return Shield;
      case 'Faculty Staff': return UserCheck;
      case 'Viewer': return Eye;
      default: return User;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300';
      case 'inactive': return 'bg-gray-100 text-gray-700 dark:bg-gray-900/50 dark:text-gray-300';
      case 'pending': return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300';
      default: return '';
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'University Admin': return 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300';
      case 'Department Admin': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300';
      case 'Faculty Staff': return 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300';
      case 'Viewer': return 'bg-gray-100 text-gray-700 dark:bg-gray-900/50 dark:text-gray-300';
      default: return '';
    }
  };

  const userStats = {
    total: users.length,
    active: users.filter(u => u.status === 'active').length,
    pending: users.filter(u => u.status === 'pending').length,
    admins: users.filter(u => u.role.includes('Admin')).length,
  };

  const handleUserAction = (action: string, userId: string) => {
    switch (action) {
      case 'activate':
        toast.success('User activated successfully');
        break;
      case 'deactivate':
        toast.success('User deactivated successfully');
        break;
      case 'delete':
        toast.success('User deleted successfully');
        break;
      case 'edit':
        const user = users.find(u => u.id === userId);
        setSelectedUser(user || null);
        break;
      default:
        break;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">User Management</h1>
          <p className="text-muted-foreground">Manage users and their permissions</p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add User
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/50 rounded-full">
                <User className="h-4 w-4 text-blue-600 dark:text-blue-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Users</p>
                <p className="text-lg font-semibold">{userStats.total}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-green-100 dark:bg-green-900/50 rounded-full">
                <UserCheck className="h-4 w-4 text-green-600 dark:text-green-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Active Users</p>
                <p className="text-lg font-semibold">{userStats.active}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-yellow-100 dark:bg-yellow-900/50 rounded-full">
                <UserX className="h-4 w-4 text-yellow-600 dark:text-yellow-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-lg font-semibold">{userStats.pending}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-purple-100 dark:bg-purple-900/50 rounded-full">
                <Shield className="h-4 w-4 text-purple-600 dark:text-purple-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Admins</p>
                <p className="text-lg font-semibold">{userStats.admins}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search users by name, email, or department..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex space-x-3">
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Filter by role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Roles</SelectItem>
                  <SelectItem value="University Admin">University Admin</SelectItem>
                  <SelectItem value="Department Admin">Department Admin</SelectItem>
                  <SelectItem value="Faculty Staff">Faculty Staff</SelectItem>
                  <SelectItem value="Viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardHeader>
          <CardTitle>Users ({filteredUsers.length})</CardTitle>
          <CardDescription>
            Manage user accounts and permissions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsers.map((user) => {
                const RoleIcon = getRoleIcon(user.role);
                return (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center space-x-3">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback>
                            <AvatarInitials name={user.name} />
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="font-medium">{user.name}</div>
                          <div className="text-sm text-muted-foreground">{user.email}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={getRoleColor(user.role)}>
                        <RoleIcon className="h-3 w-3 mr-1" />
                        {user.role}
                      </Badge>
                    </TableCell>
                    <TableCell>{user.department}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(user.status)}>
                        {user.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {user.lastLogin}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem 
                            onClick={() => handleUserAction('edit', user.id)}
                          >
                            <Edit className="h-4 w-4 mr-2" />
                            Edit User
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Mail className="h-4 w-4 mr-2" />
                            Send Email
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          {user.status === 'active' ? (
                            <DropdownMenuItem 
                              onClick={() => handleUserAction('deactivate', user.id)}
                            >
                              <UserX className="h-4 w-4 mr-2" />
                              Deactivate
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem 
                              onClick={() => handleUserAction('activate', user.id)}
                            >
                              <UserCheck className="h-4 w-4 mr-2" />
                              Activate
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            className="text-destructive"
                            onClick={() => handleUserAction('delete', user.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete User
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create User Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Add New User</DialogTitle>
            <DialogDescription>
              Create a new user account with appropriate permissions
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input id="name" placeholder="Enter full name" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input id="email" type="email" placeholder="Enter email address" />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Select>
                  <SelectTrigger>
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="University Admin">University Admin</SelectItem>
                    <SelectItem value="Department Admin">Department Admin</SelectItem>
                    <SelectItem value="Faculty Staff">Faculty Staff</SelectItem>
                    <SelectItem value="Viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="department">Department</Label>
                <Select>
                  <SelectTrigger>
                    <SelectValue placeholder="Select department" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Computer Science">Computer Science</SelectItem>
                    <SelectItem value="Mathematics">Mathematics</SelectItem>
                    <SelectItem value="Physics">Physics</SelectItem>
                    <SelectItem value="Chemistry">Chemistry</SelectItem>
                    <SelectItem value="Biology">Biology</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-4">
              <Label>Permissions</Label>
              <div className="space-y-3">
                {[
                  { key: 'canCreateSessions', label: 'Create Sessions', description: 'Allow user to create new academic sessions' },
                  { key: 'canModifyTimetables', label: 'Modify Timetables', description: 'Allow user to edit exam schedules' },
                  { key: 'canViewReports', label: 'View Reports', description: 'Allow user to view and export reports' },
                  { key: 'canManageUsers', label: 'Manage Users', description: 'Allow user to manage other user accounts' },
                  { key: 'canConfigureConstraints', label: 'Configure Constraints', description: 'Allow user to modify scheduling constraints' },
                ].map(permission => (
                  <div key={permission.key} className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <div className="text-sm font-medium">{permission.label}</div>
                      <div className="text-xs text-muted-foreground">{permission.description}</div>
                    </div>
                    <Switch />
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end space-x-3">
              <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => {
                toast.success('User created successfully');
                setIsCreateDialogOpen(false);
              }}>
                Create User
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}