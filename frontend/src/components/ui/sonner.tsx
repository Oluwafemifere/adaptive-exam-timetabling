"use client";

import { useTheme } from "next-themes";
import { Toaster as Sonner, ToasterProps } from "sonner";

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      position="bottom-right"
      toastOptions={{
        // --- FIX START ---
        // Enhanced styles for better readability, size, and color-coding based on action.
        classNames: {
          toast:
            "group toast w-full md:max-w-md group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border group-[.toaster]:shadow-xl group-[.toaster]:p-4 text-sm",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
          
          // Added prominent background colors and stronger border/text colors for each type.
          success:
            "!bg-green-50 dark:!bg-green-950/60 !border-green-300 dark:!border-green-700 !text-green-800 dark:!text-green-200",
          error:
            "!bg-red-50 dark:!bg-red-950/60 !border-red-300 dark:!border-red-700 !text-red-800 dark:!text-red-200",
          info:
            "!bg-blue-50 dark:!bg-blue-950/60 !border-blue-300 dark:!border-blue-700 !text-blue-800 dark:!text-blue-200",
          
          // Ensure icons match the toast type color.
          icon: "group-[.toast.success]:text-green-600 group-[.toast.error]:text-red-600 group-[.toast.info]:text-blue-600",
        },
        // --- FIX END ---
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };