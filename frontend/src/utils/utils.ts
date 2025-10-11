// frontend\src\utils\utils.ts
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Formats a snake_case or camelCase string into a capitalized, space-separated title.
 * Example: 'course_instructors' becomes 'Course Instructors'.
 * @param header The string to format.
 * @returns A formatted, human-readable string.
 */
export function formatHeader(header: string): string {
  if (!header) return '';
  return header
    // Replace underscores with spaces
    .replace(/_/g, ' ')
    // Insert a space before capital letters (for camelCase)
    .replace(/([A-Z])/g, ' $1')
    // Capitalize the first letter of each word
    .replace(/\b\w/g, char => char.toUpperCase())
    // Trim any leading/trailing spaces
    .trim();
};