import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from './components/ui/sonner'
import { Layout } from './components/common/Layout'
import { Dashboard } from './pages/Dashboard'
import { Upload } from './pages/Upload'
import { Scheduling } from './pages/Scheduling'
import { Timetable } from './pages/Timetable'
import { Reports } from './pages/Reports'
import { Settings } from './pages/Settings'
import { useAppStore } from './store'
import { useRealTimeUpdates } from './hooks/useApi'

// Create a client instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      cacheTime: 1000 * 60 * 10, // 10 minutes
      retry: 2,
    },
  },
})

function AppContent() {
  const { currentPage } = useAppStore()
  
  // Initialize real-time updates
  useRealTimeUpdates()

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />
      case 'upload':
        return <Upload />
      case 'scheduling':
        return <Scheduling />
      case 'timetable':
        return <Timetable />
      case 'reports':
        return <Reports />
      case 'settings':
        return <Settings />
      default:
        return <Dashboard />
    }
  }

  return (
    <Layout>
      {renderCurrentPage()}
    </Layout>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <AppContent />
        <Toaster 
          position="top-right"
          expand={true}
          richColors
          closeButton
        />
      </div>
    </QueryClientProvider>
  )
}