// // frontend/src/components/scheduling/TimetableCalendar.tsx

// import React, { useMemo } from 'react';
// import { GripVertical, AlertTriangle, Users, Box, Info, UserCheck } from 'lucide-react';
// import { cn } from '../ui/utils';
// import type { RenderableExam, TimetableCalendarProps } from '../../store/types';
// import {
//   Tooltip,
//   TooltipContent,
//   TooltipProvider,
//   TooltipTrigger,
// } from "../ui/tooltip"

// // --- Sizing & Layout Constants ---
// const BASE_EXAM_BLOCK_HEIGHT_PX = 120; // A baseline height for calculation and min-height
// const VERTICAL_SPACING_PX = 12; // Increased vertical gap for better readability
// const HORIZONTAL_PADDING_PX = 4; // Horizontal padding around blocks

// // --- Color & Style Utilities ---
// const colorPalette = [
//     { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-300', darkBg: 'dark:bg-blue-900/40', darkText: 'dark:text-blue-200', darkBorder: 'dark:border-blue-700' },
//     { bg: 'bg-emerald-100', text: 'text-emerald-800', border: 'border-emerald-300', darkBg: 'dark:bg-emerald-900/40', darkText: 'dark:text-emerald-200', darkBorder: 'dark:border-emerald-700' },
//     { bg: 'bg-violet-100', text: 'text-violet-800', border: 'border-violet-300', darkBg: 'dark:bg-violet-900/40', darkText: 'dark:text-violet-200', darkBorder: 'dark:border-violet-700' },
//     { bg: 'bg-rose-100', text: 'text-rose-800', border: 'border-rose-300', darkBg: 'dark:bg-rose-900/40', darkText: 'dark:text-rose-200', darkBorder: 'dark:border-rose-700' },
//     { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-300', darkBg: 'dark:bg-amber-900/40', darkText: 'dark:text-amber-200', darkBorder: 'dark:border-amber-700' },
//     { bg: 'bg-cyan-100', text: 'text-cyan-800', border: 'border-cyan-300', darkBg: 'dark:bg-cyan-900/40', darkText: 'dark:text-cyan-200', darkBorder: 'dark:border-cyan-700' },
//     { bg: 'bg-pink-100', text: 'text-pink-800', border: 'border-pink-300', darkBg: 'dark:bg-pink-900/40', darkText: 'dark:text-pink-200', darkBorder: 'dark:border-pink-700' },
//     { bg: 'bg-indigo-100', text: 'text-indigo-800', border: 'border-indigo-300', darkBg: 'dark:bg-indigo-900/40', darkText: 'dark:text-indigo-200', darkBorder: 'dark:border-indigo-700' },
//     { bg: 'bg-teal-100', text: 'text-teal-800', border: 'border-teal-300', darkBg: 'dark:bg-teal-900/40', darkText: 'dark:text-teal-200', darkBorder: 'dark:border-teal-700' },
//     { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300', darkBg: 'dark:bg-orange-900/40', darkText: 'dark:text-orange-200', darkBorder: 'dark:border-orange-700' },
// ];

// function getEntityColor(id: string | undefined, salt: string = "") {
//   if (!id) return colorPalette[0];
//   let hash = 0;
//   for (let i = 0; i < id.length + salt.length; i++) {
//     const char = (id + salt).charCodeAt(i);
//     hash = ((hash << 5) - hash) + char;
//     hash |= 0;
//   }
//   return colorPalette[Math.abs(hash) % colorPalette.length];
// }

// // --- REBUILT UI COMPONENT ---
// function ExamBlock({ exam, hasConflict, conflictType, color }: { exam: RenderableExam, hasConflict?: boolean, conflictType?: 'hard' | 'soft', color: typeof colorPalette[0] }) {
//     const { capacity, student_count } = exam;
//     const utilization = (capacity && capacity.total_assigned_capacity > 0) 
//         ? (student_count / capacity.total_assigned_capacity) * 100 
//         : 0;
  
//     return (
//         <TooltipProvider delayDuration={100}>
//             <Tooltip>
//                 <TooltipTrigger asChild>
//                 <div
//                     className={cn(
//                         "relative w-full h-full flex flex-col text-left border rounded-md p-2 transition-shadow hover:shadow-md cursor-pointer",
//                         color.bg, color.border, color.text,
//                         color.darkBg, color.darkBorder, color.darkText,
//                         hasConflict && conflictType === 'hard' && "!border-red-500 !border-2 !bg-red-50 dark:!bg-red-900/50 !text-red-800 dark:!text-red-200",
//                         hasConflict && conflictType === 'soft' && "!border-amber-500 !border-2 !bg-amber-50 dark:!bg-amber-900/50 !text-amber-800 dark:!text-amber-200",
//                     )}
//                 >
//                     {/* Top Section: Course Code, Icons */}
//                     <div className="flex-shrink-0 flex items-start justify-between">
//                         <div className="flex items-center min-w-0">
//                             {hasConflict && <AlertTriangle className={cn("h-4 w-4 mr-2 flex-shrink-0", conflictType === 'hard' ? "!text-red-500" : "!text-amber-500")} />}
//                             <h4 className="font-semibold text-sm truncate" title={exam.courseCode}>
//                                 {exam.courseCode}
//                             </h4>
//                         </div>
//                         <GripVertical className="h-6 w-3 text-current/30 cursor-grab flex-shrink-0" />
//                     </div>

//                     {/* Middle Section: Course Name (Flexible, but clamped) */}
//                     <div className="flex-1 my-1">
//                          <p className="text-xs text-current/80" title={exam.courseName}>
//                              {exam.courseName}
//                          </p>
//                     </div>

//                     {/* Bottom Section: Details */}
//                     <div className="flex-shrink-0 text-xs space-y-1.5">
//                         <div className="flex items-center" title={`Students: ${student_count} / Capacity: ${capacity?.total_assigned_capacity ?? 'N/A'}`}>
//                             <Users className="h-3.5 w-3.5 mr-1.5 flex-shrink-0" />
//                             <span className="font-medium">{student_count}</span>
//                             <span className="text-current/70 mx-0.5">/</span>
//                             <span className="text-current/70">{capacity?.total_assigned_capacity ?? 'N/A'}</span>
//                             <div className="w-full bg-current/10 rounded-full h-1.5 ml-2">
//                                 <div className={cn("h-1.5 rounded-full", color.bg.replace('-100', '-400'))} style={{ width: `${Math.min(utilization, 100)}%` }} />
//                             </div>
//                         </div>
//                         <div className="flex items-center" title={`Rooms: ${exam.roomCodes.join(', ')}`}>
//                             <Box className="h-3.5 w-3.5 mr-1.5 flex-shrink-0" />
//                             <span className="truncate">{exam.roomCodes.join(', ')}</span>
//                         </div>
//                         <div className="flex items-center" title={`Invigilator: ${exam.instructor}`}>
//                             <UserCheck className="h-3.5 w-3.5 mr-1.5 flex-shrink-0" />
//                             <span className="truncate">{exam.instructor}</span>
//                         </div>
//                     </div>
//                 </div>
//                 </TooltipTrigger>
//                 <TooltipContent className="w-64" side="top" align="start">
//                 <div className="space-y-2 text-sm">
//                     <p className="font-bold">{exam.courseCode}: {exam.courseName}</p>
//                     <p><span className="font-semibold">Department:</span> {exam.department}</p>
//                     <p><span className="font-semibold">Invigilator(s):</span> {exam.instructor}</p>
//                     <p><span className="font-semibold">Duration:</span> {exam.duration_minutes} mins</p>
//                     <p><span className="font-semibold">Time:</span> {exam.start_time} - {exam.end_time}</p>
//                     {capacity && <p><span className="font-semibold">Capacity:</span> {capacity.expected_students} students in room(s) with {capacity.total_assigned_capacity} seats ({capacity.utilization_percentage.toFixed(1)}% full).</p>}
//                 </div>
//                 </TooltipContent>
//             </Tooltip>
//         </TooltipProvider>
//     );
// }


// // --- Core Logic ---
// const parseTimeToMinutes = (timeStr: string): number => {
//   if (typeof timeStr !== 'string' || !timeStr.includes(':')) return 0;
//   const [hours, minutes] = timeStr.split(':').map(Number);
//   return (hours || 0) * 60 + (minutes || 0);
// };

// // A type to hold calculated layout properties for each exam.
// type PositionedExam = RenderableExam & {
//   startMinutes: number;
//   endMinutes: number;
//   lane: number;
// };

// type DayLayout = {
//   positionedExams: (PositionedExam & { top: number; height: number })[];
//   totalHeight: number;
// };

// const calculateDayLayout = (
//     dailyExams: RenderableExam[],
//     measureTextHeight: (exam: RenderableExam) => number
// ): DayLayout => {
//   if (!dailyExams || dailyExams.length === 0) {
//     return { positionedExams: [], totalHeight: 0 };
//   }

//   // 1. Initial mapping and sorting
//   const sortedExams = dailyExams
//     .map(exam => ({
//       ...exam,
//       startMinutes: parseTimeToMinutes(exam.start_time),
//       endMinutes: parseTimeToMinutes(exam.end_time),
//       // Estimate height based on content
//       height: Math.max(BASE_EXAM_BLOCK_HEIGHT_PX, measureTextHeight(exam)),
//     }))
//     .sort((a, b) => a.startMinutes - b.startMinutes || a.endMinutes - b.endMinutes);

//   // 2. Position exams into lanes
//   const lanes: { lastExamEndMinutes: number, currentHeight: number }[] = [];
//   const positionedExams: (PositionedExam & { top: number; height: number })[] = [];
//   let maxLaneHeight = 0;

//   for (const exam of sortedExams) {
//     let assignedToLane = false;
//     for (let i = 0; i < lanes.length; i++) {
//       if (exam.startMinutes >= lanes[i].lastExamEndMinutes + 2 /* small buffer */) {
//         const top = lanes[i].currentHeight;
//         lanes[i].lastExamEndMinutes = exam.endMinutes;
//         lanes[i].currentHeight += exam.height + VERTICAL_SPACING_PX;
//         positionedExams.push({ ...exam, lane: i, top });
//         assignedToLane = true;
//         maxLaneHeight = Math.max(maxLaneHeight, lanes[i].currentHeight);
//         break;
//       }
//     }
//     if (!assignedToLane) {
//       const newLaneIndex = lanes.length;
//       lanes.push({
//         lastExamEndMinutes: exam.endMinutes,
//         currentHeight: exam.height + VERTICAL_SPACING_PX,
//       });
//       positionedExams.push({ ...exam, lane: newLaneIndex, top: 0 });
//       maxLaneHeight = Math.max(maxLaneHeight, lanes[newLaneIndex].currentHeight);
//     }
//   }
  
//   // Subtract the final spacing from the total height
//   const totalHeight = maxLaneHeight > 0 ? maxLaneHeight - VERTICAL_SPACING_PX : 0;
//   return { positionedExams, totalHeight };
// };


// // --- Main Timetable Component ---
// export function TimetableCalendar({ exams, conflicts, dateRange, timeSlots, viewType }: TimetableCalendarProps) {
//   const gridTemplateColumns = `minmax(8rem, auto) repeat(${timeSlots.length}, minmax(10rem, 1fr))`;
  
//   // Helper function to estimate exam block height based on its text content
//   const measureExamHeight = useMemo(() => {
//     // These are estimates. A real implementation might use a hidden div to measure text.
//     const baseHeight = 65; // Height of static elements (icons, padding, progress bar)
//     const lineHeight = 16; // Approx height of one line of text
//     const charWidth = 7;   // Approx width of a character
//     const blockContentWidth = 150; // Estimated avg width of the content area in an exam block

//     return (exam: RenderableExam) => {
//         let totalLines = 0;
//         totalLines += Math.ceil(((exam.courseName?.length ?? 0) * charWidth) / blockContentWidth);
//         totalLines += Math.ceil(((exam.roomCodes.join(', ').length ?? 0) * charWidth) / blockContentWidth);
//         totalLines += Math.ceil(((exam.instructor?.length ?? 0) * charWidth) / blockContentWidth);
//         return baseHeight + totalLines * lineHeight;
//     };
// }, []);

//   const timetableLayout = useMemo(() => {
//     const examsByDate = (exams || []).reduce((acc, exam) => {
//       (acc[exam.date] = acc[exam.date] || []).push(exam);
//       return acc;
//     }, {} as Record<string, RenderableExam[]>);

//     return dateRange.reduce((acc, date) => {
//       acc[date] = calculateDayLayout(examsByDate[date] || [], measureExamHeight);
//       return acc;
//     }, {} as Record<string, DayLayout>);
//   }, [exams, dateRange, measureExamHeight]);
  
//   const getExamConflictType = (examId: string): 'hard' | 'soft' | undefined => {
//     return conflicts.find(c => c.examIds?.includes(examId))?.type;
//   };
  
//   const getExamColor = (exam: RenderableExam) => {
//     return viewType === 'department' 
//       ? getEntityColor(exam.department, "dept_view") 
//       : getEntityColor(exam.courseCode);
//   };

//   const dayStartMinutes = timeSlots.length > 0 ? parseTimeToMinutes(timeSlots[0].label.split(' - ')[0]) : 540;
//   const dayEndMinutes = timeSlots.length > 0 ? parseTimeToMinutes(timeSlots[timeSlots.length - 1].label.split(' - ')[1]) : 1020;
//   const totalDayMinutes = dayEndMinutes - dayStartMinutes;
  
//   if (totalDayMinutes <= 0) {
//       return <div className="p-4 text-destructive-foreground bg-destructive">Error: Invalid time range configuration.</div>;
//   }

//   return (
//     <div className="timetable-container overflow-auto border border-border rounded-lg bg-card">
//       <div className="grid min-w-max" style={{ gridTemplateColumns }}>
//         {/* Header Row */}
//         <div className="sticky top-0 z-20 bg-muted border-r border-b border-border p-4 font-semibold">Date</div>
//         {timeSlots.map(slot => (
//           <div key={slot.id} className="sticky top-0 z-20 px-4 py-3 text-center font-semibold border-r border-b border-border bg-muted truncate" title={slot.label}>
//             {slot.label}
//           </div>
//         ))}

//         {/* Calendar Grid Rows */}
//         {dateRange.map((date) => {
//           const { positionedExams, totalHeight } = timetableLayout[date] || { positionedExams: [], totalHeight: BASE_EXAM_BLOCK_HEIGHT_PX };
          
//           return (
//             <React.Fragment key={date}>
//               <div className="sticky left-0 z-10 bg-muted/50 px-4 py-3 font-semibold border-r border-b border-border flex items-center justify-center text-center">
//                 {new Date(date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
//               </div>
              
//               <div className="relative border-b border-border" style={{ gridColumn: `span ${timeSlots.length}`, minHeight: `${totalHeight}px` }}>
//                 {timeSlots.slice(0, -1).map((_, index) => (
//                   <div key={`line-${index}`} className="absolute top-0 bottom-0 border-r border-border/60" style={{ left: `${(100 / timeSlots.length) * (index + 1)}%` }} />
//                 ))}

//                 {positionedExams.map((exam) => {
//                   const leftPercent = (exam.startMinutes - dayStartMinutes) / totalDayMinutes * 100;
//                   const widthPercent = (exam.endMinutes - exam.startMinutes) / totalDayMinutes * 100;

//                   return (
//                     <div
//                       key={exam.id}
//                       className="absolute"
//                       style={{
//                         left: `${Math.max(0, leftPercent)}%`,
//                         width: `${Math.min(100 - leftPercent, widthPercent)}%`,
//                         top: `${exam.top}px`,
//                         height: `${exam.height}px`,
//                         zIndex: 10 + exam.lane,
//                         padding: `0 ${HORIZONTAL_PADDING_PX}px`
//                       }}
//                     >
//                       <ExamBlock exam={exam} hasConflict={!!getExamConflictType(exam.id)} conflictType={getExamConflictType(exam.id)} color={getExamColor(exam)} />
//                     </div>
//                   );
//                 })}
//               </div>
//             </React.Fragment>
//           );
//         })}
//       </div>
      
//       {exams.length === 0 && (
//         <div className="flex items-center justify-center h-64 text-center text-muted-foreground">
//           <div>
//             <Info className="mx-auto h-10 w-10 mb-2" />
//             <p>No exams match the current filters.</p>
//             <p className='text-sm'>Try adjusting the view mode or search filters.</p>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }