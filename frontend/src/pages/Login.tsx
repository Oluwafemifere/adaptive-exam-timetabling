import React, { useState } from 'react';
import { Lock, Mail } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useAuth } from '../hooks/useAuth';

export function Login() {
  const [username, setUsername] = useState('admin@baze.edu');
  const [password, setPassword] = useState('demo');
  const { login, isLoggingIn, error } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await login(username, password);
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Exam Timetabling System</CardTitle>
          <CardDescription>
            Please sign in to access the scheduling dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="username">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="username"
                  type="email"
                  placeholder="user@example.com"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="********"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            {/* Demo Credentials */}
            <div className="bg-muted p-3 rounded-md space-y-2">
              <p className="text-sm font-medium">Demo Credentials:</p>
              <div className="text-xs space-y-1">
                <div className="flex justify-between">
                  <span>Administrator:</span>
                  <span className="font-mono">admin@baze.edu</span>
                </div>
                <div className="flex justify-between">
                  <span>Staff:</span>
                  <span className="font-mono">staff@baze.edu</span>
                </div>
                <div className="flex justify-between">
                  <span>Student:</span>
                  <span className="font-mono">student@baze.edu</span>
                </div>
                <div className="flex justify-between">
                  <span>Password (all):</span>
                  <span className="font-mono">demo</span>
                </div>
              </div>
            </div>
            
            {error && (
              <p className="text-sm text-destructive text-center">{error}</p>
            )}
            <Button type="submit" className="w-full" disabled={isLoggingIn}>
              {isLoggingIn ? 'Signing In...' : 'Sign In'}
            </Button>
          </form>
          
          {/* Quick Login Buttons */}
          <div className="mt-4 space-y-2">
            <p className="text-xs text-center text-muted-foreground">Quick Login:</p>
            <div className="grid grid-cols-3 gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  setUsername('admin@baze.edu');
                  setPassword('demo');
                }}
                disabled={isLoggingIn}
              >
                Admin
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  setUsername('staff@baze.edu');
                  setPassword('demo');
                }}
                disabled={isLoggingIn}
              >
                Staff
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => {
                  setUsername('student@baze.edu');
                  setPassword('demo');
                }}
                disabled={isLoggingIn}
              >
                Student
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}