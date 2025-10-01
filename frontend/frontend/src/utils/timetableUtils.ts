// frontend\frontend\src\utils\timetableUtils.ts
/**
 * Calculates the starting time slot index for an exam.
 * Assumes time slots start at 9:00 and are hourly.
 * @param time The start time of the exam in "HH:MM" format.
 * @returns A 0-indexed integer for the time slot.
 */
export const getTimeSlot = (time: string): number => {
  try {
    const hour = parseInt(time.split(':')[0]);
    // Assuming the grid starts at 9 AM (slot 0)
    return Math.max(0, hour - 9);
  } catch {
    return 0;
  }
};

/**
 * Calculates the duration of an exam in hours.
 * @param startTime The start time in "HH:MM" format.
 * @param endTime The end time in "HH:MM" format.
 * @returns The duration in hours.
 */
export const calculateDuration = (startTime: string, endTime: string): number => {
  try {
    const start = new Date(`1970-01-01T${startTime}:00`);
    const end = new Date(`1970-01-01T${endTime}:00`);
    const durationMs = end.getTime() - start.getTime();
    return durationMs / (1000 * 60 * 60);
  } catch {
    return 1; // Default to 1 hour if parsing fails
  }
};

/**
 * Generates a map of department names to visually distinct colors.
 * @param departments An array of department name strings.
 * @returns An object where keys are department names and values are color strings.
 */
export const generateDepartmentColors = (departments: string[]): Record<string, string> => {
  const colors: Record<string, string> = {};
  const hueStep = 360 / departments.length;
  
  departments.forEach((dept, index) => {
    // Using HSL for better color distribution
    const hue = index * hueStep;
    colors[dept] = `hsl(${hue}, 70%, 50%)`;
  });
  
  return colors;
};

/**
 * Generates an array of visually distinct colors.
 * @param count The number of distinct colors to generate.
 * @returns An array of color strings.
 */
export const generateDistinctColors = (count: number): string[] => {
  const colors: string[] = [];
  const hueStep = 360 / count;

  for (let i = 0; i < count; i++) {
    const hue = i * hueStep;
    colors.push(`hsl(${hue}, 65%, 55%)`);
  }
  
  return colors;
};