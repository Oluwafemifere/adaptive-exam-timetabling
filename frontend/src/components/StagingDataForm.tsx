// frontend/src/components/StagingDataForm.tsx
import React, { useState } from 'react';
import { StagingRecord } from '../store/types';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { formatHeader } from '../utils/utils';

// Configuration for relational dropdowns, specifying which field links to which entity.
const ENTITY_RELATIONSHIPS: Record<string, Record<string, { ref: string; value: string; label: string }>> = {
  departments: {
    faculty_code: { ref: 'faculties', value: 'code', label: 'name' },
  },
  programmes: {
    department_code: { ref: 'departments', value: 'code', label: 'name' },
  },
  buildings: {
    faculty_code: { ref: 'faculties', value: 'code', label: 'name' },
  },
  rooms: {
    building_code: { ref: 'buildings', value: 'code', label: 'name' },
  },
  staff: {
    department_code: { ref: 'departments', value: 'code', label: 'name' },
  },
  students: {
    programme_code: { ref: 'programmes', value: 'code', label: 'name' },
  },
  course_departments: {
    course_code: { ref: 'courses', value: 'code', label: 'title' },
    department_code: { ref: 'departments', value: 'code', label: 'name' },
  },
  course_faculties: {
    course_code: { ref: 'courses', value: 'code', label: 'title' },
    faculty_code: { ref: 'faculties', value: 'code', label: 'name' },
  },
  course_instructors: {
    course_code: { ref: 'courses', value: 'code', label: 'title' },
    staff_number: { ref: 'staff', value: 'staff_number', label: 'last_name' },
  },
  course_registrations: {
    course_code: { ref: 'courses', value: 'code', label: 'title' },
    student_matric_number: { ref: 'students', value: 'matric_number', label: 'last_name' },
  },
};

interface StagingDataFormProps {
  record: Partial<StagingRecord>;
  entityType: string;
  columns: string[];
  primaryKeys: string[];
  allData: any; 
  onSave: (data: StagingRecord) => void;
  onCancel: () => void;
  isEditing: boolean;
}

export const StagingDataForm: React.FC<StagingDataFormProps> = ({ record, entityType, columns, primaryKeys, allData, onSave, onCancel, isEditing }) => {
  const [formData, setFormData] = useState(record);

  const handleChange = (key: string, value: string | number | boolean) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData as StagingRecord);
  };

  const renderInput = (key: string) => {
    const isPrimaryKey = primaryKeys.includes(key);
    const relationships = ENTITY_RELATIONSHIPS[entityType] || {};
    const relation = relationships[key];
    const value = formData[key];

    // Disable primary key fields if they are pre-filled (on create) or if editing (and not a relation)
    const isDisabled = (isEditing && isPrimaryKey) || (!isEditing && isPrimaryKey && !!value);

    // Render a Select dropdown if a relationship is defined
    if (relation) {
      const options = allData[relation.ref] || [];
      return (
        <Select
          value={value as any ?? ''}
          onValueChange={(selectValue) => handleChange(key, selectValue)}
          disabled={isDisabled}
        >
          <SelectTrigger>
            <SelectValue placeholder={`Select a ${formatHeader(relation.ref)}`} />
          </SelectTrigger>
          <SelectContent>
            {options.map((option: any, index: number) => (
              <SelectItem key={index} value={option[relation.value]}>
                {`${option[relation.label]} (${option[relation.value]})`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    }

    const valueType = typeof record[key];

    if (valueType === 'boolean') {
      return (
        <div className="flex items-center h-10">
          <Checkbox
            id={key}
            checked={!!formData[key]}
            onCheckedChange={(checked) => handleChange(key, !!checked)}
          />
        </div>
      );
    }
    
    if (valueType === 'number') {
        return <Input id={key} type="number" value={formData[key] as any ?? ''} onChange={(e) => handleChange(key, parseFloat(e.target.value) || 0)} />;
    }

    return <Input id={key} type="text" value={formData[key] as any ?? ''} onChange={(e) => handleChange(key, e.target.value)} disabled={isDisabled} />;
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[60vh] overflow-y-auto p-1">
        {columns.filter(c => c !== 'session_id').map(key => (
            <div key={key} className="space-y-2">
                <Label htmlFor={key}>{formatHeader(key)}</Label>
                {renderInput(key)}
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