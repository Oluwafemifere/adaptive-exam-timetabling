import React, { useState, useCallback, useMemo } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  Chip,
  IconButton,
  Toolbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  CalendarViewWeek,
  CalendarViewMonth,
  List as ListIcon,
  Warning as WarningIcon,
  FilterList as FilterIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
  GetApp as ExportIcon,
  DragIndicator,
} from '@mui/icons-material';
import { useDrag, useDrop } from 'react-dnd';
import { useScheduling } from '@hooks/useScheduling';
import { useScheduleStats } from '@store';
import { ExamSlot, Conflict } from '@store/schedulingSlice';
import { TIME_SLOTS, WEEKDAYS } from '@utils/constants';
import { formatTime, formatDate } from '@utils/formatting';
import clsx from 'clsx';

// Types
interface TimetableViewProps {
  viewMode: 'calendar' | 'list' | 'conflicts';
  dateRange: { start: string; end: string };
  selectedExam: string | null;
  onExamSelect: (examId: string | null) => void;
  onExamMove: (examId: string, newDate: string, newTimeSlot: string, newRoom?: string) => void;
}

interface ExamBlockProps {
  exam: ExamSlot;
  isSelected: boolean;
  conflicts: string[];
  onClick: () => void;
  onMove: (newDate: string, newTimeSlot: string, newRoom?: string) => void;
}

interface ConflictPanelProps {
  conflicts: Conflict[];
  onResolveConflict: (conflictId: string) => void;
}

// Draggable Exam Block Component
const ExamBlock: React.FC<ExamBlockProps> = ({ 
  exam, 
  isSelected, 
  conflicts, 
  onClick, 
  onMove 
}) => {
  const [{ isDragging }, dragRef] = useDrag({
    type: 'exam',
    item: { id: exam.id, exam },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const getConflictSeverity = () => {
    if (conflicts.includes('critical')) return 'error';
    if (conflicts.includes('high')) return 'warning';
    if (conflicts.includes('medium')) return 'warning';
    return 'default';
  };

  const getBorderColor = () => {
    if (isSelected) return 'primary.main';
    if (conflicts.length > 0) {
      const severity = getConflictSeverity();
      if (severity === 'error') return 'error.main';
      if (severity === 'warning') return 'warning.main';
    }
    return 'success.main';
  };

  const getUtilizationColor = (utilization?: number) => {
    if (!utilization) return 'grey';
    if (utilization > 0.9) return 'error';
    if (utilization > 0.8) return 'warning';
    return 'success';
  };

  return (
    <Card
      ref={dragRef}
      onClick={onClick}
      sx={{
        minHeight: 100,
        mb: 1,
        cursor: 'pointer',
        borderLeft: 4,
        borderColor: getBorderColor(),
        opacity: isDragging ? 0.5 : 1,
        transition: 'all 0.2s',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 2,
        },
        ...(isSelected && {
          boxShadow: 3,
          transform: 'scale(1.02)',
        }),
      }}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        {/* Course Code and Room */}
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
          <Typography variant="subtitle2" fontWeight="bold" color="primary">
            {exam.courseCode}
          </Typography>
          <IconButton size="small" sx={{ p: 0 }}>
            <DragIndicator fontSize="small" />
          </IconButton>
        </Box>

        {/* Course Name */}
        <Typography variant="body2" color="text.primary" mb={1}>
          {exam.courseName}
        </Typography>

        {/* Room and Capacity */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="caption" color="text.secondary">
            {exam.roomCode}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {exam.studentsCount} students
          </Typography>
        </Box>

        {/* Invigilator */}
        {exam.invigilator && (
          <Typography variant="caption" color="text.secondary" display="block" mb={1}>
            {exam.invigilator}
          </Typography>
        )}

        {/* Utilization Bar */}
        {exam.utilization && (
          <Box mb={1}>
            <Box display="flex" justifyContent="between" mb={0.5}>
              <Typography variant="caption" color="text.secondary">
                Utilization
              </Typography>
              <Typography variant="caption" color={`${getUtilizationColor(exam.utilization)}.main`}>
                {Math.round(exam.utilization * 100)}%
              </Typography>
            </Box>
            <Box
              sx={{
                height: 4,
                backgroundColor: 'grey.200',
                borderRadius: 2,
                overflow: 'hidden',
              }}
            >
              <Box
                sx={{
                  height: '100%',
                  width: `${exam.utilization * 100}%`,
                  backgroundColor: `${getUtilizationColor(exam.utilization)}.main`,
                  transition: 'width 0.3s ease',
                }}
              />
            </Box>
          </Box>
        )}

        {/* Conflict Indicators */}
        {conflicts.length > 0 && (
          <Box display="flex" flexWrap="wrap" gap={0.5}>
            {conflicts.slice(0, 2).map((conflict, index) => (
              <Chip
                key={index}
                size="small"
                label={conflict}
                color={getConflictSeverity()}
                variant="outlined"
                sx={{ fontSize: '0.7rem', height: 18 }}
              />
            ))}
            {conflicts.length > 2 && (
              <Chip
                size="small"
                label={`+${conflicts.length - 2}`}
                color="default"
                variant="outlined"
                sx={{ fontSize: '0.7rem', height: 18 }}
              />
            )}
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

// Drop Zone Component for Time Slots
interface TimeSlotDropZoneProps {
  date: string;
  timeSlot: string;
  exams: ExamSlot[];
  onExamMove: (examId: string, newDate: string, newTimeSlot: string) => void;
  onExamSelect: (examId: string | null) => void;
  selectedExam: string | null;
  conflicts: Conflict[];
}

const TimeSlotDropZone: React.FC<TimeSlotDropZoneProps> = ({
  date,
  timeSlot,
  exams,
  onExamMove,
  onExamSelect,
  selectedExam,
  conflicts,
}) => {
  const [{ isOver, canDrop }, dropRef] = useDrop({
    accept: 'exam',
    drop: (item: { id: string; exam: ExamSlot }) => {
      onExamMove(item.id, date, timeSlot);
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  });

  const getExamConflicts = (examId: string) => {
    return conflicts
      .filter(conflict => conflict.affectedExams.includes(examId))
      .map(conflict => conflict.type);
  };

  return (
    <Box
      ref={dropRef}
      sx={{
        minHeight: 120,
        p: 1,
        backgroundColor: isOver ? 'action.hover' : 'background.default',
        borderRadius: 1,
        border: '1px solid',
        borderColor: isOver && canDrop ? 'primary.main' : 'divider',
        borderStyle: isOver && canDrop ? 'dashed' : 'solid',
        transition: 'all 0.2s',
      }}
    >
      {exams.length === 0 ? (
        <Box
          sx={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'text.disabled',
          }}
        >
          {isOver && canDrop ? (
            <Typography variant="body2">Drop exam here</Typography>
          ) : (
            <Typography variant="body2">No exams scheduled</Typography>
          )}
        </Box>
      ) : (
        exams.map(exam => (
          <ExamBlock
            key={exam.id}
            exam={exam}
            isSelected={selectedExam === exam.id}
            conflicts={getExamConflicts(exam.id)}
            onClick={() => onExamSelect(exam.id === selectedExam ? null : exam.id)}
            onMove={(newDate, newTimeSlot, newRoom) => onExamMove(exam.id, newDate, newTimeSlot, newRoom)}
          />
        ))
      )}
    </Box>
  );
};

// Calendar View Component
const CalendarView: React.FC<TimetableViewProps> = ({
  dateRange,
  selectedExam,
  onExamSelect,
  onExamMove,
}) => {
  const { schedule, conflicts } = useScheduling();

  // Group exams by date and time slot
  const examsBySlot = useMemo(() => {
    const grouped: Record<string, Record<string, ExamSlot[]>> = {};
    
    schedule.forEach(exam => {
      if (!grouped[exam.date]) {
        grouped[exam.date] = {};
      }
      if (!grouped[exam.date][exam.timeSlot]) {
        grouped[exam.date][exam.timeSlot] = [];
      }
      grouped[exam.date][exam.timeSlot].push(exam);
    });

    return grouped;
  }, [schedule]);

  // Generate date range for display
  const dateRange7Days = useMemo(() => {
    const dates = [];
    const start = new Date(dateRange.start);
    
    for (let i = 0; i < 7; i++) {
      const date = new Date(start);
      date.setDate(start.getDate() + i);
      dates.push(date.toISOString().split('T')[0]);
    }
    
    return dates;
  }, [dateRange.start]);

  return (
    <Paper sx={{ overflow: 'auto' }}>
      {/* Calendar Header */}
      <Box sx={{ position: 'sticky', top: 0, backgroundColor: 'background.paper', zIndex: 1 }}>
        <Grid container sx={{ borderBottom: 1, borderColor: 'divider' }}>
          {/* Time slot header */}
          <Grid item xs={2} md={1.5}>
            <Box sx={{ p: 2, borderRight: 1, borderColor: 'divider' }}>
              <Typography variant="subtitle2" fontWeight="bold">
                Time
              </Typography>
            </Box>
          </Grid>
          
          {/* Date headers */}
          {dateRange7Days.map(date => {
            const dayOfWeek = new Date(date).toLocaleDateString('en-US', { weekday: 'short' });
            const dayOfMonth = new Date(date).getDate();
            
            return (
              <Grid item key={date} xs={10/6} md={10/6}>
                <Box sx={{ p: 2, textAlign: 'center', borderRight: 1, borderColor: 'divider' }}>
                  <Typography variant="subtitle2" fontWeight="bold">
                    {dayOfWeek} {dayOfMonth}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatDate(date, 'MMM d')}
                  </Typography>
                </Box>
              </Grid>
            );
          })}
        </Grid>
      </Box>

      {/* Calendar Body */}
      <Box sx={{ minHeight: 600 }}>
        {TIME_SLOTS.map(timeSlot => (
          <Grid container key={timeSlot.id} sx={{ borderBottom: 1, borderColor: 'divider' }}>
            {/* Time slot label */}
            <Grid item xs={2} md={1.5}>
              <Box sx={{ p: 2, borderRight: 1, borderColor: 'divider', minHeight: 120 }}>
                <Typography variant="body2" fontWeight="medium">
                  {formatTime(timeSlot.start)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {timeSlot.label}
                </Typography>
              </Box>
            </Grid>
            
            {/* Date columns */}
            {dateRange7Days.map(date => (
              <Grid item key={`${date}-${timeSlot.id}`} xs={10/6} md={10/6}>
                <Box sx={{ borderRight: 1, borderColor: 'divider' }}>
                  <TimeSlotDropZone
                    date={date}
                    timeSlot={timeSlot.id}
                    exams={examsBySlot[date]?.[timeSlot.id] || []}
                    onExamMove={onExamMove}
                    onExamSelect={onExamSelect}
                    selectedExam={selectedExam}
                    conflicts={conflicts}
                  />
                </Box>
              </Grid>
            ))}
          </Grid>
        ))}
      </Box>
    </Paper>
  );
};

// Main Timetable Component
const Timetable: React.FC = () => {
  const {
    schedule,
    conflicts,
    viewMode,
    dateRange,
    selectedExam,
    setViewMode,
    selectExam,
    moveExam,
    resolveConflict,
    refreshSchedule,
    exportSchedule,
  } = useScheduling();

  const [isExportDialogOpen, setIsExportDialogOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState('pdf');

  const handleExamMove = useCallback(async (examId: string, newDate: string, newTimeSlot: string, newRoom?: string) => {
    try {
      await moveExam(examId, newDate, newTimeSlot, newRoom);
    } catch (error) {
      console.error('Failed to move exam:', error);
      // Show error notification
    }
  }, [moveExam]);

  const handleExportSchedule = async () => {
    try {
      await exportSchedule(exportFormat);
      setIsExportDialogOpen(false);
    } catch (error) {
      console.error('Failed to export schedule:', error);
    }
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <Box sx={{ flexGrow: 1, p: 3 }}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              Exam Timetable
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Week View: {formatDate(dateRange.start)} - {formatDate(dateRange.end)}
            </Typography>
          </Box>

          <Box display="flex" gap={1}>
            <ButtonGroup variant="outlined" size="small">
              <Button
                startIcon={<ListIcon />}
                variant={viewMode === 'list' ? 'contained' : 'outlined'}
                onClick={() => setViewMode('list')}
              >
                List
              </Button>
              <Button
                startIcon={<CalendarViewWeek />}
                variant={viewMode === 'calendar' ? 'contained' : 'outlined'}
                onClick={() => setViewMode('calendar')}
              >
                Calendar
              </Button>
              <Button
                startIcon={<WarningIcon />}
                variant={viewMode === 'conflicts' ? 'contained' : 'outlined'}
                onClick={() => setViewMode('conflicts')}
              >
                Conflicts
              </Button>
            </ButtonGroup>

            <IconButton onClick={refreshSchedule}>
              <RefreshIcon />
            </IconButton>
            <Button
              variant="outlined"
              startIcon={<ExportIcon />}
              onClick={() => setIsExportDialogOpen(true)}
            >
              Export
            </Button>
          </Box>
        </Box>

        {/* Conflict Alert */}
        {conflicts.length > 0 && (
          <Alert
            severity="warning"
            sx={{ mb: 3 }}
            action={
              <Button color="inherit" size="small" onClick={() => setViewMode('conflicts')}>
                View All
              </Button>
            }
          >
            {conflicts.filter(c => !c.isResolved).length} unresolved conflicts detected.
          </Alert>
        )}

        {/* Main Content */}
        {viewMode === 'calendar' && (
          <CalendarView
            viewMode={viewMode}
            dateRange={dateRange}
            selectedExam={selectedExam}
            onExamSelect={selectExam}
            onExamMove={handleExamMove}
          />
        )}

        {/* Export Dialog */}
        <Dialog open={isExportDialogOpen} onClose={() => setIsExportDialogOpen(false)}>
          <DialogTitle>Export Timetable</DialogTitle>
          <DialogContent>
            <FormControl fullWidth sx={{ mt: 2 }}>
              <InputLabel>Format</InputLabel>
              <Select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                label="Format"
              >
                <MenuItem value="pdf">PDF</MenuItem>
                <MenuItem value="csv">CSV</MenuItem>
                <MenuItem value="excel">Excel</MenuItem>
                <MenuItem value="json">JSON</MenuItem>
              </Select>
            </FormControl>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setIsExportDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleExportSchedule} variant="contained">
              Export
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </DndProvider>
  );
};

export default Timetable;