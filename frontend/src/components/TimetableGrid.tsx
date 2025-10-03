// frontend/src/components/TimetableGrid.tsx
import { useMemo } from 'react';
import { RenderableExam } from '../store/types';
import { ExamBlock } from './ExamBlock';
import { TooltipProvider } from './ui/tooltip'; // Import the provider
import { getTimeSlot, generateDepartmentColors, generateDistinctColors, calculateDuration } from '../utils/timetableUtils';

interface TimetableGridProps {
  exams: RenderableExam[];
  viewMode: 'general' | 'department';
  departments: string[];
  onMoveExam: (examId: string, newDate: string, newStartTime: string) => void;
}

// FIX: Renamed this interface to avoid conflict with the global 'Exam' type
interface PositionedRenderableExam extends RenderableExam {
  startColumn: number;
  spanColumns: number;
  stackLevel: number;
  examIndex: number;
}

export function TimetableGrid({ exams, viewMode, departments, onMoveExam }: TimetableGridProps) {
  const timeSlots = [
    '9:00am–10:00am', '10:00am–11:00am', '11:00am–12:00pm', 
    '12:00pm–1:00pm', '1:00pm–2:00pm', '2:00pm–3:00pm', 
    '3:00pm–4:00pm', '4:00pm–5:00pm', '5:00pm–6:00pm'
  ];
  
  const timeSlotValues = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'];
  
  const dates = useMemo(() => {
    const dateSet = new Set(exams.map(exam => exam.date));
    return Array.from(dateSet).sort();
  }, [exams]);

  const departmentColors = useMemo(() => {
    return viewMode === 'general' 
      ? generateDepartmentColors(departments)
      : {};
  }, [departments, viewMode]);

  const examColors = useMemo(() => {
    return viewMode === 'department' 
      ? generateDistinctColors(exams.length)
      : {};
  }, [exams.length, viewMode]);

  // Process exams for each date with proper positioning and stacking
  const examsByDate = useMemo(() => {
    const result: Record<string, PositionedRenderableExam[]> = {};
    
    dates.forEach(date => {
      const dateExams = exams.filter(exam => exam.date === date);
      const positioned: PositionedRenderableExam[] = [];
      
      dateExams.forEach((exam, examIndex) => {
        const startColumn = getTimeSlot(exam.startTime) + 2; // +2 to account for date column
        const duration = calculateDuration(exam.startTime, exam.endTime);
        const spanColumns = Math.max(1, Math.ceil(duration)); // Use ceil to ensure it covers the full hour
        
        // Find stack level by checking for overlaps with already positioned exams
        let stackLevel = 0;
        let hasOverlap = true;
        
        while (hasOverlap) {
          hasOverlap = positioned.some(posExam => 
            posExam.stackLevel === stackLevel &&
            posExam.startColumn < startColumn + spanColumns &&
            posExam.startColumn + posExam.spanColumns > startColumn
          );
          
          if (hasOverlap) {
            stackLevel++;
          }
        }
        
        positioned.push({
          ...exam,
          startColumn,
          spanColumns,
          stackLevel,
          examIndex: exams.findIndex(e => e.id === exam.id)
        });
      });
      
      result[date] = positioned;
    });
    
    return result;
  }, [exams, dates]);

  // Calculate maximum stack levels for each date to determine row height
  const maxStackLevels = useMemo(() => {
    const result: Record<string, number> = {};
    
    dates.forEach(date => {
      const maxLevel = examsByDate[date]?.reduce((max, exam) => 
        Math.max(max, exam.stackLevel), 0) || 0;
      result[date] = maxLevel + 1; // +1 because stack levels are 0-indexed
    });
    
    return result;
  }, [examsByDate, dates]);

  const getExamColor = (exam: PositionedRenderableExam) => {
    if (viewMode === 'general') {
      if (exam.departments.length === 1) {
        return departmentColors[exam.departments[0]] || '#6b7280';
      } else {
        // Create gradient for multi-department exams
        const colors = exam.departments.map(dept => departmentColors[dept] || '#6b7280');
        return `linear-gradient(135deg, ${colors.join(', ')})`;
      }
    } else {
      return examColors[exam.examIndex] || '#6b7280';
    }
  };

  return (
    <TooltipProvider>
      <div className="overflow-x-auto">
        <div className="min-w-max">
          {/* Header with time slots */}
          <div className="grid grid-cols-[200px_repeat(9,_1fr)] gap-px bg-border mb-px">
            <div className="bg-card p-3 border-r">
              <span className="font-medium">Date</span>
            </div>
            {timeSlots.map(time => (
              <div key={time} className="bg-card p-2 text-center">
                <span className="text-xs leading-tight">{time}</span>
              </div>
            ))}
          </div>

          {/* Date rows */}
          {dates.map((date, dateIndex) => {
            const stackLevels = maxStackLevels[date] || 1;
            const rowHeight = Math.max(140, stackLevels * 100 + (stackLevels - 1) * 8); // 100px per stack + 8px gap
            
            return (
              <div key={date}>
                <div 
                  className="relative grid grid-cols-[200px_repeat(9,_1fr)] gap-px bg-border mb-px"
                  style={{ minHeight: `${rowHeight}px` }}
                >
                  {/* Date column */}
                  <div className="bg-card p-3 border-r flex flex-col justify-center">
                    <div className="font-medium">
                      {new Date(date + 'T00:00:00').toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {date}
                    </div>
                  </div>

                  {/* Time slot columns - background cells */}
                  {timeSlots.map((_, slotIndex) => (
                    <div key={slotIndex} className="bg-card relative min-h-full">
                    </div>
                  ))}

                  {/* Positioned exam blocks */}
                  {examsByDate[date]?.map(exam => (
                    <ExamBlock
                      key={exam.id}
                      exam={exam}
                      color={getExamColor(exam)}
                      startColumn={exam.startColumn}
                      spanColumns={exam.spanColumns}
                      stackLevel={exam.stackLevel}
                      rowHeight={rowHeight}
                    />
                  ))}
                </div>
                
                {/* Day separator - thicker border between days */}
                {dateIndex < dates.length - 1 && (
                  <div className="h-2 bg-gradient-to-r from-border via-border/50 to-border mb-2">
                    <div className="h-full bg-muted/20"></div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </TooltipProvider>
  );
}