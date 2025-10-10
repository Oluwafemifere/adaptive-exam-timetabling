import React, { useState, useEffect } from "react";
import {
  User,
  Plus,
  Search,
  MoreHorizontal,
  Edit,
  Trash2,
  Shield,
  UserCheck,
  Users,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Avatar, AvatarFallback } from "../components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "../components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { toast } from "sonner";
import { useUserManagementData } from "../hooks/useApi";
import { api } from "../services/api";
import { useAppStore } from "../store";
import {
  AdminUserCreatePayload,
  UserManagementRecord,
  UserUpdatePayload,
  UserRole,
} from "../store/types";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "../components/ui/pagination";

// Simple debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

const AvatarInitials = ({ name }: { name: string }) => {
  const initials = name
    ? name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
    : "?";
  return <span>{initials}</span>;
};

interface UserFormData
  extends Partial<AdminUserCreatePayload>,
    Partial<UserUpdatePayload> {
  id?: string;
}

const UserFormDialog = ({
  user,
  isOpen,
  onClose,
  onSave,
}: {
  user: UserManagementRecord | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (
    data: AdminUserCreatePayload | UserUpdatePayload,
    userId?: string
  ) => void;
}) => {
  const [formData, setFormData] = useState<Partial<UserFormData>>({});
  const [userType, setUserType] = useState<"student" | "admin">("student");
  const { activeSessionId } = useAppStore();

  useEffect(() => {
    if (user) {
      setFormData({
        id: user.id,
        first_name: user.first_name,
        last_name: user.last_name,
        email: user.email,
        role: user.role,
        is_active: user.is_active,
      });
      setUserType(
        user.role === "admin" || user.role === "superuser"
          ? "admin"
          : "student"
      );
    } else {
      setFormData({
        user_type: "student",
        first_name: "",
        last_name: "",
        email: "",
        password: "",
      });
      setUserType("student");
    }
  }, [user, isOpen]);

  const handleSave = () => {
    if (user?.id) {
      const payload: UserUpdatePayload = {
        first_name: formData.first_name || "",
        last_name: formData.last_name || "",
        email: formData.email || "",
        role: (formData.role as UserRole) || "student",
        is_active: formData.is_active ?? true,
      };
      onSave(payload, user.id);
    } else {
      if (
        userType === "student" &&
        (!formData.matric_number ||
          !formData.programme_code ||
          !formData.entry_year)
      ) {
        toast.error(
          "Matric number, programme code, and entry year are required for students."
        );
        return;
      }
      if (!formData.password) {
        toast.error("Password is required for new users.");
        return;
      }
      const payload: AdminUserCreatePayload = {
        user_type: userType,
        email: formData.email || "",
        first_name: formData.first_name || "",
        last_name: formData.last_name || "",
        password: formData.password || "",
        session_id: activeSessionId || undefined,
        matric_number: formData.matric_number,
        programme_code: formData.programme_code,
        entry_year: formData.entry_year,
      };
      onSave(payload);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{user?.id ? "Edit User" : "Add New User"}</DialogTitle>
          <DialogDescription>
            {user?.id
              ? `Editing account details for ${user.first_name} ${user.last_name}`
              : "Create a new user account"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {!user?.id && (
            <div className="space-y-2">
              <Label>User Type</Label>
              <Select
                value={userType}
                onValueChange={(v) => setUserType(v as "student" | "admin")}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select user type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="student">Student</SelectItem>
                  <SelectItem value="admin">Administrator</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>First Name</Label>
              <Input
                placeholder="John"
                value={formData.first_name || ""}
                onChange={(e) =>
                  setFormData({ ...formData, first_name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>Last Name</Label>
              <Input
                placeholder="Doe"
                value={formData.last_name || ""}
                onChange={(e) =>
                  setFormData({ ...formData, last_name: e.target.value })
                }
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Email Address</Label>
            <Input
              type="email"
              placeholder="user@example.com"
              value={formData.email || ""}
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
            />
          </div>

          {!user?.id && (
            <div className="space-y-2">
              <Label>Password</Label>
              <Input
                type="password"
                placeholder="Enter a strong password"
                value={formData.password || ""}
                onChange={(e) =>
                  setFormData({ ...formData, password: e.target.value })
                }
              />
            </div>
          )}

          {userType === "student" && !user?.id && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Matric Number</Label>
                  <Input
                    placeholder="F/01/12345"
                    value={formData.matric_number || ""}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        matric_number: e.target.value,
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Programme Code</Label>
                  <Input
                    placeholder="e.g., CS"
                    value={formData.programme_code || ""}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        programme_code: e.target.value,
                      })
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Entry Year</Label>
                <Input
                  type="number"
                  placeholder="e.g., 2021"
                  value={formData.entry_year || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      entry_year: Number(e.target.value) || undefined,
                    })
                  }
                />
              </div>
            </>
          )}

          <div className="flex justify-end space-x-3 pt-4">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleSave}>
              {user?.id ? "Save Changes" : "Create User"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export function UserManagement() {
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearch = useDebounce(searchTerm, 500);
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedUser, setSelectedUser] = useState<UserManagementRecord | null>(
    null
  );
  const [isFormOpen, setIsFormOpen] = useState(false);

  const { users, pagination, isLoading, error, refetch } =
    useUserManagementData();
  const { updateUserInList, removeUserFromList } = useAppStore();

  useEffect(() => {
    refetch({
      page: currentPage,
      page_size: 10,
      search_term: debouncedSearch || undefined,
      role_filter: roleFilter === "all" ? undefined : roleFilter,
      status_filter: statusFilter === "all" ? undefined : statusFilter,
    });
  }, [debouncedSearch, roleFilter, statusFilter, currentPage, refetch]);

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "superuser":
      case "admin":
        return Shield;
      case "staff":
        return UserCheck;
      case "student":
        return User;
      default:
        return User;
    }
  };

  const getStatusColor = (isActive: boolean) =>
    isActive
      ? "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300"
      : "bg-gray-100 text-gray-700 dark:bg-gray-900/50 dark:text-gray-300";

  const handleSaveUser = async (
    data: AdminUserCreatePayload | UserUpdatePayload,
    userId?: string
  ) => {
    try {
      if (userId) {
        const response = await api.updateUser(userId, data as UserUpdatePayload);
        updateUserInList(response.data.data as UserManagementRecord);
        toast.success("User updated successfully.");
      } else {
        const response = await api.adminCreateUser(data as AdminUserCreatePayload);
        if (response.data.success) {
          refetch({ page: 1, page_size: 10 });
          toast.success("User created successfully.");
        } else throw new Error(response.data.message || "Failed to create user.");
      }
      setIsFormOpen(false);
      setSelectedUser(null);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || "Error occurred.";
      toast.error(`Error: ${detail}`);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (window.confirm("Are you sure you want to delete this user?")) {
      try {
        await api.deleteUser(userId);
        removeUserFromList(userId);
        toast.success("User deleted successfully.");
      } catch (err: any) {
        toast.error(err.response?.data?.detail || "Failed to delete user.");
      }
    }
  };

  const userStats = {
    total: pagination.total_items,
    active: users.filter((u) => u.is_active).length,
    admins: users.filter((u) => ["admin", "superuser"].includes(u.role)).length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">User Account Management</h1>
          <p className="text-muted-foreground">
            Track, manage, and configure all user accounts
          </p>
        </div>
        <Button
          onClick={() => {
            setSelectedUser(null);
            setIsFormOpen(true);
          }}
        >
          <Plus className="h-4 w-4 mr-2" /> Add User
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/50 rounded-full">
                <Users className="h-4 w-4 text-blue-600 dark:text-blue-300" />
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

      {/* Filters */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search users by name or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            <div className="flex space-x-3">
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Filter by role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Roles</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="staff">Staff</SelectItem>
                  <SelectItem value="student">Student</SelectItem>
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
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* User Table */}
      <Card>
        <CardHeader>
          <CardTitle>Users ({pagination.total_items})</CardTitle>
          <CardDescription>Manage user accounts and permissions</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && <div className="text-center py-8">Loading users...</div>}
          {!isLoading && error && (
            <div className="text-center py-8 text-destructive">
              Error: {error.message}
            </div>
          )}
          {!isLoading && !error && (
            users.length === 0 ? (
              <div className="py-16 text-center">
                <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="font-semibold">No Users Found</h3>
                <p className="text-muted-foreground text-sm">
                  No users match the current criteria.
                </p>
                <Button
                  className="mt-4"
                  onClick={() => {
                    setSelectedUser(null);
                    setIsFormOpen(true);
                  }}
                >
                  <Plus className="h-4 w-4 mr-2" /> Add First User
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => {
                    const RoleIcon = getRoleIcon(user.role);
                    const fullName = `${user.first_name} ${user.last_name}`;
                    return (
                      <TableRow key={user.id}>
                        <TableCell>
                          <div className="flex items-center space-x-3">
                            <Avatar className="h-8 w-8">
                              <AvatarFallback>
                                <AvatarInitials name={fullName} />
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <div className="font-medium">{fullName}</div>
                              <div className="text-sm text-muted-foreground">
                                {user.email}
                              </div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge>
                            <RoleIcon className="h-3 w-3 mr-1" />
                            {user.role}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getStatusColor(user.is_active)}>
                            {user.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {user.last_login
                            ? new Date(user.last_login).toLocaleString()
                            : "Never"}
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
                                onClick={() => {
                                  setSelectedUser(user);
                                  setIsFormOpen(true);
                                }}
                              >
                                <Edit className="h-4 w-4 mr-2" /> Edit User
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={() => handleDeleteUser(user.id)}
                              >
                                <Trash2 className="h-4 w-4 mr-2" /> Delete User
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )
          )}
        </CardContent>

        {pagination.total_pages > 1 && (
          <Pagination className="p-4">
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    setCurrentPage((p) => Math.max(1, p - 1));
                  }}
                />
              </PaginationItem>
              {Array.from({ length: pagination.total_pages }).map((_, i) => (
                <PaginationItem key={i}>
                  <PaginationLink
                    href="#"
                    isActive={currentPage === i + 1}
                    onClick={(e) => {
                      e.preventDefault();
                      setCurrentPage(i + 1);
                    }}
                  >
                    {i + 1}
                  </PaginationLink>
                </PaginationItem>
              ))}
              <PaginationItem>
                <PaginationNext
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    setCurrentPage((p) =>
                      Math.min(pagination.total_pages, p + 1)
                    );
                  }}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        )}
      </Card>

      {isFormOpen && (
        <UserFormDialog
          isOpen={isFormOpen}
          onClose={() => {
            setIsFormOpen(false);
            setSelectedUser(null);
          }}
          onSave={handleSaveUser}
          user={selectedUser}
        />
      )}
    </div>
  );
}
