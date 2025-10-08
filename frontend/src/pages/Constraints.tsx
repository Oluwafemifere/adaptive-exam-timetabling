// frontend/src/pages/Constraints.tsx
import React, { useState, useMemo, useEffect } from 'react';
import { Sliders, Save, RotateCcw, Info, AlertTriangle, Settings2, Loader2 } from 'lucide-react';
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
import { useAppStore } from '../store';
import { Constraint, ConstraintCategory, ConstraintParameter } from '../store/types';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

// Define a local type for the component's state to handle UI-specific properties like 'id'
interface LocalConstraint extends Omit<Constraint, 'parameters'> {
  id: string; // Use rule_id for a stable ID
  parameters: ConstraintParameter[];
}

// Helper to group constraints by category for rendering.
const groupConstraintsByCategory = (constraints: LocalConstraint[]): ConstraintCategory[] => {
  const categoriesMap: { [key: string]: { name: string, id: string, constraints: LocalConstraint[] } } = {};

  constraints.forEach(c => {
    const categoryName = c.category || "Uncategorized"; // Use category name from API
    if (!categoriesMap[categoryName]) {
        categoriesMap[categoryName] = { 
            name: categoryName, 
            id: categoryName, 
            constraints: [] 
        };
    }
    categoriesMap[categoryName].constraints.push(c);
  });

  return Object.values(categoriesMap)
    .filter(cat => cat.constraints.length > 0)
    .sort((a, b) => a.name.localeCompare(b.name)); // Sort for consistent order
};

// Helper to transform parameters between API (object) and UI (array) formats
const transformParameters = {
  fromApi: (params: Record<string, any>): ConstraintParameter[] => {
    return Object.entries(params || {}).map(([key, value]) => ({
      key,
      value,
      type: typeof value === 'number' ? 'int' : 'text',
    }));
  },
  toApi: (params: ConstraintParameter[]): Record<string, any> => {
    return params.reduce((acc, param) => {
      acc[param.key] = param.value;
      return acc;
    }, {} as Record<string, any>);
  }
};

export function Constraints() {
  const {
    configurations,
    activeConfigurationId,
    activeConfigurationDetails,
    fetchAndSetActiveConfiguration,
    updateAndSaveActiveConfiguration,
  } = useAppStore();

  const [localConstraints, setLocalConstraints] = useState<LocalConstraint[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (activeConfigurationDetails?.rules) {
      const transformed: LocalConstraint[] = activeConfigurationDetails.rules.map(rule => ({
        ...rule,
        id: rule.rule_id, // Map rule_id to id for component key consistency
        parameters: transformParameters.fromApi(rule.parameters),
      }));
      setLocalConstraints(JSON.parse(JSON.stringify(transformed)));
    }
  }, [activeConfigurationDetails]);

  const groupedConstraints = useMemo(() => {
    if (!localConstraints) return [];
    return groupConstraintsByCategory(localConstraints);
  }, [localConstraints]);

  const updateConstraint = (id: string, updates: Partial<LocalConstraint>) => {
    setLocalConstraints(prev => prev.map(c => c.id === id ? { ...c, ...updates } : c));
  };
  
  const updateParameter = (constraintId: string, paramKey: string, value: any) => {
    setLocalConstraints(prev => prev.map(c => {
      if (c.id === constraintId) {
        return {
          ...c,
          parameters: c.parameters.map((p: ConstraintParameter) => p.key === paramKey ? { ...p, value } : p)
        };
      }
      return c;
    }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    const payloadForApi: Constraint[] = localConstraints.map(c => ({
      ...c,
      parameters: transformParameters.toApi(c.parameters),
    }));
    await updateAndSaveActiveConfiguration({ constraints: payloadForApi });
    setIsSaving(false);
  };

  const handleReset = () => {
    if (activeConfigurationDetails?.rules) {
       const transformed: LocalConstraint[] = activeConfigurationDetails.rules.map(rule => ({
        ...rule,
        id: rule.rule_id,
        parameters: transformParameters.fromApi(rule.parameters),
      }));
      setLocalConstraints(JSON.parse(JSON.stringify(transformed)));
      toast.info('Changes have been discarded.');
    }
  };

  const hardConstraints = localConstraints.filter(c => c.type === 'hard');
  const softConstraints = localConstraints.filter(c => c.type === 'soft');
  const enabledHard = hardConstraints.filter(c => c.is_enabled).length;
  const enabledSoft = softConstraints.filter(c => c.is_enabled).length;

  if (!activeConfigurationDetails) {
    return (
      <div className="flex justify-center items-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="ml-4 text-muted-foreground">Loading configuration...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Constraint Configuration</h1>
          <p className="text-muted-foreground">Define rules and priorities for the scheduling solver</p>
        </div>
        <div className="flex items-center space-x-3">
          <Select value={activeConfigurationId ?? ""} onValueChange={fetchAndSetActiveConfiguration}>
            <SelectTrigger className="w-48"><SelectValue placeholder="Select configuration..." /></SelectTrigger>
            <SelectContent>
              {configurations.map(config => (
                <SelectItem key={config.id} value={config.id}>{config.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleReset} disabled={isSaving}><RotateCcw className="h-4 w-4 mr-2" />Discard Changes</Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
            Save Changes
          </Button>
        </div>
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
                        <div className="flex items-center space-x-3"><h4 className="font-medium">{c.name}</h4><Badge variant={c.type === 'hard' ? 'destructive' : 'secondary'}>{c.type}</Badge>{!c.is_enabled && <Badge variant="outline">Disabled</Badge>}</div>
                        <p className="text-sm text-muted-foreground">{c.description}</p>
                        {c.is_enabled && c.parameters && c.parameters.length > 0 && (
                          <div className="flex flex-wrap items-center gap-4 mt-2 pt-2">
                            {c.parameters.map((param: ConstraintParameter) => (
                              <div key={param.key} className="flex items-center space-x-2">
                                <Label htmlFor={`param-${c.id}-${param.key}`} className="text-sm capitalize">{param.key.replace(/_/g, ' ')}:</Label>
                                <Input id={`param-${c.id}-${param.key}`} type={param.type === 'int' ? 'number' : 'text'} value={param.value} onChange={(e) => updateParameter(c.id, param.key, param.type === 'int' ? parseInt(e.target.value) || 0 : e.target.value)} className="w-24" />
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <Switch checked={c.is_enabled} onCheckedChange={(enabled) => updateConstraint(c.id, { is_enabled: enabled })} />
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
            <CardContent className="space-y-6 pt-6">
              {softConstraints.filter(c => c.is_enabled).map((c) => (
                <div key={c.id} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div><h4 className="font-medium">{c.name}</h4><p className="text-sm text-muted-foreground">{c.description}</p></div>
                    <div className="text-right"><div className="text-sm font-medium">Weight: {c.weight}</div></div>
                  </div>
                  <div className="px-2"><Slider value={[c.weight]} onValueChange={([value]) => updateConstraint(c.id, { weight: value })} max={100} step={5} /></div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}