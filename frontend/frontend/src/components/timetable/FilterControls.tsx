import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Button } from "../ui/button";
import { Card } from "../ui/card";

interface FilterControlsProps {
  departments: string[];
  selectedDepartment: string;
  onDepartmentChange: (department: string) => void;
  viewMode: 'general' | 'department';
  onViewModeChange: (mode: 'general' | 'department') => void;
}

export function FilterControls({ 
  departments, 
  selectedDepartment, 
  onDepartmentChange, 
  viewMode, 
  onViewModeChange 
}: FilterControlsProps) {
  return (
    <Card className="p-4">
      <div className="flex flex-wrap gap-4 items-center">
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
          <label className="text-sm">Filter by Department:</label>
          <Select value={selectedDepartment} onValueChange={onDepartmentChange}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select department" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Departments</SelectItem>
              {departments.map(dept => (
                <SelectItem key={dept} value={dept}>
                  {dept}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        {viewMode === 'general' && (
          <div className="text-sm text-muted-foreground">
            Colors represent departments. Gradients indicate multi-department exams.
          </div>
        )}
        
        {viewMode === 'department' && (
          <div className="text-sm text-muted-foreground">
            Each exam has a distinct color for better visibility.
          </div>
        )}
      </div>
    </Card>
  );
}