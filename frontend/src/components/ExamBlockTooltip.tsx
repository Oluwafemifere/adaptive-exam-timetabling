import { RenderableExam } from '../store/types';
import { Badge } from './ui/badge';
import { Clock, Users, MapPin, User, FileText, Building, UserCheck, Calendar } from 'lucide-react';

interface ExamBlockTooltipProps {
  exam: RenderableExam;
}

export function ExamBlockTooltip({ exam }: ExamBlockTooltipProps) {
  const formatTime = (time: string) => {
    try {
      const [hours, minutes] = time.split(':');
      const hour = parseInt(hours);
      const ampm = hour >= 12 ? 'PM' : 'AM';
      const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
      return `${displayHour}:${minutes} ${ampm}`;
    } catch (e) {
      return time;
    }
  };

  const getUtilization = () => {
    const percentage = Math.round((exam.expectedStudents / exam.roomCapacity) * 100);
    return `${percentage}%`;
  };

  const getUtilizationColor = () => {
    const percentage = (exam.expectedStudents / exam.roomCapacity) * 100;
    if (percentage >= 90) return 'text-red-400';
    if (percentage >= 75) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getUtilizationLabel = () => {
    const percentage = (exam.expectedStudents / exam.roomCapacity) * 100;
    if (percentage >= 90) return 'Overbooked';
    if (percentage >= 85) return 'Nearly Full';
    if (percentage >= 75) return 'High Capacity';
    if (percentage >= 50) return 'Moderate';
    return 'Low Capacity';
  };

  const calculateDuration = () => {
    try {
      const start = new Date(`1970-01-01T${exam.startTime}:00`);
      const end = new Date(`1970-01-01T${exam.endTime}:00`);
      const durationMs = end.getTime() - start.getTime();
      const hours = Math.floor(durationMs / (1000 * 60 * 60));
      const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
      
      if (minutes === 0) return `${hours} hour${hours !== 1 ? 's' : ''}`;
      return `${hours}h ${minutes}m`;
    } catch (e) {
      return 'Duration unknown';
    }
  };

  const formatDate = () => {
    try {
      return new Date(exam.date + 'T00:00:00').toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    } catch (e) {
      return exam.date;
    }
  };

  return (
    <div className="space-y-4 max-w-md">
      {/* Header */}
      <div className="border-b border-border pb-3">
        <div className="font-semibold text-base">{exam.courseCode} - {exam.courseName}</div>
        <div className="text-sm text-muted-foreground mt-1">{exam.examType}</div>
        <div className="flex items-center gap-2 mt-2">
          <Badge variant="outline" className="text-xs">
            {calculateDuration()}
          </Badge>
          <Badge 
            variant={
              exam.expectedStudents / exam.roomCapacity >= 0.9 ? "destructive" : 
              exam.expectedStudents / exam.roomCapacity >= 0.75 ? "secondary" : "default"
            } 
            className="text-xs"
          >
            {getUtilizationLabel()}
          </Badge>
        </div>
      </div>
      
      {/* Schedule Information */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Calendar className="w-4 h-4 text-muted-foreground" />
          <div>
            <div className="font-medium">{formatDate()}</div>
            <div className="text-sm text-muted-foreground">
              {formatTime(exam.startTime)} - {formatTime(exam.endTime)} ({calculateDuration()})
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <MapPin className="w-4 h-4 text-muted-foreground" />
          <div>
            <div className="font-medium">{exam.room}</div>
            <div className="text-sm text-muted-foreground">{exam.building}</div>
          </div>
        </div>
      </div>
      
      {/* Personnel */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <User className="w-4 h-4 text-muted-foreground" />
          <div>
            <div className="text-sm text-muted-foreground">Instructor</div>
            <div className="font-medium">{exam.instructor}</div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <UserCheck className="w-4 h-4 text-muted-foreground" />
          <div>
            <div className="text-sm text-muted-foreground">Invigilator</div>
            <div className="font-medium">{exam.invigilator}</div>
          </div>
        </div>
      </div>
      
      {/* Capacity Information */}
      <div className="bg-muted/20 rounded-md p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">Room Capacity</span>
          <span className={`font-semibold ${getUtilizationColor()}`}>
            {getUtilization()}
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Users className="w-4 h-4" />
          <span>
            <span className="font-medium">{exam.expectedStudents}</span> expected students
            <span className="text-muted-foreground"> of {exam.roomCapacity} capacity</span>
          </span>
        </div>
        <div className="w-full bg-muted mt-2 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all ${
              exam.expectedStudents / exam.roomCapacity >= 0.9 ? 'bg-red-500' :
              exam.expectedStudents / exam.roomCapacity >= 0.75 ? 'bg-yellow-500' : 'bg-green-500'
            }`}
            style={{ width: `${Math.min(100, (exam.expectedStudents / exam.roomCapacity) * 100)}%` }}
          />
        </div>
      </div>
      
      {/* Departments */}
      <div>
        <div className="text-sm font-medium mb-2">Departments</div>
        <div className="flex flex-wrap gap-1">
          {exam.departments.map(dept => (
            <Badge key={dept} variant="secondary" className="text-xs">
              {dept}
            </Badge>
          ))}
        </div>
      </div>
      
      {/* Notes */}
      {exam.notes && (
        <div className="flex items-start gap-3 pt-2 border-t border-border">
          <FileText className="w-4 h-4 mt-0.5 text-muted-foreground" />
          <div>
            <div className="text-sm font-medium mb-1">Notes</div>
            <div className="text-sm text-muted-foreground">{exam.notes}</div>
          </div>
        </div>
      )}
      
      {/* Conflicts */}
      {exam.conflicts && exam.conflicts.length > 0 && (
        <div className="flex items-start gap-3 pt-2 border-t border-border">
          <FileText className="w-4 h-4 mt-0.5 text-destructive" />
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
      
      <div className="text-xs text-muted-foreground pt-2 border-t border-border">
        💡 Drag this exam to move it to a different time slot
      </div>
    </div>
  );
}