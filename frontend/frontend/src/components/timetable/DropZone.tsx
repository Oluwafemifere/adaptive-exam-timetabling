import { useDrop } from 'react-dnd';
import type { Exam } from '../../store/types';

interface DropZoneProps {
  date: string;
  timeSlot: string;
  onDrop: (examId: string, newDate: string, newStartTime: string) => void;
  children: React.ReactNode;
  className?: string;
}

interface DragItem {
  type: 'exam';
  exam: Exam;
}

export function DropZone({ date, timeSlot, onDrop, children, className = '' }: DropZoneProps) {
  const [{ isOver, canDrop }, drop] = useDrop(() => ({
    accept: 'exam',
    drop: (item: DragItem) => {
      onDrop(item.exam.id, date, timeSlot);
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  }), [date, timeSlot, onDrop]);

  const dropZoneClassName = `
    ${className}
    ${isOver && canDrop ? 'bg-primary/10 ring-2 ring-primary/30' : ''}
    ${canDrop && !isOver ? 'bg-muted/30' : ''}
    transition-all duration-200 relative
  `.trim();

  return (
    <div ref={drop} className={dropZoneClassName}>
      {children}
      {isOver && canDrop && (
        <div className="absolute inset-0 bg-primary/20 flex items-center justify-center text-primary font-medium text-sm z-[100] rounded-md border-2 border-primary border-dashed">
          Drop exam here
        </div>
      )}
    </div>
  );
}