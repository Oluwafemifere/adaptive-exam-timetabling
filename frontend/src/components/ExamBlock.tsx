// frontend/src/components/ExamBlock.tsx
import { RenderableExam } from '../store/types';
import { Card } from './ui/card';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { Clock, Users, MapPin, Building, UserCheck, GripVertical } from 'lucide-react';
import { ExamBlockTooltip } from './ExamBlockTooltip';
import { formatTime } from '../utils/timetableUtils';

interface ExamBlockProps {
  exam: RenderableExam;
  color: string;
  startColumn: number;
  spanColumns: number;
  stackLevel: number;
  rowHeight: number;
}

export function ExamBlock({ exam, color, startColumn, spanColumns, stackLevel, rowHeight }: ExamBlockProps) {
  const isGradient = color.includes('linear-gradient');
  
  // Calculate positioning
  const stackHeight = 92;
  const stackGap = 8;
  const topOffset = 8 + stackLevel * (stackHeight + stackGap);

  const getUtilization = () => {
    if (!exam.roomCapacity || exam.roomCapacity === 0) return '0%';
    const percentage = Math.round((exam.expectedStudents / exam.roomCapacity) * 100);
    return `${percentage}%`;
  };

  const getUtilizationColor = () => {
    if (!exam.roomCapacity || exam.roomCapacity === 0) return 'text-gray-400';
    const percentage = (exam.expectedStudents / exam.roomCapacity) * 100;
    if (percentage >= 90) return 'text-red-400';
    if (percentage >= 75) return 'text-yellow-400';
    return 'text-green-400';
  };

  return (
    <div 
      className="absolute"
      style={{
        top: `${topOffset}px`,
        height: `${stackHeight}px`,
        left: '4px',
        right: '4px',
        zIndex: 10 + stackLevel,
        gridColumn: `${startColumn} / span ${spanColumns}`,
      }}
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <Card 
            className="border-0 shadow-md hover:shadow-lg transition-all duration-200 hover:scale-[1.02] text-white overflow-hidden select-none cursor-grab active:cursor-grabbing h-full w-full"
            style={{
              background: isGradient ? color : undefined,
              backgroundColor: isGradient ? undefined : color,
            }}
          >
            <div className="p-2 h-full flex text-xs relative">
              {/* Drag handle */}
              <div className="absolute left-1 top-1/2 transform -translate-y-1/2 opacity-60 hover:opacity-100 z-10">
                <GripVertical className="w-3 h-3" />
              </div>
              
              <div className="flex-1 ml-4 flex flex-col">
                {/* Header - Course Info */}
                <div className="space-y-1 mb-2">
                  <div className="font-medium truncate" title={exam.courseName}>
                    {exam.courseCode || 'N/A'}
                  </div>
                  <div className="text-xs opacity-90 truncate leading-tight">
                    {exam.courseName || 'Unknown Course'}
                  </div>
                </div>
                
                {/* Two-column metadata layout */}
                <div className="flex-1 grid grid-cols-2 gap-2 text-xs">
                  {/* Left Column */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-1 opacity-90">
                      <Clock className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate text-xs">
                        {(exam.startTime && formatTime(exam.startTime)) || 'N/A'}–{(exam.endTime && formatTime(exam.endTime)) || 'N/A'}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-1 opacity-90">
                      <MapPin className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate text-xs">{exam.room || 'N/A'}</span>
                    </div>
                    
                    <div className="flex items-center gap-1 opacity-90">
                      <Users className="w-3 h-3 flex-shrink-0" />
                      <span className="text-xs">{exam.expectedStudents || 0}/{exam.roomCapacity || 0}</span>
                    </div>
                  </div>
                  
                  {/* Right Column */}
                  <div className="space-y-1">
                    <div className="flex items-center gap-1 opacity-90">
                      <Building className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate text-xs">{exam.building || 'N/A'}</span>
                    </div>
                    
                    <div className="flex items-center gap-1 opacity-90">
                      <UserCheck className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate text-xs">{exam.invigilator || 'N/A'}</span>
                    </div>
                    
                    <div className="flex justify-end">
                      <span className={`font-medium text-xs ${getUtilizationColor()}`}>
                        {getUtilization()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </TooltipTrigger>
        
        <TooltipContent side="right" className="p-4 bg-card border shadow-lg rounded-lg">
          <ExamBlockTooltip exam={exam} />
        </TooltipContent>
      </Tooltip>
    </div>
  );
}