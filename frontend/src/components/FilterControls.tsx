import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";
import { Checkbox } from "./ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";
import { Separator } from "./ui/separator";
import { X, Search, Filter, ChevronDown, Save, Bookmark, Settings } from "lucide-react";
import { useState } from "react";

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
  // Support both old and new interface
  selectedDepartments?: string[];
  onDepartmentsChange?: (departments: string[]) => void;
  // Legacy single-select support for backward compatibility
  selectedDepartment?: string;
  onDepartmentChange?: (department: string) => void;
  viewMode: 'general' | 'department';
  onViewModeChange: (mode: 'general' | 'department') => void;
  // Enhanced filter props
  faculties?: string[];
  selectedFaculties?: string[];
  onFacultiesChange?: (faculties: string[]) => void;
  rooms?: string[];
  selectedRooms?: string[];
  onRoomsChange?: (rooms: string[]) => void;
  staff?: string[];
  selectedStaff?: string[];
  onStaffChange?: (staff: string[]) => void;
  students?: string[];
  selectedStudents?: string[];
  onStudentsChange?: (students: string[]) => void;
  searchTerm?: string;
  onSearchChange?: (term: string) => void;
  showAdvancedFilters?: boolean;
  onAdvancedFiltersToggle?: () => void;
  // Filter presets
  filterPresets?: FilterPreset[];
  onSavePreset?: (preset: Omit<FilterPreset, 'id'>) => void;
  onLoadPreset?: (preset: FilterPreset) => void;
}

export function FilterControls({ 
  departments, 
  selectedDepartments,
  onDepartmentsChange,
  selectedDepartment,
  onDepartmentChange,
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
  students = [],
  selectedStudents = [],
  onStudentsChange,
  searchTerm = '',
  onSearchChange,
  showAdvancedFilters = false,
  onAdvancedFiltersToggle,
  filterPresets = [],
  onSavePreset,
  onLoadPreset
}: FilterControlsProps) {
  const [localSearchTerm, setLocalSearchTerm] = useState(searchTerm);
  const [showPresetDialog, setShowPresetDialog] = useState(false);
  const [presetName, setPresetName] = useState('');
  
  // Handle backward compatibility for single department selection
  const actualSelectedDepartments = selectedDepartments || (selectedDepartment && selectedDepartment !== 'all' ? [selectedDepartment] : []);
  const actualOnDepartmentsChange = onDepartmentsChange || ((depts: string[]) => {
    if (onDepartmentChange) {
      onDepartmentChange(depts.length > 0 ? depts[0] : 'all');
    }
  });
  
  const activeFiltersCount = [
    actualSelectedDepartments.length > 0,
    (selectedFaculties || []).length > 0,
    (selectedRooms || []).length > 0,
    (selectedStaff || []).length > 0,
    (selectedStudents || []).length > 0,
    (searchTerm || '').length > 0
  ].filter(Boolean).length;

  const clearAllFilters = () => {
    actualOnDepartmentsChange([]);
    onFacultiesChange?.([]);
    onRoomsChange?.([]);
    onStaffChange?.([]);
    onStudentsChange?.([]);
    onSearchChange?.('');
    setLocalSearchTerm('');
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchChange?.(localSearchTerm);
  };

  const handleSavePreset = () => {
    if (presetName.trim() && onSavePreset) {
      onSavePreset({
        name: presetName.trim(),
        departments: actualSelectedDepartments,
        faculties: selectedFaculties || [],
        rooms: selectedRooms || [],
        staff: selectedStaff || [],
        searchTerm: searchTerm || ''
      });
      setPresetName('');
      setShowPresetDialog(false);
    }
  };

  const MultiSelectFilter = ({ 
    label, 
    options, 
    selected, 
    onChange, 
    placeholder 
  }: {
    label: string;
    options: string[];
    selected: string[];
    onChange: (values: string[]) => void;
    placeholder: string;
  }) => (
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
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onChange([])}
                  className="h-6 px-2"
                >
                  Clear
                </Button>
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
                  <label
                    htmlFor={`${label}-${option}`}
                    className="text-sm flex-1 cursor-pointer"
                  >
                    {option}
                  </label>
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
        {/* View Mode and Search */}
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex gap-2">
            <Button
              variant={viewMode === 'general' ? 'default' : 'outline'}
              onClick={() => onViewModeChange('general')}
              size="sm"
            >
              General View
            </Button>
            <Button
              variant={viewMode === 'department' ? 'default' : 'outline'}
              onClick={() => onViewModeChange('department')}
              size="sm"
            >
              Department View
            </Button>
          </div>

          <div className="flex items-center gap-2">
            {onSearchChange && (
              <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
                <div className="relative">
                  <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
                  <Input
                    placeholder="Search exams, courses, rooms..."
                    value={localSearchTerm}
                    onChange={(e) => setLocalSearchTerm(e.target.value)}
                    className="pl-9 w-64"
                  />
                </div>
              </form>
            )}
            
            {/* Filter Presets */}
            {filterPresets.length > 0 && (
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Bookmark className="h-4 w-4 mr-2" />
                    Presets
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-56">
                  <div className="space-y-2">
                    <div className="font-medium">Filter Presets</div>
                    <Separator />
                    {filterPresets.map(preset => (
                      <Button
                        key={preset.id}
                        variant="ghost"
                        size="sm"
                        className="w-full justify-start"
                        onClick={() => onLoadPreset?.(preset)}
                      >
                        {preset.name}
                      </Button>
                    ))}
                  </div>
                </PopoverContent>
              </Popover>
            )}
            
            {onSavePreset && activeFiltersCount > 0 && (
              <Popover open={showPresetDialog} onOpenChange={setShowPresetDialog}>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Save className="h-4 w-4 mr-2" />
                    Save
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-64">
                  <div className="space-y-3">
                    <div className="font-medium">Save Filter Preset</div>
                    <Input
                      placeholder="Preset name"
                      value={presetName}
                      onChange={(e) => setPresetName(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSavePreset()}
                    />
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={handleSavePreset}
                        disabled={!presetName.trim()}
                        className="flex-1"
                      >
                        Save
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowPresetDialog(false)}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                </PopoverContent>
              </Popover>
            )}
          
            {onAdvancedFiltersToggle && (
              <Button
                variant="outline"
                size="sm"
                onClick={onAdvancedFiltersToggle}
                className="flex items-center gap-2"
              >
                <Filter className="h-4 w-4" />
                Filters
                {activeFiltersCount > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 w-5 p-0 text-xs">
                    {activeFiltersCount}
                  </Badge>
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Basic Filters */}
        <div className="flex flex-wrap gap-4 items-center">
          {/* Handle both single and multi-select for departments */}
          {selectedDepartments !== undefined || onDepartmentsChange ? (
            <MultiSelectFilter
              label="Departments"
              options={departments || []}
              selected={actualSelectedDepartments}
              onChange={actualOnDepartmentsChange}
              placeholder="All Departments"
            />
          ) : (
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Department:</label>
              <Select value={selectedDepartment || 'all'} onValueChange={onDepartmentChange}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Select department" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Departments</SelectItem>
                  {(departments || []).map(dept => (
                    <SelectItem key={dept} value={dept}>
                      {dept}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {activeFiltersCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4 mr-1" />
              Clear All
            </Button>
          )}
        </div>

        {/* Advanced Filters */}
        {showAdvancedFilters && (
          <div className="border-t pt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {(faculties || []).length > 0 && (
                <MultiSelectFilter
                  label="Faculties"
                  options={faculties || []}
                  selected={selectedFaculties || []}
                  onChange={onFacultiesChange || (() => {})}
                  placeholder="All Faculties"
                />
              )}

              {(rooms || []).length > 0 && (
                <MultiSelectFilter
                  label="Rooms"
                  options={rooms || []}
                  selected={selectedRooms || []}
                  onChange={onRoomsChange || (() => {})}
                  placeholder="All Rooms"
                />
              )}

              {(staff || []).length > 0 && (
                <MultiSelectFilter
                  label="Staff"
                  options={staff || []}
                  selected={selectedStaff || []}
                  onChange={onStaffChange || (() => {})}
                  placeholder="All Staff"
                />
              )}

              {(students || []).length > 0 && (
                <MultiSelectFilter
                  label="Students"
                  options={students || []}
                  selected={selectedStudents || []}
                  onChange={onStudentsChange || (() => {})}
                  placeholder="All Students"
                />
              )}
            </div>
          </div>
        )}

        {/* Active Filters Display */}
        {activeFiltersCount > 0 && (
          <div className="flex flex-wrap gap-2">
            <span className="text-sm font-medium">Active filters:</span>
            {actualSelectedDepartments.length > 0 && (
              <Badge variant="secondary" className="flex items-center gap-1">
                Departments: {actualSelectedDepartments.length}
                <X 
                  className="h-3 w-3 cursor-pointer" 
                  onClick={() => actualOnDepartmentsChange([])} 
                />
              </Badge>
            )}
            {(selectedFaculties || []).length > 0 && (
              <Badge variant="secondary" className="flex items-center gap-1">
                Faculties: {(selectedFaculties || []).length}
                <X 
                  className="h-3 w-3 cursor-pointer" 
                  onClick={() => onFacultiesChange?.([])} 
                />
              </Badge>
            )}
            {(selectedRooms || []).length > 0 && (
              <Badge variant="secondary" className="flex items-center gap-1">
                Rooms: {(selectedRooms || []).length}
                <X 
                  className="h-3 w-3 cursor-pointer" 
                  onClick={() => onRoomsChange?.([])} 
                />
              </Badge>
            )}
            {(selectedStaff || []).length > 0 && (
              <Badge variant="secondary" className="flex items-center gap-1">
                Staff: {(selectedStaff || []).length}
                <X 
                  className="h-3 w-3 cursor-pointer" 
                  onClick={() => onStaffChange?.([])} 
                />
              </Badge>
            )}
            {(selectedStudents || []).length > 0 && (
              <Badge variant="secondary" className="flex items-center gap-1">
                Students: {(selectedStudents || []).length}
                <X 
                  className="h-3 w-3 cursor-pointer" 
                  onClick={() => onStudentsChange?.([])} 
                />
              </Badge>
            )}
            {(searchTerm || '').length > 0 && (
              <Badge variant="secondary" className="flex items-center gap-1">
                Search: "{searchTerm}"
                <X 
                  className="h-3 w-3 cursor-pointer" 
                  onClick={() => {
                    onSearchChange?.('');
                    setLocalSearchTerm('');
                  }} 
                />
              </Badge>
            )}
          </div>
        )}

        {/* View Mode Descriptions */}
        <div className="text-sm text-muted-foreground">
          {viewMode === 'general' && (
            <span>Colors represent departments. Gradients indicate multi-department exams.</span>
          )}
          {viewMode === 'department' && (
            <span>Each exam has a distinct color for better visibility.</span>
          )}
        </div>
      </div>
    </Card>
  );
}