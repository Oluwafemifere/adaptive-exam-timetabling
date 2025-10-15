// frontend/src/components/SessionDataForm.tsx
import React, { useState } from 'react';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { formatHeader } from '../utils/utils';
import { Checkbox } from './ui/checkbox';

// --- EXPANDED Configuration for form fields and their relationships ---
const ENTITY_FIELD_CONFIG: Record<string, Record<string, { type: 'text' | 'number' | 'relation' | 'boolean'; ref?: string; labelField?: string }>> = {
  courses: {
    code: { type: 'text' },
    title: { type: 'text' },
    credit_units: { type: 'number' },
    course_level: { type: 'number' },
    semester: { type: 'number' },
    exam_duration_minutes: { type: 'number' },
    department_id: { type: 'relation', ref: 'departments', labelField: 'name' },
  },
  buildings: {
    code: { type: 'text' },
    name: { type: 'text' },
  },
  rooms: {
    code: { type: 'text' },
    name: { type: 'text' },
    capacity: { type: 'number' },
    exam_capacity: { type: 'number' },
    building_id: { type: 'relation', ref: 'buildings', labelField: 'name' },
  },
  departments: {
    code: { type: 'text' },
    name: { type: 'text' },
    faculty_id: { type: 'relation', ref: 'faculties', labelField: 'name' },
  },
  staff: {
    staff_number: { type: 'text' },
    first_name: { type: 'text' },
    last_name: { type: 'text' },
    position: { type: 'text' },
    staff_type: { type: 'text' },
    department_id: { type: 'relation', ref: 'departments', labelField: 'name' },
    can_invigilate: { type: 'boolean' },
  },
  exams: {
    course_id: { type: 'relation', ref: 'courses', labelField: 'title' },
    duration_minutes: { type: 'number' },
    expected_students: { type: 'number' },
    is_practical: { type: 'boolean' },
    morning_only: { type: 'boolean' },
    requires_projector: { type: 'boolean' },
  },
};

interface SessionDataFormProps {
  entityType: 'courses' | 'buildings' | 'rooms' | 'departments' | 'staff' | 'exams';
  initialData: any;
  dataGraph: any; // The full data graph for populating selects
  onSave: (data: any) => void;
  onCancel: () => void;
}

export const SessionDataForm: React.FC<SessionDataFormProps> = ({ entityType, initialData, dataGraph, onSave, onCancel }) => {
  const [formData, setFormData] = useState(initialData);

  const fieldConfig = ENTITY_FIELD_CONFIG[entityType] || {};
  const formFields = Object.keys(fieldConfig);

  const handleChange = (key: string, value: string | number | boolean) => {
    const fieldType = fieldConfig[key]?.type;
    const finalValue = fieldType === 'number' ? Number(value) : value;
    setFormData((prev: any) => ({ ...prev, [key]: finalValue }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  const renderInput = (key: string) => {
    const config = fieldConfig[key];
    const value = formData[key] ?? '';

    if (config.type === 'relation' && config.ref) {
      const options = dataGraph[config.ref] || [];
      return (
        <Select
          value={value}
          onValueChange={(selectValue) => handleChange(key, selectValue)}
        >
          <SelectTrigger>
            <SelectValue placeholder={`Select a ${formatHeader(config.ref).slice(0, -1)}`} />
          </SelectTrigger>
          <SelectContent>
            {options.map((option: any) => (
              <SelectItem key={option.id} value={option.id}>
                {option[config.labelField || 'name']} ({option.code || option.id.substring(0, 8)})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    }
    
    if (config.type === 'boolean') {
        return (
            <div className="flex items-center h-10">
                <Checkbox
                    id={key}
                    checked={!!value}
                    onCheckedChange={(checked) => handleChange(key, !!checked)}
                />
            </div>
        );
    }

    return (
      <Input
        id={key}
        type={config.type === 'number' ? 'number' : 'text'}
        value={value}
        onChange={(e) => handleChange(key, e.target.value)}
      />
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[60vh] overflow-y-auto p-1">
        {formFields.map(key => (
          <div key={key} className="space-y-2">
            <Label htmlFor={key}>{formatHeader(key)}</Label>
            {renderInput(key)}
          </div>
        ))}
      </div>
      <div className="flex justify-end space-x-2 pt-4 border-t">
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit">Save Changes</Button>
      </div>
    </form>
  );
};