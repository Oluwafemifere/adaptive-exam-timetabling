// frontend/src/utils/timetableUtils.ts

// Convert an ISO datetime string to a time slot index (0-8 representing 9am-5pm)
export function getTimeSlot(timeString: string): number {
  console.log(`[timetableUtils:getTimeSlot] Received time string: ${timeString}`);
  if (!timeString) {
    console.warn("[timetableUtils:getTimeSlot] Input string is empty or null. Returning default slot 0.");
    return 0;
  }
  // FIX: To reliably parse a time string like "09:00:00", it must be combined
  // with a dummy date and a 'Z' suffix to be correctly parsed as a UTC date.
  const date = new Date(`1970-01-01T${timeString}Z`);
  if (isNaN(date.getTime())) {
    console.error(`[timetableUtils:getTimeSlot] Invalid date created from string: ${timeString}. Returning default slot 0.`);
    return 0;
  }
  
  // Use getUTCHours on a UTC date to get the correct hour value.
  const hours = date.getUTCHours();
  console.log(`[timetableUtils:getTimeSlot] Extracted hours: ${hours}`);
  
  // The grid starts at 9 AM, so subtract 9 to get the 0-based index.
  const slot = Math.max(0, hours - 9);
  console.log(`[timetableUtils:getTimeSlot] Calculated time slot index: ${slot}`);
  return slot;
}

// Generate consistent colors for departments (dark mode friendly)
export function generateDepartmentColors(departments: string[]): Record<string, string> {
  console.log("[timetableUtils:generateDepartmentColors] Generating colors for departments:", departments);
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
  
  // Create a unique, sorted list of departments to ensure consistent color assignment
  const uniqueDepartments = [...new Set(departments)].sort();
  console.log("[timetableUtils:generateDepartmentColors] Unique sorted departments:", uniqueDepartments);

  uniqueDepartments.forEach((dept, index) => {
    const color = darkModeColors[index % darkModeColors.length];
    colors[dept] = color;
    console.log(`[timetableUtils:generateDepartmentColors] Assigning color ${color} to department "${dept}"`);
  });
  
  console.log("[timetableUtils:generateDepartmentColors] Final color mapping:", colors);
  return colors;
}

// Generate distinct colors for individual exams in department view
export function generateDistinctColors(count: number): Record<number, string> {
  console.log(`[timetableUtils:generateDistinctColors] Generating ${count} distinct colors.`);
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
  
  console.log(`[timetableUtils:generateDistinctColors] Generated color map for ${count} items:`, colors);
  return colors;
}

// Calculate exam duration in hours from two ISO datetime strings
export function calculateDuration(startTime: string, endTime: string): number {
  console.log(`[timetableUtils:calculateDuration] Calculating duration between startTime: ${startTime} and endTime: ${endTime}`);
  if (!startTime || !endTime) {
    console.warn("[timetableUtils:calculateDuration] startTime or endTime is missing. Returning 0.");
    return 0;
  }
  // FIX: Reliably parse time-only strings by combining them with a dummy date
  // and a 'Z' suffix to parse them as UTC, avoiding timezone issues.
  const start = new Date(`1970-01-01T${startTime}Z`);
  const end = new Date(`1970-01-01T${endTime}Z`);

  if (isNaN(start.getTime()) || isNaN(end.getTime())) {
    console.error("[timetableUtils:calculateDuration] Invalid date created from start or end time. Returning 0.");
    return 0;
  }

  // Difference in milliseconds, convert to hours
  const durationInHours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);
  console.log(`[timetableUtils:calculateDuration] Calculated duration: ${durationInHours} hours.`);
  return durationInHours;
}


// Format a time string (e.g., "HH:mm:ss") for display
export function formatTime(timeString: string): string {
  console.log(`[timetableUtils:formatTime] Formatting time string: ${timeString}`);
  if (!timeString) {
    console.warn("[timetableUtils:formatTime] Input string is empty or null. Returning 'N/A'.");
    return 'N/A';
  }
  // Prepend a dummy date to the time string to create a valid Date object for parsing.
  // This is a robust way to handle time-only strings.
  const date = new Date(`1970-01-01T${timeString}`);
  if (isNaN(date.getTime())) {
    console.error(`[timetableUtils:formatTime] Invalid date created from string: ${timeString}. Returning 'N/A'.`);
    return 'N/A';
  }

  const formattedTime = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
  console.log(`[timetableUtils:formatTime] Formatted time: ${formattedTime}`);
  return formattedTime;
}

// Calculate room utilization percentage
export function calculateUtilization(expectedStudents: number, roomCapacity: number): number {
  console.log(`[timetableUtils:calculateUtilization] Calculating utilization for ${expectedStudents} students in a room with capacity ${roomCapacity}.`);
  if (!roomCapacity || roomCapacity === 0) {
    console.warn("[timetableUtils:calculateUtilization] Room capacity is 0 or undefined. Returning 0 to avoid division by zero.");
    return 0; // Avoid division by zero
  }
  const utilization = Math.round((expectedStudents / roomCapacity) * 100);
  console.log(`[timetableUtils:calculateUtilization] Calculated utilization: ${utilization}%`);
  return utilization;
}

// Get color class based on utilization percentage
export function getUtilizationColorClass(percentage: number): string {
  console.log(`[timetableUtils:getUtilizationColorClass] Getting color for utilization: ${percentage}%`);
  if (percentage > 100) {
    console.log("[timetableUtils:getUtilizationColorClass] Over capacity. Returning 'text-red-600 font-bold'.");
    return 'text-red-600 font-bold'; // Over capacity
  }
  if (percentage >= 90) {
    console.log("[timetableUtils:getUtilizationColorClass] High utilization (>=90%). Returning 'text-red-500'.");
    return 'text-red-500';
  }
  if (percentage >= 75) {
    console.log("[timetableUtils:getUtilizationColorClass] Medium utilization (>=75%). Returning 'text-yellow-500'.");
    return 'text-yellow-500';
  }
  console.log("[timetableUtils:getUtilizationColorClass] Low utilization (<75%). Returning 'text-green-500'.");
  return 'text-green-500';
}