// frontend/src/components/FilterControls.tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { Checkbox } from "./ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { Separator } from "./ui/separator";
import { X, Search, Filter, ChevronDown, Save, Bookmark, Settings, Calendar, MapPin, User } from "lucide-react";
import { useState } from "react";

// interface definitions
interface FilterPreset {
  id: string;
  name: string;
  departments: string[];
  faculties: string[];
  rooms: string[];
  staff: string[];
  searchTerm: string;
}

interface FilterControlsProps {
  departments: string[];
  selectedDepartments?: string[];
  onDepartmentsChange?: (departments: string[]) => void;
  viewMode?: 'date' | 'room' | 'invigilator';
  onViewModeChange?: (mode: 'date' | 'room' | 'invigilator') => void;
  faculties?: string[];
  selectedFaculties?: string[];
  onFacultiesChange?: (faculties: string[]) => void;
  rooms?: string[];
  selectedRooms?: string[];
  onRoomsChange?: (rooms: string[]) => void;
  staff?: string[];
  selectedStaff?: string[];
  onStaffChange?: (staff: string[]) => void;
  searchTerm?: string;
  onSearchChange?: (term: string) => void;
  showAdvancedFilters?: boolean;
  onAdvancedFiltersToggle?: () => void;
  filterPresets?: FilterPreset[];
  onSavePreset?: (preset: Omit<FilterPreset, 'id'>) => void;
  onLoadPreset?: (preset: FilterPreset) => void;
}


export function FilterControls({ 
  departments, 
  selectedDepartments = [],
  onDepartmentsChange,
  viewMode, 
  onViewModeChange,
  faculties = [],
  selectedFaculties = [],
  onFacultiesChange,
  rooms = [],
  selectedRooms = [],
  onRoomsChange,
  staff = [],
  selectedStaff = [],
  onStaffChange,
  searchTerm = '',
  onSearchChange,
}: FilterControlsProps) {
  const [localSearchTerm, setLocalSearchTerm] = useState(searchTerm);
  const [advancedFiltersVisible, setAdvancedFiltersVisible] = useState(false);
  
  const activeFiltersCount = [
    selectedDepartments.length > 0,
    selectedFaculties.length > 0,
    selectedRooms.length > 0,
    selectedStaff.length > 0,
    searchTerm.length > 0
  ].filter(Boolean).length;

  const clearAllFilters = () => {
    onDepartmentsChange?.([]);
    onFacultiesChange?.([]);
    onRoomsChange?.([]);
    onStaffChange?.([]);
    onSearchChange?.('');
    setLocalSearchTerm('');
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchChange?.(localSearchTerm);
  };
  
  const MultiSelectFilter = ({ label, options, selected, onChange, placeholder }: { label: string; options: string[]; selected: string[]; onChange: (values: string[]) => void; placeholder: string; }) => (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium min-w-fit">{label}:</label>
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="outline" className="justify-between min-w-32">
            {selected.length === 0 ? placeholder : `${selected.length} selected`}
            <ChevronDown className="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 p-3">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-medium">{label}</span>
              {selected.length > 0 && (
                <Button variant="ghost" size="sm" onClick={() => onChange([])} className="h-6 px-2">Clear</Button>
              )}
            </div>
            <Separator />
            <div className="max-h-48 overflow-y-auto space-y-2">
              {options.map(option => (
                <div key={option} className="flex items-center space-x-2">
                  <Checkbox
                    id={`${label}-${option}`}
                    checked={selected.includes(option)}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        onChange([...selected, option]);
                      } else {
                        onChange(selected.filter(item => item !== option));
                      }
                    }}
                  />
                  <label htmlFor={`${label}-${option}`} className="text-sm flex-1 cursor-pointer">{option}</label>
                </div>
              ))}
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );

  return (
    <Card className="p-4">
      <div className="space-y-4">
        <div className="flex flex-wrap gap-4 items-center justify-between">
          {viewMode && onViewModeChange && (
            <div className="flex gap-2">
              <Button variant={viewMode === 'date' ? 'default' : 'outline'} onClick={() => onViewModeChange('date')} size="sm"><Calendar className="h-4 w-4 mr-2"/>Date View</Button>
              <Button variant={viewMode === 'room' ? 'default' : 'outline'} onClick={() => onViewModeChange('room')} size="sm"><MapPin className="h-4 w-4 mr-2"/>Room View</Button>
              <Button variant={viewMode === 'invigilator' ? 'default' : 'outline'} onClick={() => onViewModeChange('invigilator')} size="sm"><User className="h-4 w-4 mr-2"/>Invigilator View</Button>
            </div>
          )}

          <div className="flex items-center gap-2">
            {onSearchChange && (
              <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
                <div className="relative">
                  <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input placeholder="Search exams, courses, rooms..." value={localSearchTerm} onChange={(e) => setLocalSearchTerm(e.target.value)} className="pl-9 w-64"/>
                </div>
              </form>
            )}
            <Button variant="outline" size="sm" onClick={() => setAdvancedFiltersVisible(!advancedFiltersVisible)} className="flex items-center gap-2">
              <Filter className="h-4 w-4" />
              Filters
              {activeFiltersCount > 0 && (<Badge variant="secondary" className="ml-1 h-5 w-5 p-0 text-xs">{activeFiltersCount}</Badge>)}
            </Button>
          </div>
        </div>

        {advancedFiltersVisible && (
          <div className="border-t pt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {onDepartmentsChange && <MultiSelectFilter label="Departments" options={departments} selected={selectedDepartments} onChange={onDepartmentsChange} placeholder="All Departments" />}
              {onFacultiesChange && <MultiSelectFilter label="Faculties" options={faculties} selected={selectedFaculties} onChange={onFacultiesChange} placeholder="All Faculties" />}
              {onRoomsChange && <MultiSelectFilter label="Rooms" options={rooms} selected={selectedRooms} onChange={onRoomsChange} placeholder="All Rooms" />}
              {onStaffChange && <MultiSelectFilter label="Staff" options={staff} selected={selectedStaff} onChange={onStaffChange} placeholder="All Staff" />}
            </div>
             {activeFiltersCount > 0 && (
                <Button variant="ghost" size="sm" onClick={clearAllFilters} className="text-muted-foreground hover:text-foreground mt-4">
                    <X className="h-4 w-4 mr-1" /> Clear All Filters
                </Button>
             )}
          </div>
        )}
      </div>
    </Card>
  );
}