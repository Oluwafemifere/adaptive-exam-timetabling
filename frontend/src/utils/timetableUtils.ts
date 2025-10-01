// Convert time string to time slot index (0-8 for 9:00-17:00)
export function getTimeSlot(timeString: string): number {
  const [hours] = timeString.split(':').map(Number);
  return Math.max(0, Math.min(8, hours - 9));
}

// Generate consistent colors for departments (dark mode friendly)
export function generateDepartmentColors(departments: string[]): Record<string, string> {
  const darkModeColors = [
    '#3b82f6', // blue
    '#10b981', // emerald
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // violet
    '#06b6d4', // cyan
    '#84cc16', // lime
    '#f97316', // orange
    '#ec4899', // pink
    '#6366f1', // indigo
    '#14b8a6', // teal
    '#eab308', // yellow
  ];

  const colors: Record<string, string> = {};
  
  departments.forEach((dept, index) => {
    colors[dept] = darkModeColors[index % darkModeColors.length];
  });
  
  return colors;
}

// Generate distinct colors for individual exams in department view
export function generateDistinctColors(count: number): Record<number, string> {
  const distinctColors = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1',
    '#14b8a6', '#eab308', '#64748b', '#dc2626', '#7c3aed',
    '#059669', '#d97706', '#be123c', '#7c2d12', '#365314'
  ];

  const colors: Record<number, string> = {};
  
  for (let i = 0; i < count; i++) {
    colors[i] = distinctColors[i % distinctColors.length];
  }
  
  return colors;
}

// Calculate exam duration in hours
export function calculateDuration(startTime: string, endTime: string): number {
  const start = new Date(`1970-01-01T${startTime}:00`);
  const end = new Date(`1970-01-01T${endTime}:00`);
  return (end.getTime() - start.getTime()) / (1000 * 60 * 60);
}

// Format time for display
export function formatTime(time: string): string {
  const [hours, minutes] = time.split(':');
  const hour = parseInt(hours);
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${displayHour}:${minutes} ${ampm}`;
}

// Calculate room utilization percentage
export function calculateUtilization(expectedStudents: number, roomCapacity: number): number {
  return Math.round((expectedStudents / roomCapacity) * 100);
}

// Get color class based on utilization percentage
export function getUtilizationColorClass(percentage: number): string {
  if (percentage >= 90) return 'text-red-500';
  if (percentage >= 75) return 'text-yellow-500';
  return 'text-green-500';
}