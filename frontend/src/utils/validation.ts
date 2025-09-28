import { format, parseISO, isValid } from 'date-fns';

// Date formatting utilities
export const formatDate = (date: string | Date, pattern: string = 'PPP'): string => {
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    if (!isValid(dateObj)) return 'Invalid Date';
    return format(dateObj, pattern);
  } catch {
    return 'Invalid Date';
  }
};

export const formatTime = (time: string): string => {
  const [hours, minutes] = time.split(':');
  const hour = parseInt(hours, 10);
  const period = hour >= 12 ? 'PM' : 'AM';
  const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${displayHour}:${minutes} ${period}`;
};

// Number formatting utilities
export const formatPercentage = (value: number, decimals: number = 1): string => {
  return `${(value * 100).toFixed(decimals)}%`;
};

export const formatDuration = (minutes: number): string => {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  
  if (hours === 0) return `${mins}min`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}min`;
};

export const formatFileSize = (bytes: number): string => {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(1)} ${units[unitIndex]}`;
};

// String formatting utilities
export const formatStudentId = (id: string): string => {
  return id.toUpperCase().replace(/[^A-Z0-9]/g, '');
};

export const formatCourseCode = (code: string): string => {
  return code.toUpperCase().replace(/\s+/g, ' ').trim();
};

export const formatRoomCode = (code: string): string => {
  return code.toUpperCase().replace(/[^A-Z0-9\-]/g, '');
};

// Name formatting utilities
export const formatName = (firstName: string, lastName: string): string => {
  return `${firstName.trim()} ${lastName.trim()}`.trim();
};

export const formatInitials = (name: string): string => {
  return name
    .split(' ')
    .map(part => part.charAt(0).toUpperCase())
    .join('');
};

// Status formatting utilities
export const formatStatus = (status: string): string => {
  return status
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

// Capacity formatting utilities
export const formatCapacity = (current: number, total: number): string => {
  const percentage = (current / total) * 100;
  return `${current}/${total} (${percentage.toFixed(0)}%)`;
};

// Conflict formatting utilities
export const formatConflictSeverity = (severity: string): string => {
  const severityMap = {
    critical: 'Critical',
    high: 'High Priority',
    medium: 'Medium Priority',
    low: 'Low Priority',
  };
  return severityMap[severity as keyof typeof severityMap] || severity;
};

// Phone number formatting
export const formatPhoneNumber = (phone: string): string => {
  const cleaned = phone.replace(/\D/g, '');
  if (cleaned.length === 11 && cleaned.startsWith('0')) {
    return `${cleaned.slice(0, 4)} ${cleaned.slice(4, 7)} ${cleaned.slice(7)}`;
  }
  if (cleaned.length === 10) {
    return `${cleaned.slice(0, 3)} ${cleaned.slice(3, 6)} ${cleaned.slice(6)}`;
  }
  return phone;
};

// Currency formatting (for Nigerian context)
export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
};

// Address formatting
export const formatAddress = (address: {
  street?: string;
  city?: string;
  state?: string;
  country?: string;
}): string => {
  const parts = [address.street, address.city, address.state, address.country]
    .filter(Boolean)
    .map(part => part?.trim());
  return parts.join(', ');
};

// Grade formatting
export const formatGrade = (score: number): string => {
  if (score >= 70) return 'A';
  if (score >= 60) return 'B';
  if (score >= 50) return 'C';
  if (score >= 45) return 'D';
  if (score >= 40) return 'E';
  return 'F';
};

// GPA formatting
export const formatGPA = (gpa: number): string => {
  return gpa.toFixed(2);
};

// Semester formatting
export const formatSemester = (semester: string, year: string): string => {
  const semesterMap = {
    '1': 'First',
    '2': 'Second',
    '3': 'Third',
  };
  const semesterName = semesterMap[semester as keyof typeof semesterMap] || semester;
  return `${semesterName} Semester ${year}`;
};

// Academic year formatting
export const formatAcademicYear = (year: string): string => {
  const currentYear = parseInt(year);
  const nextYear = currentYear + 1;
  return `${currentYear}/${nextYear.toString().slice(-2)}`;
};

// Truncate text with ellipsis
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
};

// Capitalize first letter
export const capitalize = (text: string): string => {
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
};

// Convert to title case
export const toTitleCase = (text: string): string => {
  return text
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};