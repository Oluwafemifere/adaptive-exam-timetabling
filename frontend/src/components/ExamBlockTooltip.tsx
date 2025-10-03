// frontend/src/components/ExamBlockTooltip.tsx
import { RenderableExam } from '../store/types';
import { Badge } from './ui/badge';
import { Clock, Users, MapPin, User, FileText, Building, UserCheck, Calendar } from 'lucide-react';
import { formatTime } from '../utils/timetableUtils';

interface ExamBlockTooltipProps {
  exam: RenderableExam;
}

export function ExamBlockTooltip({ exam }: ExamBlockTooltipProps) {

  // Helper function to calculate room utilization percentage string
  const getUtilization = () => {
    if (!exam.roomCapacity || exam.roomCapacity === 0) return '0%';
    const percentage = Math.round((exam.expectedStudents / exam.roomCapacity) * 100);
    return `${percentage}%`;
  };

  // Helper function to determine the color for the utilization text
  const getUtilizationColor = () => {
    if (!exam.roomCapacity || exam.roomCapacity === 0) return 'text-gray-400';
    const percentage = (exam.expectedStudents / exam.roomCapacity) * 100;
    if (percentage >= 90) return 'text-red-400';
    if (percentage >= 75) return 'text-yellow-400';
    return 'text-green-400';
  };

  // Helper function to get a descriptive label for the room capacity
  const getUtilizationLabel = () => {
    if (!exam.roomCapacity || exam.roomCapacity === 0) return 'Unknown';
    const percentage = (exam.expectedStudents / exam.roomCapacity) * 100;
    if (percentage >= 90) return 'Overbooked';
    if (percentage >= 85) return 'Nearly Full';
    if (percentage >= 75) return 'High Capacity';
    if (percentage >= 50) return 'Moderate';
    return 'Low Capacity';
  };

  // Calculates and formats the exam duration from its start and end times
  const calculateDuration = () => {
    try {
      if (!exam.startTime || !exam.endTime) return 'Unknown';
      const start = new Date(`1970-01-01T${exam.startTime}`);
      const end = new Date(`1970-01-01T${exam.endTime}`);
      const durationMs = end.getTime() - start.getTime();
      if (isNaN(durationMs) || durationMs < 0) return 'Unknown';
      
      const hours = Math.floor(durationMs / (1000 * 60 * 60));
      const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
      
      if (hours > 0 && minutes === 0) return `${hours} hour${hours !== 1 ? 's' : ''}`;
      if (hours > 0 && minutes > 0) return `${hours}h ${minutes}m`;
      if (hours === 0 && minutes > 0) return `${minutes} minutes`;

      return 'Unknown';
    } catch (e) {
      return 'Unknown';
    }
  };
  
  // Formats the date string for display
  const formatDate = () => {
    try {
      if (!exam.date) return 'Invalid Date';
      return new Date(exam.date + 'T00:00:00').toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (e) {
      return exam.date || 'Invalid Date';
    }
  };

  return (
    // FIX: Added `text-card-foreground` to ensure text is visible on the card background in both light and dark modes.
    <div className="space-y-4 max-w-md p-1 text-card-foreground">
      {/* Header: Course Code, Name, and Badges */}
      <div className="border-b border-border pb-3">
        <div className="font-semibold text-base">{exam.courseCode || 'N/A'} - {exam.courseName || 'Unknown Course'}</div>
        <div className="text-sm text-muted-foreground mt-1">{exam.examType || 'N/A'}</div>
        <div className="flex items-center gap-2 mt-2">
          <Badge variant="outline" className="text-xs">
            {calculateDuration()}
          </Badge>
          <Badge 
            variant={
              (!exam.roomCapacity || exam.expectedStudents / exam.roomCapacity >= 0.9) ? "destructive" : 
              exam.expectedStudents / exam.roomCapacity >= 0.75 ? "secondary" : "default"
            } 
            className="text-xs"
          >
            {getUtilizationLabel()}
          </Badge>
        </div>
      </div>
      
      {/* Schedule Information: Date and Time */}
      <div className="space-y-3">
        <div className="flex items-start gap-3">
          <Calendar className="w-4 h-4 text-muted-foreground mt-1" />
          <div>
            <div className="font-medium">{formatDate()}</div>
            <div className="text-sm text-muted-foreground">
              {(exam.startTime && formatTime(exam.startTime)) || 'N/A'} - {(exam.endTime && formatTime(exam.endTime)) || 'N/A'}
            </div>
          </div>
        </div>
        
        <div className="flex items-start gap-3">
          <MapPin className="w-4 h-4 text-muted-foreground mt-1" />
          <div>
            <div className="font-medium">{exam.room || 'N/A'}</div>
            <div className="text-sm text-muted-foreground">{exam.building || 'N/A'}</div>
          </div>
        </div>
      </div>
      
      {/* Personnel: Instructor and Invigilator */}
      <div className="space-y-3">
        <div className="flex items-start gap-3">
          <User className="w-4 h-4 text-muted-foreground mt-1" />
          <div>
            <div className="text-sm text-muted-foreground">Instructor(s)</div>
            <div className="font-medium">{exam.instructor || 'N/A'}</div>
          </div>
        </div>
        
        <div className="flex items-start gap-3">
          <UserCheck className="w-4 h-4 text-muted-foreground mt-1" />
          <div>
            <div className="text-sm text-muted-foreground">Invigilator(s)</div>
            <div className="font-medium">{exam.invigilator || 'N/A'}</div>
          </div>
        </div>
      </div>
      
      {/* Capacity Information: Visual progress bar and student counts */}
      <div className="bg-muted/30 rounded-md p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">Room Capacity</span>
          <span className={`font-semibold ${getUtilizationColor()}`}>
            {getUtilization()}
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Users className="w-4 h-4" />
          <span>
            <span className="font-medium">{exam.expectedStudents || 0}</span> expected students
            <span className="text-muted-foreground"> of {exam.roomCapacity || 0} capacity</span>
          </span>
        </div>
        <div className="w-full bg-muted mt-2 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all ${getUtilizationColor().replace('text-', 'bg-')}`}
            style={{ width: `${Math.min(100, (exam.expectedStudents && exam.roomCapacity) ? (exam.expectedStudents / exam.roomCapacity) * 100 : 0)}%` }}
          />
        </div>
      </div>
      
      {/* Departments */}
      <div>
        <div className="text-sm font-medium mb-2">Departments</div>
        <div className="flex flex-wrap gap-1">
          {(exam.departments || []).map(dept => (
            <Badge key={dept} variant="secondary" className="text-xs">
              {dept}
            </Badge>
          ))}
        </div>
      </div>
      
      {/* Conflicts: Displayed only if there are conflicts */}
      {exam.conflicts && exam.conflicts.length > 0 && (
        <div className="flex items-start gap-3 pt-3 border-t border-border">
          <FileText className="w-4 h-4 mt-1 text-destructive" />
          <div>
            <div className="text-sm font-medium mb-1 text-destructive">Conflicts</div>
            <div className="space-y-1">
              {exam.conflicts.map((conflict, index) => (
                <div key={index} className="text-sm text-destructive">{conflict}</div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      <div className="text-xs text-muted-foreground pt-3 border-t border-border">
        💡 Drag this exam to move it to a different time slot.
      </div>
    </div>
  );
}