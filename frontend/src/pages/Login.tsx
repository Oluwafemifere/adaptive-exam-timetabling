// frontend/src/pages/Login.tsx
import React, { useState } from 'react';
import { Lock, Mail, UserPlus, GraduationCap, User as UserIcon } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'; // Import Tabs
import { useAuth } from '../hooks/useAuth';
import { toast } from 'sonner';
import { api } from '../services/api';

export function Login() {
  const [username, setUsername] = useState('admin@baze.edu');
  const [password, setPassword] = useState('demo');
  const { login, isLoggingIn, error } = useAuth();
  const [isCreateAccountOpen, setCreateAccountOpen] = useState(false);

  // --- State for the registration forms ---
  const [registrationType, setRegistrationType] = useState<'student' | 'staff'>('student');
  const [isRegistering, setIsRegistering] = useState(false);

  // --- FIX: Separate state for each registration form to prevent data leakage between tabs ---
  const [studentEmail, setStudentEmail] = useState('');
  const [studentPassword, setStudentPassword] = useState('');
  const [matricNumber, setMatricNumber] = useState('');

  const [staffEmail, setStaffEmail] = useState('');
  const [staffPassword, setStaffPassword] = useState('');
  const [staffNumber, setStaffNumber] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login(username, password);
  };

  const resetForm = () => {
    // FIX: Clear all registration form fields
    setStudentEmail('');
    setStudentPassword('');
    setMatricNumber('');
    setStaffEmail('');
    setStaffPassword('');
    setStaffNumber('');
    setRegistrationType('student');
  };

  const handleCreateAccount = async () => {
    setIsRegistering(true);
    try {
      let response;
      if (registrationType === 'student') {
        // FIX: Use student-specific state and add check to stop loading on validation error
        if (!matricNumber || !studentEmail || !studentPassword) {
          toast.error('Please fill out all fields for student registration.');
          setIsRegistering(false);
          return;
        }
        response = await api.selfRegisterStudent({ matric_number: matricNumber, email: studentEmail, password: studentPassword });
      } else {
        // FIX: Use staff-specific state and add check to stop loading on validation error
        if (!staffNumber || !staffEmail || !staffPassword) {
          toast.error('Please fill out all fields for staff registration.');
          setIsRegistering(false);
          return;
        }
        response = await api.selfRegisterStaff({ staff_number: staffNumber, email: staffEmail, password: staffPassword });
      }

      if (response.data.success) {
        toast.success('Account created successfully! You can now log in.');
        setCreateAccountOpen(false);
        resetForm();
      } else {
        throw new Error(response.data.message || 'Registration failed.');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'An unknown error occurred.';
      toast.error(`Registration Failed: ${errorMessage}`);
    } finally {
      setIsRegistering(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Exam Timetabling System</CardTitle>
          <CardDescription>Please sign in to access the scheduling dashboard.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="username">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input id="username" type="email" placeholder="user@example.com" required value={username} onChange={(e) => setUsername(e.target.value)} className="pl-10" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input id="password" type="password" placeholder="********" required value={password} onChange={(e) => setPassword(e.target.value)} className="pl-10" />
              </div>
            </div>
            {error && <p className="text-sm text-destructive text-center">{error}</p>}
            <Button type="submit" className="w-full" disabled={isLoggingIn}>{isLoggingIn ? 'Signing In...' : 'Sign In'}</Button>
          </form>

          <div className="mt-4 text-center">
            <Dialog open={isCreateAccountOpen} onOpenChange={setCreateAccountOpen}>
              <DialogTrigger asChild>
                <Button variant="link" className="text-sm">Don't have an account? Create one</Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Create Account</DialogTitle>
                  <DialogDescription>
                    If you are a registered student or staff member, create your user account here.
                  </DialogDescription>
                </DialogHeader>
                <Tabs value={registrationType} onValueChange={(value) => setRegistrationType(value as 'student' | 'staff')} className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="student"><GraduationCap className="h-4 w-4 mr-2" />Student</TabsTrigger>
                    <TabsTrigger value="staff"><UserIcon className="h-4 w-4 mr-2" />Staff</TabsTrigger>
                  </TabsList>
                  
                  {/* Student Registration Form */}
                  <TabsContent value="student">
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label htmlFor="matricNumber">Matriculation Number</Label>
                        <Input id="matricNumber" placeholder="e.g., BSU/20/CS/1234" value={matricNumber} onChange={e => setMatricNumber(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="student-email">Email</Label>
                        {/* FIX: Use student-specific email state */}
                        <Input id="student-email" type="email" placeholder="your.email@university.edu" value={studentEmail} onChange={e => setStudentEmail(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="student-password">Password</Label>
                        {/* FIX: Use student-specific password state */}
                        <Input id="student-password" type="password" placeholder="Choose a secure password" value={studentPassword} onChange={e => setStudentPassword(e.target.value)} />
                      </div>
                    </div>
                  </TabsContent>
                  
                  {/* Staff Registration Form */}
                  <TabsContent value="staff">
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label htmlFor="staffNumber">Staff ID Number</Label>
                        <Input id="staffNumber" placeholder="e.g., 98765" value={staffNumber} onChange={e => setStaffNumber(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="staff-email">Email</Label>
                        {/* FIX: Use staff-specific email state */}
                        <Input id="staff-email" type="email" placeholder="your.email@university.edu" value={staffEmail} onChange={e => setStaffEmail(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="staff-password">Password</Label>
                        {/* FIX: Use staff-specific password state */}
                        <Input id="staff-password" type="password" placeholder="Choose a secure password" value={staffPassword} onChange={e => setStaffPassword(e.target.value)} />
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
                <div className="flex justify-end pt-2">
                  <Button onClick={handleCreateAccount} disabled={isRegistering}>
                    {isRegistering ? 'Creating...' : <><UserPlus className="h-4 w-4 mr-2" /> Create Account</>}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}