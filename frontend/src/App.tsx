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
      {/* --- FIX START --- */}
      {/* Updated toast styles to be more vibrant and integrated with the app theme. */}
      {/* Uses a colored accent border and matching icon/title colors. */}
      <Toaster
      position="top-right"
      offset={64} // distance from top bar; tweak as needed
      toastOptions={{
        style: {
          zIndex: 99999, // forces it above modals, navbars, etc.
        },
        classNames: {
          toast:
            "group toast w-full md:max-w-md group-[.toaster]:bg-card group-[.toaster]:text-card-foreground group-[.toaster]:shadow-xl group-[.toaster]:p-4 border-l-4",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
          success:
            "!border-l-green-600 dark:!border-l-green-500 !text-green-700 dark:!text-green-400",
          error: "!border-l-destructive !text-destructive",
          info:
            "!border-l-blue-600 dark:!border-l-blue-500 !text-blue-700 dark:!text-blue-400",
          icon:
            "group-[.toast.success]:text-green-600 group-[.toast.error]:text-destructive group-[.toast.info]:text-blue-600",
        },
      }}
    />
      {/* --- FIX END --- */}
    </>
  );
}