import React, { useState } from 'react';
import { 
  Sliders, 
  Save, 
  RotateCcw, 
  Info,
  AlertTriangle,
  CheckCircle2,
  Settings2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Switch } from '../components/ui/switch'
import { Slider } from '../components/ui/slider'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Badge } from '../components/ui/badge'
import { Separator } from '../components/ui/separator'
import { Alert, AlertDescription } from '../components/ui/alert'
import { toast } from 'sonner'

interface Constraint {
  id: string;
  name: string;
  description: string;
  type: 'hard' | 'soft';
  enabled: boolean;
  threshold?: number;
  weight?: number;
}

interface ConstraintGroup {
  name: string;
  description: string;
  constraints: Constraint[];
}

export function Constraints() {
  const [constraints, setConstraints] = useState<ConstraintGroup[]>([
    {
      name: 'Student Constraints',
      description: 'Rules related to student scheduling and conflicts',
      constraints: [
        {
          id: 'student-conflict',
          name: 'Student Conflict',
          description: 'Prevent students from having overlapping exams',
          type: 'hard',
          enabled: true,
        },
        {
          id: 'max-exams-per-day',
          name: 'Max Exams Per Day',
          description: 'Limit the number of exams a student can have in one day',
          type: 'soft',
          enabled: true,
          threshold: 2,
          weight: 80,
        },
        {
          id: 'back-to-back-exams',
          name: 'Back-to-Back Exams',
          description: 'Avoid consecutive exams for students',
          type: 'soft',
          enabled: true,
          weight: 60,
        },
      ]
    },
    {
      name: 'Room Constraints',
      description: 'Rules related to room capacity and availability',
      constraints: [
        {
          id: 'room-capacity',
          name: 'Room Capacity',
          description: 'Ensure room capacity is not exceeded',
          type: 'hard',
          enabled: true,
        },
        {
          id: 'room-availability',
          name: 'Room Availability',
          description: 'Check room availability for scheduled times',
          type: 'hard',
          enabled: true,
        },
        {
          id: 'room-type-match',
          name: 'Room Type Matching',
          description: 'Match exam requirements with room facilities',
          type: 'soft',
          enabled: true,
          weight: 70,
        },
      ]
    },
    {
      name: 'Staff Constraints',
      description: 'Rules related to invigilator scheduling and availability',
      constraints: [
        {
          id: 'invigilator-availability',
          name: 'Invigilator Availability',
          description: 'Ensure invigilators are available for assigned slots',
          type: 'hard',
          enabled: true,
        },
        {
          id: 'max-invigilation-hours',
          name: 'Max Invigilation Hours',
          description: 'Limit daily invigilation hours per staff member',
          type: 'soft',
          enabled: true,
          threshold: 6,
          weight: 50,
        },
        {
          id: 'staff-travel-time',
          name: 'Staff Travel Time',
          description: 'Allow time for staff to travel between buildings',
          type: 'soft',
          enabled: false,
          weight: 30,
        },
      ]
    },
    {
      name: 'Timing Constraints',
      description: 'Rules related to exam timing and duration',
      constraints: [
        {
          id: 'exam-duration',
          name: 'Exam Duration',
          description: 'Respect specified exam durations',
          type: 'hard',
          enabled: true,
        },
        {
          id: 'preferred-time-slots',
          name: 'Preferred Time Slots',
          description: 'Schedule exams in preferred time slots when possible',
          type: 'soft',
          enabled: true,
          weight: 40,
        },
        {
          id: 'spreading-exams',
          name: 'Spreading Exams',
          description: 'Distribute exams evenly across the exam period',
          type: 'soft',
          enabled: true,
          weight: 90,
        },
      ]
    }
  ]);

  const updateConstraint = (groupIndex: number, constraintIndex: number, updates: Partial<Constraint>) => {
    const newConstraints = [...constraints];
    newConstraints[groupIndex].constraints[constraintIndex] = {
      ...newConstraints[groupIndex].constraints[constraintIndex],
      ...updates
    };
    setConstraints(newConstraints);
  };

  const saveConstraints = () => {
    // In a real app, this would save to the backend
    toast.success('Constraints saved successfully');
  };

  const resetToDefaults = () => {
    // In a real app, this would reset to default values
    toast.info('Constraints reset to default values');
  };

  const hardConstraints = constraints.flatMap(group => 
    group.constraints.filter(c => c.type === 'hard')
  );
  const softConstraints = constraints.flatMap(group => 
    group.constraints.filter(c => c.type === 'soft')
  );

  const enabledHardConstraints = hardConstraints.filter(c => c.enabled).length;
  const enabledSoftConstraints = softConstraints.filter(c => c.enabled).length;

  return (
    <div className="space-y-6">
      {/* Header with Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Constraint Configuration</h1>
          <p className="text-muted-foreground">Define rules and priorities for the scheduling solver</p>
        </div>
        <div className="flex items-center space-x-3">
          <Button variant="outline" onClick={resetToDefaults}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset to Defaults
          </Button>
          <Button onClick={saveConstraints}>
            <Save className="h-4 w-4 mr-2" />
            Save Changes
          </Button>
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-full">
                <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Hard Constraints</p>
                <p className="text-lg font-semibold">
                  {enabledHardConstraints} / {hardConstraints.length} Enabled
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/50 rounded-full">
                <Sliders className="h-4 w-4 text-blue-600 dark:text-blue-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Soft Constraints</p>
                <p className="text-lg font-semibold">
                  {enabledSoftConstraints} / {softConstraints.length} Enabled
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-green-100 dark:bg-green-900/50 rounded-full">
                <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-300" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Configuration</p>
                <p className="text-lg font-semibold">Valid</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Configuration */}
      <Tabs defaultValue="general" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="general">General Constraints</TabsTrigger>
          <TabsTrigger value="weights">Weights & Priorities</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Hard constraints must be satisfied for a valid schedule. Soft constraints are preferences that will be optimized when possible.
            </AlertDescription>
          </Alert>

          {constraints.map((group, groupIndex) => (
            <Card key={group.name}>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings2 className="h-5 w-5" />
                  <span>{group.name}</span>
                </CardTitle>
                <CardDescription>{group.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {group.constraints.map((constraint, constraintIndex) => (
                  <div key={constraint.id}>
                    <div className="flex items-center justify-between py-3">
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center space-x-3">
                          <h4 className="font-medium">{constraint.name}</h4>
                          <Badge variant={constraint.type === 'hard' ? 'destructive' : 'secondary'}>
                            {constraint.type}
                          </Badge>
                          {!constraint.enabled && (
                            <Badge variant="outline">Disabled</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {constraint.description}
                        </p>
                        
                        {/* Threshold input for applicable constraints */}
                        {constraint.threshold !== undefined && constraint.enabled && (
                          <div className="flex items-center space-x-3 mt-2">
                            <Label htmlFor={`threshold-${constraint.id}`} className="text-sm">
                              Threshold:
                            </Label>
                            <Input
                              id={`threshold-${constraint.id}`}
                              type="number"
                              value={constraint.threshold}
                              onChange={(e) => updateConstraint(groupIndex, constraintIndex, {
                                threshold: parseInt(e.target.value)
                              })}
                              className="w-20"
                              min="1"
                              max="10"
                            />
                          </div>
                        )}
                      </div>
                      <Switch
                        checked={constraint.enabled}
                        onCheckedChange={(enabled) => 
                          updateConstraint(groupIndex, constraintIndex, { enabled })
                        }
                      />
                    </div>
                    {constraintIndex < group.constraints.length - 1 && <Separator />}
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="weights" className="space-y-6">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Adjust the relative importance of soft constraints. Higher weights mean higher priority in optimization.
            </AlertDescription>
          </Alert>

          <Card>
            <CardHeader>
              <CardTitle>Soft Constraint Priorities</CardTitle>
              <CardDescription>
                Drag the sliders to adjust constraint weights (0-100)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {softConstraints.filter(c => c.enabled).map((constraint) => (
                <div key={constraint.id} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium">{constraint.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        {constraint.description}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium">Weight: {constraint.weight}</div>
                      <div className="text-xs text-muted-foreground">
                        {constraint.weight && constraint.weight >= 80 ? 'Very High' :
                         constraint.weight && constraint.weight >= 60 ? 'High' :
                         constraint.weight && constraint.weight >= 40 ? 'Medium' :
                         constraint.weight && constraint.weight >= 20 ? 'Low' : 'Very Low'}
                      </div>
                    </div>
                  </div>
                  <div className="px-2">
                    <Slider
                      value={[constraint.weight || 50]}
                      onValueChange={([value]) => {
                        const groupIndex = constraints.findIndex(group => 
                          group.constraints.some(c => c.id === constraint.id)
                        );
                        const constraintIndex = constraints[groupIndex].constraints.findIndex(c => c.id === constraint.id);
                        updateConstraint(groupIndex, constraintIndex, { weight: value });
                      }}
                      max={100}
                      step={5}
                      className="w-full"
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}