import { VALIDATION_PATTERNS, UPLOAD_CONFIG } from './constants';

// Types for validation results
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface FileValidationResult extends ValidationResult {
  fileSize: number;
  fileName: string;
  fileType: string;
}

// General validation utilities
export const isRequired = (value: any): boolean => {
  return value !== null && value !== undefined && value !== '';
};

export const isEmail = (email: string): boolean => {
  return VALIDATION_PATTERNS.EMAIL.test(email);
};

export const isPhoneNumber = (phone: string): boolean => {
  return VALIDATION_PATTERNS.PHONE.test(phone);
};

// Academic data validation
export const isValidStudentId = (studentId: string): boolean => {
  return VALIDATION_PATTERNS.STUDENT_ID.test(studentId);
};

export const isValidCourseCode = (courseCode: string): boolean => {
  return VALIDATION_PATTERNS.COURSE_CODE.test(courseCode);
};

export const isValidRoomCode = (roomCode: string): boolean => {
  return VALIDATION_PATTERNS.ROOM_CODE.test(roomCode);
};

// Date and time validation
export const isValidDate = (date: string): boolean => {
  const dateObj = new Date(date);
  return !isNaN(dateObj.getTime());
};

export const isValidTimeSlot = (time: string): boolean => {
  const timeRegex = /^([0-1][0-9]|2[0-3]):[0-5][0-9]$/;
  return timeRegex.test(time);
};

export const isValidDateRange = (startDate: string, endDate: string): boolean => {
  const start = new Date(startDate);
  const end = new Date(endDate);
  return start < end;
};

// Numeric validation
export const isPositiveInteger = (value: number): boolean => {
  return Number.isInteger(value) && value > 0;
};

export const isValidCapacity = (capacity: number): boolean => {
  return isPositiveInteger(capacity) && capacity <= 1000;
};

export const isValidGPA = (gpa: number): boolean => {
  return gpa >= 0 && gpa <= 4.0;
};

export const isValidPercentage = (value: number): boolean => {
  return value >= 0 && value <= 100;
};

// File validation
export const validateFile = (file: File): FileValidationResult => {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check file size
  if (file.size > UPLOAD_CONFIG.MAX_FILE_SIZE) {
    errors.push(`File size exceeds maximum limit of ${UPLOAD_CONFIG.MAX_FILE_SIZE / (1024 * 1024)}MB`);
  }

  // Check file format
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!UPLOAD_CONFIG.ACCEPTED_FORMATS.includes(fileExtension)) {
    errors.push(`File format not supported. Accepted formats: ${UPLOAD_CONFIG.ACCEPTED_FORMATS.join(', ')}`);
  }

  // Check if it's a required file
  const fileName = file.name.toLowerCase();
  const isRequired = UPLOAD_CONFIG.REQUIRED_FILES.some(required => 
    fileName.includes(required.replace('.csv', ''))
  );

  if (!isRequired) {
    warnings.push('This file is optional and may not be processed');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    fileSize: file.size,
    fileName: file.name,
    fileType: file.type,
  };
};

// CSV data validation
export interface CSVValidationRule {
  field: string;
  required: boolean;
  type: 'string' | 'number' | 'email' | 'date';
  validator?: (value: any) => boolean;
  errorMessage?: string;
}

export const validateCSVRow = (
  row: Record<string, any>,
  rules: CSVValidationRule[],
  rowIndex: number
): ValidationResult => {
  const errors: string[] = [];
  const warnings: string[] = [];

  for (const rule of rules) {
    const value = row[rule.field];

    // Check required fields
    if (rule.required && !isRequired(value)) {
      errors.push(`Row ${rowIndex}: Missing required field '${rule.field}'`);
      continue;
    }

    // Skip validation if field is not required and empty
    if (!rule.required && !isRequired(value)) {
      continue;
    }

    // Type validation
    switch (rule.type) {
      case 'number':
        if (isNaN(Number(value))) {
          errors.push(`Row ${rowIndex}: '${rule.field}' must be a number`);
        }
        break;
      case 'email':
        if (!isEmail(value)) {
          errors.push(`Row ${rowIndex}: '${rule.field}' must be a valid email`);
        }
        break;
      case 'date':
        if (!isValidDate(value)) {
          errors.push(`Row ${rowIndex}: '${rule.field}' must be a valid date`);
        }
        break;
    }

    // Custom validator
    if (rule.validator && !rule.validator(value)) {
      const message = rule.errorMessage || `Row ${rowIndex}: '${rule.field}' is invalid`;
      errors.push(message);
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
};

// Predefined CSV validation rules
export const STUDENT_CSV_RULES: CSVValidationRule[] = [
  { field: 'studentId', required: true, type: 'string', validator: isValidStudentId },
  { field: 'firstName', required: true, type: 'string' },
  { field: 'lastName', required: true, type: 'string' },
  { field: 'email', required: true, type: 'email' },
  { field: 'programme', required: true, type: 'string' },
  { field: 'level', required: true, type: 'number', validator: (v) => [100, 200, 300, 400, 500].includes(Number(v)) },
];

export const COURSE_CSV_RULES: CSVValidationRule[] = [
  { field: 'courseCode', required: true, type: 'string', validator: isValidCourseCode },
  { field: 'title', required: true, type: 'string' },
  { field: 'units', required: true, type: 'number', validator: (v) => Number(v) >= 1 && Number(v) <= 6 },
  { field: 'level', required: true, type: 'number', validator: (v) => [100, 200, 300, 400, 500].includes(Number(v)) },
  { field: 'semester', required: true, type: 'string', validator: (v) => ['1', '2', 'first', 'second'].includes(v.toLowerCase()) },
];

export const ROOM_CSV_RULES: CSVValidationRule[] = [
  { field: 'roomCode', required: true, type: 'string', validator: isValidRoomCode },
  { field: 'building', required: true, type: 'string' },
  { field: 'capacity', required: true, type: 'number', validator: isValidCapacity },
  { field: 'type', required: false, type: 'string' },
  { field: 'facilities', required: false, type: 'string' },
];

export const REGISTRATION_CSV_RULES: CSVValidationRule[] = [
  { field: 'studentId', required: true, type: 'string', validator: isValidStudentId },
  { field: 'courseCode', required: true, type: 'string', validator: isValidCourseCode },
  { field: 'semester', required: true, type: 'string' },
  { field: 'academicYear', required: true, type: 'string' },
];

// Constraint validation
export interface ConstraintValidation {
  name: string;
  weight: number;
  enabled: boolean;
}

export const validateConstraints = (constraints: ConstraintValidation[]): ValidationResult => {
  const errors: string[] = [];
  const warnings: string[] = [];

  for (const constraint of constraints) {
    if (!constraint.name || constraint.name.trim() === '') {
      errors.push('Constraint name cannot be empty');
    }

    if (constraint.weight < 0 || constraint.weight > 1) {
      errors.push(`Constraint '${constraint.name}' weight must be between 0 and 1`);
    }

    if (constraint.weight === 0 && constraint.enabled) {
      warnings.push(`Constraint '${constraint.name}' is enabled but has zero weight`);
    }
  }

  const enabledConstraints = constraints.filter(c => c.enabled);
  if (enabledConstraints.length === 0) {
    warnings.push('No constraints are enabled');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
};

// Schedule validation
export interface ExamSlot {
  examId: string;
  courseCode: string;
  roomCode: string;
  date: string;
  timeSlot: string;
  duration: number;
  students: string[];
}

export const validateSchedule = (schedule: ExamSlot[]): ValidationResult => {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check for room conflicts
  const roomSchedule = new Map<string, ExamSlot[]>();
  schedule.forEach(slot => {
    const key = `${slot.roomCode}-${slot.date}-${slot.timeSlot}`;
    if (!roomSchedule.has(key)) {
      roomSchedule.set(key, []);
    }
    roomSchedule.get(key)!.push(slot);
  });

  roomSchedule.forEach((slots, key) => {
    if (slots.length > 1) {
      errors.push(`Room conflict detected: ${key} has multiple exams scheduled`);
    }
  });

  // Check for student conflicts
  const studentSchedule = new Map<string, ExamSlot[]>();
  schedule.forEach(slot => {
    slot.students.forEach(studentId => {
      const key = `${studentId}-${slot.date}-${slot.timeSlot}`;
      if (!studentSchedule.has(key)) {
        studentSchedule.set(key, []);
      }
      studentSchedule.get(key)!.push(slot);
    });
  });

  studentSchedule.forEach((slots, key) => {
    if (slots.length > 1) {
      const [studentId] = key.split('-');
      errors.push(`Student conflict detected: ${studentId} has multiple exams at the same time`);
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  };
};

// Form validation helpers
export const createValidator = (rules: { [key: string]: (value: any) => string | null }) => {
  return (data: Record<string, any>) => {
    const errors: Record<string, string> = {};
    
    Object.keys(rules).forEach(field => {
      const value = data[field];
      const error = rules[field](value);
      if (error) {
        errors[field] = error;
      }
    });

    return {
      isValid: Object.keys(errors).length === 0,
      errors,
    };
  };
};