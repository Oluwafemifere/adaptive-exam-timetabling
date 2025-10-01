import React, { useEffect } from "react";
import { Toaster } from "sonner";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Scheduling } from "./pages/Scheduling";
import { Timetable } from "./pages/Timetable";
import { Constraints } from "./pages/Constraints";
import { Scenarios } from "./pages/Scenarios";
import { Analytics } from "./pages/Analytics";
import { SessionSetup } from "./pages/SessionSetup";
import { UserManagement } from "./pages/UserManagement";
import { Notifications } from "./pages/Notifications";
import { History } from "./pages/History";
import { StudentPortal } from "./pages/StudentPortal";
import { StaffPortal } from "./pages/StaffPortal";
import { useAppStore } from "./store";

function AppContent() {
  const { currentPage, isAuthenticated, user, settings } =
    useAppStore();

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    if (settings.theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [settings.theme]);

  // If not authenticated, show login page
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

  // Administrator portal (existing functionality)
  if (user?.role === "administrator") {
    const renderPage = () => {
      switch (currentPage) {
        case "dashboard":
          return <Dashboard />;
        case "scheduling":
          return <Scheduling />;
        case "timetable":
          return <Timetable />;
        case "constraints":
          return <Constraints />;
        case "scenarios":
          return <Scenarios />;
        case "analytics":
          return <Analytics />;
        case "session-setup":
          return <SessionSetup />;
        case "user-management":
          return <UserManagement />;
        case "notifications":
          return <Notifications />;
        case "history":
          return <History />;
        default:
          return <Dashboard />;
      }
    };

    return <Layout>{renderPage()}</Layout>;
  }

  // Fallback to login if role is not recognized
  return <Login />;
}

export default function App() {
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