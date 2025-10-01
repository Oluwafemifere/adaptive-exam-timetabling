// frontend/src/App.tsx

import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from './components/ui/sonner';
import { Layout } from './components/common/Layout';
import { Dashboard } from './pages/Dashboard';
import { Upload } from './pages/Upload';
import { Scheduling } from './pages/Scheduling';
import { Timetable } from './pages/Timetable';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';
import { useAppStore } from './store';
import { useAuthStore } from './hooks/useAuth';
import { Login } from './pages/Login';
import { useEffect } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';

// Create a client instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      retry: (failureCount, error: any) => {
        // Don't retry on 401/403/404 errors
        if (error.response?.status === 401 || error.response?.status === 403 || error.response?.status === 404) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});

function AppContent() {
  const { currentPage, settings } = useAppStore();
  
  // Effect to toggle dark mode class on the body element
  useEffect(() => {
    const body = window.document.body;
    const root = window.document.documentElement;
    
    body.classList.remove('light', 'dark');
    root.classList.remove('light', 'dark');
    
    body.classList.add(settings.theme);
    root.classList.add(settings.theme);
  }, [settings.theme]);

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />;
      case 'upload':
        return <Upload />;
      case 'scheduling':
        return <Scheduling />;
      case 'timetable':
        return <Timetable />;
      case 'reports':
        return <Reports />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <Layout>
      {renderCurrentPage()}
    </Layout>
  );
}

// This component will decide whether to show Login or the main App
function AuthGate() {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Login />;
  }

  return <AppContent />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DndProvider backend={HTML5Backend}>
        <div className="min-h-screen bg-background text-foreground">
          <AuthGate />
          <Toaster 
            position="top-right"
            expand={true}
            richColors
            closeButton
          />
        </div>
      </DndProvider>
    </QueryClientProvider>
  );
}