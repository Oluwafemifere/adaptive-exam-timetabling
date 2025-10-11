// frontend/src/components/StagingDataForm.tsx
import React, { useState } from 'react';
import { StagingRecord } from '../store/types';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { formatHeader } from '../utils/utils'; // Assuming you have a utils file

interface StagingDataFormProps {
  record: Partial<StagingRecord>;
  columns: string[];
  primaryKeys: string[];
  onSave: (data: StagingRecord) => void;
  onCancel: () => void;
  isEditing: boolean;
}

export const StagingDataForm: React.FC<StagingDataFormProps> = ({ record, columns, primaryKeys, onSave, onCancel, isEditing }) => {
  const [formData, setFormData] = useState(record);

  const handleChange = (key: string, value: string | number | boolean) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData as StagingRecord);
  };

  const renderInput = (key: string, value: any) => {
    const isPrimaryKey = primaryKeys.includes(key);
    // For editing, PKs are usually not editable.
    if (isEditing && isPrimaryKey) {
        return <Input id={key} value={value ?? ''} disabled />;
    }
    
    const valueType = typeof value;

    if (valueType === 'boolean') {
      return (
        <Checkbox
          id={key}
          checked={!!formData[key]}
          onCheckedChange={(checked) => handleChange(key, !!checked)}
        />
      );
    }
    
    if (valueType === 'number') {
        return <Input id={key} type="number" value={formData[key] ?? ''} onChange={(e) => handleChange(key, parseFloat(e.target.value) || 0)} />;
    }

    return <Input id={key} type="text" value={formData[key] ?? ''} onChange={(e) => handleChange(key, e.target.value)} />;
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[60vh] overflow-y-auto p-1">
        {columns.filter(c => c !== 'session_id').map(key => (
            <div key={key} className="space-y-2">
                <Label htmlFor={key}>{formatHeader(key)}</Label>
                {renderInput(key, record[key])}
            </div>
        ))}
      </div>
      <div className="flex justify-end space-x-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit">Save Changes</Button>
      </div>
    </form>
  );
};