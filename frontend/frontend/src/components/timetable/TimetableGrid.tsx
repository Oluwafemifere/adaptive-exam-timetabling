// frontend/src/components/timetable/TimetableGrid.tsx
import { useMemo } from 'react';
import type { RenderableExam, TimeSlot } from '../../store/types';
import { ExamBlock } from './ExamBlock';
import { DropZone } from './DropZone';
import { generateDepartmentColors, generateDistinctColors, calculateDuration } from '../../utils/timetableUtils';

interface TimetableGridProps {
  exams: RenderableExam[];
  viewMode: 'general' | 'department';
  departments: string[];
  onMoveExam: (examId: string, newDate: string, newStartTime: string) => void;
  dateRange: string[];
  timeSlots: TimeSlot[];
}

interface PositionedExam extends RenderableExam {
  startColumn: number;
  spanColumns: number;
  stackLevel: number;
  examIndex: number;
}

export function TimetableGrid({ exams, viewMode, departments, onMoveExam, dateRange, timeSlots }: TimetableGridProps) {
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
    const result: Record<string, PositionedExam[]> = {};
    const getTimeSlotIndex = (time: string) => {
        const hour = parseInt(time.split(':')[0], 10);
        return timeSlots.findIndex(ts => ts.start_hour === hour);
    };

    dateRange.forEach(date => {
      const dateExams = exams.filter(exam => exam.date === date);
      const positioned: PositionedExam[] = [];
      
      dateExams.forEach((exam) => {
        const slotIndex = getTimeSlotIndex(exam.startTime);
        if (slotIndex === -1) return; // Skip if exam time is outside rendered slots
        
        const startColumn = slotIndex + 2; // +2 to account for date column
        const duration = calculateDuration(exam.startTime, exam.endTime);
        const spanColumns = Math.max(1, Math.round(duration));
        
        // Find stack level by checking for overlaps
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
  }, [exams, dateRange, timeSlots]);

  const maxStackLevels = useMemo(() => {
    const result: Record<string, number> = {};
    dateRange.forEach(date => {
      const maxLevel = examsByDate[date]?.reduce((max, exam) => Math.max(max, exam.stackLevel), 0) ?? 0;
      result[date] = maxLevel + 1;
    });
    return result;
  }, [examsByDate, dateRange]);

  const getExamColor = (exam: PositionedExam) => {
    if (viewMode === 'general') {
      if (exam.departments.length === 1) {
        return departmentColors[exam.departments[0]] || '#6b7280';
      } else {
        const colors = exam.departments.map(dept => departmentColors[dept] || '#6b7280');
        return `linear-gradient(135deg, ${colors.join(', ')})`;
      }
    } else {
      return examColors[exam.examIndex] || '#6b7280';
    }
  };

  return (
    <div className="overflow-x-auto">
      <div className="min-w-max">
        {/* Header with time slots */}
        <div className={`grid grid-cols-[200px_repeat(${timeSlots.length},_1fr)] gap-px bg-border mb-px`}>
          <div className="bg-card p-3 border-r">
            <span className="font-medium">Date</span>
          </div>
          {timeSlots.map(time => (
            <div key={time.id} className="bg-card p-2 text-center">
              <span className="text-xs leading-tight">{time.label}</span>
            </div>
          ))}
        </div>

        {/* Date rows */}
        {dateRange.map((date) => {
          const stackLevels = maxStackLevels[date] || 1;
          const rowHeight = Math.max(140, stackLevels * 100 + (stackLevels - 1) * 8);
          
          return (
            <div key={date}>
              <div 
                className={`relative grid grid-cols-[200px_repeat(${timeSlots.length},_1fr)] gap-px bg-border mb-px`}
                style={{ minHeight: `${rowHeight}px` }}
              >
                {/* Date column */}
                <div className="bg-card p-3 border-r flex flex-col justify-center">
                  <div className="font-medium">
                    {new Date(date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                  </div>
                </div>

                {/* Drop zones */}
                {timeSlots.map((slot) => (
                  <DropZone 
                    key={slot.id} 
                    date={date} 
                    timeSlot={slot.id} 
                    onDrop={onMoveExam}
                  />
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
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}