import React, { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { 
  Search, 
  Calendar, 
  MapPin, 
  Users, 
  Clock, 
  Book,
  GraduationCap,
  UserCheck,
  ArrowRight
} from 'lucide-react';
import { useAppStore } from '../store';
import { Exam, User } from '../store/types';

interface SearchResult {
  id: string;
  type: 'exam' | 'course' | 'room' | 'student' | 'staff';
  title: string;
  subtitle?: string;
  description?: string;
  data: any;
}

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (page: string, itemId?: string) => void;
}

export function GlobalSearch({ isOpen, onClose, onNavigate }: GlobalSearchProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const { exams, setCurrentPage } = useAppStore();

  // Mock data for students and staff - in real app this would come from the store
  const mockStudents = [
    { id: 'std001', name: 'John Smith', studentId: 'S12345', department: 'Computer Science' },
    { id: 'std002', name: 'Emma Johnson', studentId: 'S12346', department: 'Mathematics' },
    { id: 'std003', name: 'Michael Brown', studentId: 'S12347', department: 'Physics' }
  ];

  const mockStaff = [
    { id: 'stf001', name: 'Dr. Sarah Wilson', staffId: 'F001', department: 'Computer Science', role: 'Professor' },
    { id: 'stf002', name: 'Prof. David Lee', staffId: 'F002', department: 'Mathematics', role: 'Professor' },
    { id: 'stf003', name: 'Dr. Lisa Chen', staffId: 'F003', department: 'Physics', role: 'Associate Professor' }
  ];

  const searchResults = useMemo(() => {
    if (!searchTerm.trim()) return [];

    const term = searchTerm.toLowerCase();
    const results: SearchResult[] = [];
    const safeExams = exams || [];

    // Search exams
    safeExams.forEach(exam => {
      if (
        exam.courseCode.toLowerCase().includes(term) ||
        exam.courseName.toLowerCase().includes(term) ||
        exam.room.toLowerCase().includes(term) ||
        exam.building.toLowerCase().includes(term) ||
        exam.invigilator.toLowerCase().includes(term) ||
        exam.departments.some(dept => dept.toLowerCase().includes(term))
      ) {
        results.push({
          id: exam.id,
          type: 'exam',
          title: `${exam.courseCode} - ${exam.courseName}`,
          subtitle: `${exam.date} at ${exam.startTime}`,
          description: `${exam.room}, ${exam.building} • ${exam.expectedStudents} students`,
          data: exam
        });
      }
    });

    // Search courses (extract unique courses from exams)
    const uniqueCourses = new Map();
    safeExams.forEach(exam => {
      const key = exam.courseCode;
      if (!uniqueCourses.has(key) && 
          (exam.courseCode.toLowerCase().includes(term) || 
           exam.courseName.toLowerCase().includes(term))) {
        uniqueCourses.set(key, {
          id: exam.courseCode,
          type: 'course',
          title: exam.courseCode,
          subtitle: exam.courseName,
          description: `${exam.departments.join(', ')} • ${exam.semester} ${exam.academicYear}`,
          data: exam
        });
      }
    });
    results.push(...uniqueCourses.values());

    // Search rooms
    const uniqueRooms = new Map();
    safeExams.forEach(exam => {
      const key = exam.room;
      if (!uniqueRooms.has(key) && 
          (exam.room.toLowerCase().includes(term) || 
           exam.building.toLowerCase().includes(term))) {
        const roomExams = safeExams.filter(e => e.room === exam.room);
        uniqueRooms.set(key, {
          id: exam.room,
          type: 'room',
          title: exam.room,
          subtitle: exam.building,
          description: `Capacity: ${exam.roomCapacity} • ${roomExams.length} scheduled exams`,
          data: { room: exam.room, building: exam.building, capacity: exam.roomCapacity, exams: roomExams }
        });
      }
    });
    results.push(...uniqueRooms.values());

    // Search students
    mockStudents.forEach(student => {
      if (
        student.name.toLowerCase().includes(term) ||
        student.studentId.toLowerCase().includes(term) ||
        student.department.toLowerCase().includes(term)
      ) {
        results.push({
          id: student.id,
          type: 'student',
          title: student.name,
          subtitle: `Student ID: ${student.studentId}`,
          description: student.department,
          data: student
        });
      }
    });

    // Search staff
    mockStaff.forEach(staff => {
      if (
        staff.name.toLowerCase().includes(term) ||
        staff.staffId.toLowerCase().includes(term) ||
        staff.department.toLowerCase().includes(term) ||
        staff.role.toLowerCase().includes(term)
      ) {
        results.push({
          id: staff.id,
          type: 'staff',
          title: staff.name,
          subtitle: `${staff.role} • ${staff.staffId}`,
          description: staff.department,
          data: staff
        });
      }
    });

    return results.slice(0, 20); // Limit results
  }, [searchTerm, exams]);

  const groupedResults = useMemo(() => {
    const groups: Record<string, SearchResult[]> = {
      exam: [],
      course: [],
      room: [],
      student: [],
      staff: []
    };

    searchResults.forEach(result => {
      groups[result.type].push(result);
    });

    return Object.entries(groups).filter(([_, items]) => items.length > 0);
  }, [searchResults]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [searchTerm]);

  useEffect(() => {
    if (!isOpen) {
      setSearchTerm('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, searchResults.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (searchResults[selectedIndex]) {
          handleSelectResult(searchResults[selectedIndex]);
        }
        break;
      case 'Escape':
        onClose();
        break;
    }
  };

  const handleSelectResult = (result: SearchResult) => {
    switch (result.type) {
      case 'exam':
        setCurrentPage('timetable');
        // In a real app, you'd scroll to or highlight the specific exam
        break;
      case 'course':
        setCurrentPage('timetable');
        break;
      case 'room':
        setCurrentPage('timetable');
        break;
      case 'student':
        setCurrentPage('user-management');
        break;
      case 'staff':
        setCurrentPage('user-management');
        break;
    }
    onClose();
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'exam': return Calendar;
      case 'course': return Book;
      case 'room': return MapPin;
      case 'student': return GraduationCap;
      case 'staff': return UserCheck;
      default: return Search;
    }
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'exam': return 'Exams';
      case 'course': return 'Courses';
      case 'room': return 'Rooms';
      case 'student': return 'Students';
      case 'staff': return 'Staff';
      default: return 'Results';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] p-0">
        <DialogHeader className="p-6 pb-2">
          <DialogTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Global Search
          </DialogTitle>
          <DialogDescription>
            Search across all exams, courses, rooms, students, and staff. Use keyboard arrows to navigate and Enter to select.
          </DialogDescription>
        </DialogHeader>
        
        <div className="px-6">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
            <Input
              placeholder="Search exams, courses, rooms, students, staff..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={handleKeyDown}
              className="pl-9"
              autoFocus
            />
          </div>
        </div>

        <ScrollArea className="max-h-96 px-6 pb-6">
          {searchTerm.trim() === '' ? (
            <div className="text-center py-8 text-muted-foreground">
              <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Start typing to search across all data...</p>
              <div className="text-sm mt-2">
                <p>Use <kbd className="px-1.5 py-0.5 text-xs bg-muted rounded">↑</kbd> <kbd className="px-1.5 py-0.5 text-xs bg-muted rounded">↓</kbd> to navigate</p>
                <p><kbd className="px-1.5 py-0.5 text-xs bg-muted rounded">Enter</kbd> to select</p>
              </div>
            </div>
          ) : searchResults.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No results found for "{searchTerm}"</p>
            </div>
          ) : (
            <div className="space-y-4">
              {groupedResults.map(([type, items], groupIndex) => {
                const Icon = getTypeIcon(type);
                const cumulativePreviousItems = groupedResults
                  .slice(0, groupIndex)
                  .reduce((sum, [_, groupItems]) => sum + groupItems.length, 0);

                return (
                  <div key={type}>
                    <div className="flex items-center gap-2 mb-3">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <h4 className="font-medium">{getTypeLabel(type)}</h4>
                      <Badge variant="secondary">{items.length}</Badge>
                    </div>
                    <div className="space-y-1">
                      {items.map((result, index) => {
                        const globalIndex = cumulativePreviousItems + index;
                        const isSelected = globalIndex === selectedIndex;
                        
                        return (
                          <Button
                            key={result.id}
                            variant="ghost"
                            className={`w-full justify-start h-auto p-3 ${
                              isSelected ? 'bg-muted' : ''
                            }`}
                            onClick={() => handleSelectResult(result)}
                          >
                            <div className="flex items-center gap-3 w-full">
                              <Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                              <div className="flex-1 text-left">
                                <p className="font-medium">{result.title}</p>
                                {result.subtitle && (
                                  <p className="text-sm text-muted-foreground">{result.subtitle}</p>
                                )}
                                {result.description && (
                                  <p className="text-xs text-muted-foreground">{result.description}</p>
                                )}
                              </div>
                              <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                            </div>
                          </Button>
                        );
                      })}
                    </div>
                    {groupIndex < groupedResults.length - 1 && <Separator className="mt-3" />}
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}