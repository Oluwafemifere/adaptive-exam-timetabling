// frontend/src/pages/Constraints.tsx
import React, { useState, useMemo } from 'react';
import { Sliders, Save, RotateCcw, Info, AlertTriangle, Settings2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { Slider } from '../components/ui/slider';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Alert, AlertDescription } from '../components/ui/alert';
import { toast } from 'sonner';

// Mocked data based on the provided schema
const mockConstraintCategories = [
  { id: "ddebed4a-df48-4de1-91ba-7fa1d5259341", name: "Student Constraints" },
  { id: "8ff61dc2-4df9-4083-a8de-e054c611862b", name: "Spatial Constraints" },
  { id: "d89afdcf-b144-40f4-a714-b2790ce75242", name: "Resource Constraints" },
  { id: "f32b7704-139d-44c2-887b-30d9e6284c18", name: "Pedagogical Constraints" },
  { id: "88e49d5a-f9dc-4e17-a06a-733332167a5a", name: "Fairness Constraints" },
];

const mockConstraintRules = [
  { id: "fe64ceb0-cb54-4ad4-8279-ba534394465f", name: "Student Time Conflict", description: "A student cannot take two exams at the same time.", type: "hard", definition: { parameters: [] }, categoryId: "ddebed4a-df48-4de1-91ba-7fa1d5259341", defaultWeight: 100, isEnabled: true },
  { id: "c4791ccc-27a5-45f8-8733-61c6e5654af6", name: "Max Exams Per Student Per Day", description: "A student cannot take more than a specified number of exams in a single day.", type: "hard", definition: { parameters: [{ key: "max_exams_per_day", type: "int", value: 2 }] }, categoryId: "ddebed4a-df48-4de1-91ba-7fa1d5259341", defaultWeight: 100, isEnabled: true },
  { id: "ee43d90b-9361-4d49-93a8-4b38fee4a080", name: "Minimum Gap Between Exams", description: "Penalizes scheduling a student's exams too close together on the same day.", type: "soft", definition: { parameters: [{ key: "min_gap_slots", type: "int", value: 1 }] }, categoryId: "ddebed4a-df48-4de1-91ba-7fa1d5259341", defaultWeight: 80, isEnabled: true },
  { id: "ff1bb276-74d2-48b3-bcc7-42b601c8a2aa", name: "Carryover Student Conflict", description: "Allow, but penalize, scheduling conflicts for students with a 'carryover' registration status.", type: "soft", definition: { parameters: [{ key: "max_allowed_conflicts", type: "int", value: 3 }] }, categoryId: "ddebed4a-df48-4de1-91ba-7fa1d5259341", defaultWeight: 50, isEnabled: true },
  { id: "26224d75-0ae9-4943-aa2c-df57e8d15347", name: "Room Capacity Exceeded", description: "The number of students in a room cannot exceed its exam capacity.", type: "hard", definition: { parameters: [] }, categoryId: "8ff61dc2-4df9-4083-a8de-e054c611862b", defaultWeight: 100, isEnabled: true },
  { id: "96f93610-d75f-4275-95df-996c11ff283d", name: "Room Overbooking Penalty", description: "Penalize assigning more students to a room than its capacity (for overbookable rooms).", type: "soft", definition: { parameters: [] }, categoryId: "8ff61dc2-4df9-4083-a8de-e054c611862b", defaultWeight: 5, isEnabled: true },
  { id: "0f5b0da7-dfdd-420d-a4c3-df3ff7273494", name: "Minimum Invigilators", description: "Ensure enough invigilators are assigned per room based on student count.", type: "hard", definition: { parameters: [{ key: "students_per_invigilator", type: "int", value: 50 }] }, categoryId: "d89afdcf-b144-40f4-a714-b2790ce75242", defaultWeight: 100, isEnabled: true },
  { id: "6e7577db-a0de-4fdb-abc2-c2debebb4d05", name: "Invigilator Availability", description: "Penalize assigning invigilators during their stated unavailable times.", type: "soft", definition: { parameters: [] }, categoryId: "d89afdcf-b144-40f4-a714-b2790ce75242", defaultWeight: 75, isEnabled: false },
  { id: "b10c9f01-b365-4464-accf-14d9bbc4ea14", name: "Course Slot Preference", description: "Penalize scheduling exams outside of their preferred slots (e.g., 'morning only').", type: "soft", definition: { parameters: [] }, categoryId: "f32b7704-139d-44c2-887b-30d9e6284c18", defaultWeight: 10, isEnabled: true },
  { id: "5e83ab46-8073-456e-8f3b-f53ebd92d1c6", name: "Instructor Self-Invigilation", description: "An instructor for a course cannot invigilate the exam for that same course.", type: "hard", definition: { parameters: [] }, categoryId: "f32b7704-139d-44c2-887b-30d9e6284c18", defaultWeight: 100, isEnabled: true },
  { id: "7033d920-b92f-4d48-8719-49cd3de1df4e", name: "Invigilator Workload Balance", description: "Penalize uneven distribution of total invigilation slots among staff.", type: "soft", definition: { parameters: [] }, categoryId: "88e49d5a-f9dc-4e17-a06a-733332167a5a", defaultWeight: 15, isEnabled: true },
  { id: "21e76918-c11c-4a6b-a908-ce0f0fd48d33", name: "Daily Exam Load Balance", description: "Penalize uneven distribution of the total number of exams scheduled across different days.", type: "soft", definition: { parameters: [] }, categoryId: "88e49d5a-f9dc-4e17-a06a-733332167a5a", defaultWeight: 10, isEnabled: true },
];

export function Constraints() {
  const [constraints, setConstraints] = useState(mockConstraintRules);

  const groupedConstraints = useMemo(() => {
    return mockConstraintCategories.map(category => ({
      ...category,
      constraints: constraints.filter(c => c.categoryId === category.id)
    })).filter(group => group.constraints.length > 0);
  }, [constraints]);

  const updateConstraint = (id: string, updates: Partial<typeof constraints[0]>) => {
    setConstraints(prev => prev.map(c => c.id === id ? { ...c, ...updates } : c));
  };
  
  const updateParameter = (constraintId: string, paramKey: string, value: any) => {
    setConstraints(prev => prev.map(c => {
      if (c.id === constraintId) {
        return {
          ...c,
          definition: {
            ...c.definition,
            parameters: c.definition.parameters.map(p => p.key === paramKey ? { ...p, value } : p)
          }
        };
      }
      return c;
    }));
  };

  const saveConstraints = () => toast.success('Constraints saved successfully');
  const resetToDefaults = () => { setConstraints(mockConstraintRules); toast.info('Constraints reset to default values'); };

  const hardConstraints = constraints.filter(c => c.type === 'hard');
  const softConstraints = constraints.filter(c => c.type === 'soft');
  const enabledHard = hardConstraints.filter(c => c.isEnabled).length;
  const enabledSoft = softConstraints.filter(c => c.isEnabled).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-semibold">Constraint Configuration</h1><p className="text-muted-foreground">Define rules and priorities for the scheduling solver</p></div>
        <div className="flex items-center space-x-3"><Button variant="outline" onClick={resetToDefaults}><RotateCcw className="h-4 w-4 mr-2" />Reset</Button><Button onClick={saveConstraints}><Save className="h-4 w-4 mr-2" />Save Changes</Button></div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card><CardContent className="p-4 flex items-center space-x-3"><div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-full"><AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-300" /></div><div><p className="text-sm text-muted-foreground">Hard Constraints</p><p className="text-lg font-semibold">{enabledHard} / {hardConstraints.length} Enabled</p></div></CardContent></Card>
        <Card><CardContent className="p-4 flex items-center space-x-3"><div className="p-2 bg-blue-100 dark:bg-blue-900/50 rounded-full"><Sliders className="h-4 w-4 text-blue-600 dark:text-blue-300" /></div><div><p className="text-sm text-muted-foreground">Soft Constraints</p><p className="text-lg font-semibold">{enabledSoft} / {softConstraints.length} Enabled</p></div></CardContent></Card>
      </div>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2"><TabsTrigger value="general">General Constraints</TabsTrigger><TabsTrigger value="weights">Weights & Priorities</TabsTrigger></TabsList>
        <TabsContent value="general" className="space-y-6">
          <Alert><Info className="h-4 w-4" /><AlertDescription>Hard constraints must be satisfied. Soft constraints are preferences that the solver will try to optimize.</AlertDescription></Alert>
          {groupedConstraints.map(group => (
            <Card key={group.id}>
              <CardHeader><CardTitle className="flex items-center space-x-2"><Settings2 className="h-5 w-5" /><span>{group.name}</span></CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {group.constraints.map((c, index) => (
                  <div key={c.id}>
                    <div className="flex items-start justify-between py-3">
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center space-x-3"><h4 className="font-medium">{c.name}</h4><Badge variant={c.type === 'hard' ? 'destructive' : 'secondary'}>{c.type}</Badge>{!c.isEnabled && <Badge variant="outline">Disabled</Badge>}</div>
                        <p className="text-sm text-muted-foreground">{c.description}</p>
                        {c.isEnabled && c.definition.parameters.length > 0 && (
                          <div className="flex flex-wrap items-center gap-4 mt-2 pt-2">
                            {c.definition.parameters.map(param => (
                              <div key={param.key} className="flex items-center space-x-2">
                                <Label htmlFor={`param-${c.id}-${param.key}`} className="text-sm capitalize">{param.key.replace(/_/g, ' ')}:</Label>
                                <Input id={`param-${c.id}-${param.key}`} type={param.type === 'int' ? 'number' : 'text'} value={param.value} onChange={(e) => updateParameter(c.id, param.key, param.type === 'int' ? parseInt(e.target.value) : e.target.value)} className="w-24" />
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <Switch checked={c.isEnabled} onCheckedChange={(enabled) => updateConstraint(c.id, { isEnabled: enabled })} />
                    </div>
                    {index < group.constraints.length - 1 && <Separator />}
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </TabsContent>
        <TabsContent value="weights" className="space-y-6">
          <Alert><Info className="h-4 w-4" /><AlertDescription>Adjust the relative importance of soft constraints. Higher weights mean higher priority.</AlertDescription></Alert>
          <Card>
            <CardHeader><CardTitle>Soft Constraint Priorities</CardTitle><CardDescription>Adjust weights for enabled soft constraints (0-100).</CardDescription></CardHeader>
            <CardContent className="space-y-6">
              {softConstraints.filter(c => c.isEnabled).map((c) => (
                <div key={c.id} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div><h4 className="font-medium">{c.name}</h4><p className="text-sm text-muted-foreground">{c.description}</p></div>
                    <div className="text-right"><div className="text-sm font-medium">Weight: {c.defaultWeight}</div></div>
                  </div>
                  <div className="px-2"><Slider value={[c.defaultWeight]} onValueChange={([value]) => updateConstraint(c.id, { defaultWeight: value })} max={100} step={5} /></div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}