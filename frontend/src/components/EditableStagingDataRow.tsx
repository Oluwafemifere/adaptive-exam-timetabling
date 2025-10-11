// frontend/src/components/EditableStagingDataRow.tsx
import React from 'react';
import { Button } from './ui/button';
import { TableCell, TableRow } from './ui/table';
import { Pencil, Trash2 } from 'lucide-react';
import { StagingRecord } from '../store/types';

interface EditableStagingDataRowProps {
  row: StagingRecord;
  columns: string[];
  onEdit: (record: StagingRecord) => void;
  onDelete: (record: StagingRecord) => void;
}

export const EditableStagingDataRow: React.FC<EditableStagingDataRowProps> = ({ row, columns, onEdit, onDelete }) => {
  return (
    <TableRow>
      {columns.map(col => (
        <TableCell key={`${row.id}-${col}`} className="text-sm">
          {Array.isArray(row[col])
            ? row[col].join(', ')
            : typeof row[col] === 'boolean'
            ? row[col] ? 'Yes' : 'No'
            : row[col] ?? 'N/A'}
        </TableCell>
      ))}
      <TableCell className="sticky right-0 bg-background">
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="icon" onClick={() => onEdit(row)}>
            <Pencil className="h-4 w-4" />
          </Button>
          <Button variant="destructive" size="icon" onClick={() => onDelete(row)}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
};