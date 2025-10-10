// frontend/src/App.tsx
import React, { useEffect } from "react";
import { Toaster } from "sonner";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Scheduling } from "./pages/Scheduling";
import { Timetable } from "./pages/Timetable";
import { Constraints } from "./pages/Constraints";
import { SessionSetup } from "./pages/SessionSetup";
import { UserManagement } from "./pages/UserManagement";
import { Notifications } from "./pages/Notifications";
import { History } from "./pages/History";
import { StudentPortal } from "./pages/StudentPortal";
import { StaffPortal } from "./pages/StaffPortal";
import { useAppStore } from "./store";

function AppContent() {
  const { currentPage, isAuthenticated, user, initializeApp } = useAppStore();

  useEffect(() => {
    if (isAuthenticated) {
      initializeApp();
    }
  }, [isAuthenticated, initializeApp]);

  if (!isAuthenticated) {
    return <Login />;
  }

  // Role-based routing
  if (user?.role === "student") {
    return <StudentPortal />;
  }

  if (user?.role === "staff") {
    return <StaffPortal />;
  }
  
  if (user?.role === "admin" || user?.role === "superuser") {
    const renderPage = () => {
      switch (currentPage) {
        case "dashboard": return <Dashboard />;
        case "scheduling": return <Scheduling />;
        case "timetable": return <Timetable />;
        case "constraints": return <Constraints />;
        case "session-setup": return <SessionSetup />;
        case "user-management": return <UserManagement />;
        case "notifications": return <Notifications />;
        case "history": return <History />;
        default: return <Dashboard />;
      }
    };
    return <Layout>{renderPage()}</Layout>;
  }
  
  // Fallback for unrecognized roles
  return <Login />;
}

export default function App() {
  const { settings } = useAppStore.getState(); // Directly access state for initial render

  useEffect(() => {
    const unsubscribe = useAppStore.subscribe((state) => {
      const theme = state.settings.theme;
      const root = document.documentElement;
      if (theme === "dark") {
        root.classList.add("dark");
      } else {
        root.classList.remove("dark");
      }
    });
    // Apply initial theme
    const root = document.documentElement;
    if (settings.theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    return unsubscribe;
  }, [settings.theme]);

  return (
    <>
      <AppContent />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "hsl(var(--card))",
            color: "hsl(var(--card-foreground))",
            border: "1px solid hsl(var(--border))",
          },
        }}
      />
    </>
  );
}