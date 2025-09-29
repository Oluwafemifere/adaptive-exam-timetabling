import React, { useState, useRef } from 'react'
import { 
  GripVertical, 
  AlertTriangle, 
  Users, 
  MapPin,
  Clock
} from 'lucide-react'
import { cn } from '../ui/utils'
import type { Exam } from '../../store/types'

interface ExamBlockProps {
  exam: Exam
  onDragStart: (e: React.DragEvent, exam: Exam) => void
  onDragEnd: () => void
  hasConflict?: boolean
  conflictType?: 'hard' | 'soft'
}

function ExamBlock({ exam, onDragStart, onDragEnd, hasConflict, conflictType }: ExamBlockProps) {
  const utilizationPercentage = (exam.studentsCount / exam.capacity) * 100

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, exam)}
      onDragEnd={onDragEnd}
      className={cn(
        "relative bg-white border-2 rounded-md p-3 cursor-move transition-all duration-200",
        "hover:shadow-md hover:scale-[1.02] active:scale-95",
        "min-h-[120px] w-[200px]",
        hasConflict && conflictType === 'hard' && "border-red-500 bg-red-50",
        hasConflict && conflictType === 'soft' && "border-amber-500 bg-amber-50",
        !hasConflict && "border-gray-200 hover:border-blue-300"
      )}
    >
      {/* Drag Handle */}
      <div className="absolute top-1 right-1 text-gray-400 hover:text-gray-600">
        <GripVertical className="h-4 w-4" />
      </div>

      {/* Conflict Indicator */}
      {hasConflict && (
        <div className="absolute top-1 left-1">
          <AlertTriangle className={cn(
            "h-4 w-4",
            conflictType === 'hard' ? "text-red-500" : "text-amber-500"
          )} />
        </div>
      )}

      {/* Course Information */}
      <div className="space-y-2">
        <div>
          <h4 className="font-semibold text-sm text-gray-900">{exam.courseCode}</h4>
          <p className="text-xs text-gray-600 truncate">{exam.courseName}</p>
        </div>

        {/* Room */}
        <div className="flex items-center text-xs text-gray-600">
          <MapPin className="h-3 w-3 mr-1" />
          <span>{exam.room}</span>
        </div>

        {/* Instructor */}
        <div className="text-xs text-gray-600 truncate">
          {exam.instructor}
        </div>

        {/* Capacity Bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center">
              <Users className="h-3 w-3 mr-1" />
              <span>{exam.studentsCount}/{exam.capacity}</span>
            </div>
            <span className={cn(
              "font-medium",
              utilizationPercentage > 95 ? "text-red-600" :
              utilizationPercentage > 85 ? "text-amber-600" : "text-green-600"
            )}>
              {Math.round(utilizationPercentage)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div 
              className={cn(
                "h-1.5 rounded-full transition-all duration-300",
                utilizationPercentage > 95 ? "bg-red-500" :
                utilizationPercentage > 85 ? "bg-amber-500" : "bg-green-500"
              )}
              style={{ width: `${Math.min(utilizationPercentage, 100)}%` }}
            />
          </div>
        </div>

        {/* Duration */}
        <div className="flex items-center text-xs text-gray-500">
          <Clock className="h-3 w-3 mr-1" />
          <span>{exam.duration}min</span>
        </div>
      </div>
    </div>
  )
}

interface TimeSlotCellProps {
  date: string
  timeSlot: string
  exams: Exam[]
  onDrop: (date: string, timeSlot: string) => void
  onDragOver: (e: React.DragEvent) => void
  isDragOver: boolean
  conflicts: Array<{ examIds: string[]; type: 'hard' | 'soft' }>
}

function TimeSlotCell({ date, timeSlot, exams, onDrop, onDragOver, isDragOver, conflicts }: TimeSlotCellProps) {
  const [draggedExam, setDraggedExam] = useState<Exam | null>(null)

  const handleDragStart = (e: React.DragEvent, exam: Exam) => {
    setDraggedExam(exam)
    e.dataTransfer.setData('application/json', JSON.stringify(exam))
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragEnd = () => {
    setDraggedExam(null)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    onDrop(date, timeSlot)
  }

  const getExamConflicts = (examId: string) => {
    return conflicts.filter(conflict => conflict.examIds.includes(examId))
  }

  return (
    <div
      className={cn(
        "border border-gray-200 bg-white transition-colors duration-200",
        "min-h-[120px] w-[200px] p-2 relative",
        isDragOver && "bg-blue-50 border-blue-300 border-dashed"
      )}
      onDragOver={onDragOver}
      onDrop={handleDrop}
    >
      {/* CRITICAL: Stack exams vertically, never horizontally */}
      <div className="space-y-2">
        {exams.map((exam) => {
          const examConflicts = getExamConflicts(exam.id)
          const hasHardConflict = examConflicts.some(c => c.type === 'hard')
          const hasSoftConflict = examConflicts.some(c => c.type === 'soft')
          
          return (
            <div key={exam.id}>
              <ExamBlock
                exam={exam}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                hasConflict={hasHardConflict || hasSoftConflict}
                conflictType={hasHardConflict ? 'hard' : 'soft'}
              />
              {/* Clear separation line between stacked exams */}
              {exams.length > 1 && exams.indexOf(exam) < exams.length - 1 && (
                <div className="border-t border-gray-300 mx-2 my-1" />
              )}
            </div>
          )
        })}
      </div>

      {/* Empty slot indicator */}
      {exams.length === 0 && (
        <div className="flex items-center justify-center h-full text-gray-400 text-sm">
          Drop exam here
        </div>
      )}
    </div>
  )
}

interface TimetableCalendarProps {
  exams: Exam[]
  onExamMove: (examId: string, newDate: string, newTimeSlot: string) => void
  conflicts: Array<{ id: string; examIds: string[]; type: 'hard' | 'soft' }>
  dateRange: string[]
  timeSlots: string[]
}

export function TimetableCalendar({ 
  exams, 
  onExamMove, 
  conflicts, 
  dateRange, 
  timeSlots 
}: TimetableCalendarProps) {
  const [dragOverCell, setDragOverCell] = useState<{ date: string; timeSlot: string } | null>(null)
  const draggedExam = useRef<Exam | null>(null)

  const handleDragOver = (e: React.DragEvent, date: string, timeSlot: string) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverCell({ date, timeSlot })
  }

  const handleDragLeave = () => {
    setDragOverCell(null)
  }

  const handleDrop = (date: string, timeSlot: string) => {
    if (draggedExam.current) {
      onExamMove(draggedExam.current.id, date, timeSlot)
      draggedExam.current = null
    }
    setDragOverCell(null)
  }

  // Group exams by date and time slot
  const examsBySlot = exams.reduce((acc, exam) => {
    const key = `${exam.date}-${exam.timeSlot}`
    if (!acc[key]) {
      acc[key] = []
    }
    acc[key].push(exam)
    return acc
  }, {} as Record<string, Exam[]>)

  return (
    <div className="overflow-auto border border-gray-200 rounded-lg bg-white">
      <div className="min-w-max">
        {/* Header Row - Time Slots */}
        <div className="flex bg-gray-50 border-b border-gray-200 sticky top-0 z-20">
          {/* Corner cell for dates/times intersection */}
          <div className="w-32 px-4 py-3 font-medium text-gray-900 border-r border-gray-200 bg-gray-50">
            Date / Time
          </div>
          
          {/* Time slot headers */}
          {timeSlots.map((timeSlot) => (
            <div 
              key={timeSlot}
              className="w-[200px] px-4 py-3 text-center font-medium text-gray-900 border-r border-gray-200 last:border-r-0"
            >
              {timeSlot}
            </div>
          ))}
        </div>

        {/* Calendar Grid Rows */}
        {dateRange.map((date) => (
          <div key={date} className="flex border-b border-gray-200 last:border-b-0">
            {/* Date Label */}
            <div className="w-32 px-4 py-3 font-medium text-gray-900 border-r border-gray-200 bg-gray-50 sticky left-0 z-10">
              <div>{new Date(date).toLocaleDateString('en-US', { 
                weekday: 'short',
                month: 'short',
                day: 'numeric'
              })}</div>
            </div>
            
            {/* Time Slot Cells */}
            {timeSlots.map((timeSlot) => {
              const slotKey = `${date}-${timeSlot}`
              const slotExams = examsBySlot[slotKey] || []
              const isDragOver = dragOverCell?.date === date && dragOverCell?.timeSlot === timeSlot
              
              return (
                <TimeSlotCell
                  key={`${date}-${timeSlot}`}
                  date={date}
                  timeSlot={timeSlot}
                  exams={slotExams}
                  onDrop={handleDrop}
                  onDragOver={(e) => handleDragOver(e, date, timeSlot)}
                  isDragOver={isDragOver}
                  conflicts={conflicts}
                />
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}