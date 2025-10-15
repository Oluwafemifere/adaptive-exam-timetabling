// frontend/src/pages/Constraints.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { Sliders, Save, RotateCcw, Info, Settings2, Loader2, FileJson, Zap, Plus, Star } from 'lucide-react';
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
import { RuleSetting, RuleSettingRead, SystemConfigurationDetails, SystemConfigSavePayload } from '../store/types';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { ScrollArea } from '../components/ui/scroll-area';

// Helper to group rules by category
const groupRulesByCategory = (rules: RuleSettingRead[]) => {
  const categoriesMap: { [key: string]: { name: string, rules: RuleSettingRead[] } } = {};
  // This function processes ALL rules passed to it, it does not filter by enabled status.
  rules.forEach(rule => {
    const categoryName = rule.category || "Other";
    if (!categoriesMap[categoryName]) {
      categoriesMap[categoryName] = { name: categoryName, rules: [] };
    }
    categoriesMap[categoryName].rules.push(rule);
  });
  return Object.values(categoriesMap).sort((a, b) => a.name.localeCompare(b.name));
};

export function Constraints() {
  const {
    configurations,
    activeConfigurationId,
    activeConfigurationDetails,
    fetchAndSetActiveConfiguration,
    saveActiveConfiguration,
    setCurrentPage,
    createNewConfiguration,
    setDefaultConfiguration,
  } = useAppStore();

  const [localConfig, setLocalConfig] = useState<SystemConfigurationDetails | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [showRunJobDialog, setShowRunJobDialog] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newConfigData, setNewConfigData] = useState({ name: '', description: '' });
  const [selectedRuleIds, setSelectedRuleIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (activeConfigurationDetails) {
      setLocalConfig(JSON.parse(JSON.stringify(activeConfigurationDetails)));
    }
  }, [activeConfigurationDetails]);

  const groupedRules = useMemo(() => {
    if (!localConfig?.rules) return [];
    // The component state `localConfig.rules` contains the full list of constraints,
    // both enabled and disabled, ensuring all are rendered.
    return groupRulesByCategory(localConfig.rules);
  }, [localConfig]);

  const handleFieldChange = (field: keyof SystemConfigurationDetails, value: any) => {
    if (localConfig) {
      setLocalConfig({ ...localConfig, [field]: value });
    }
  };

  const handleRuleChange = (ruleId: string, updates: Partial<RuleSettingRead>) => {
    if (localConfig) {
      setLocalConfig({
        ...localConfig,
        rules: localConfig.rules.map(r => r.rule_id === ruleId ? { ...r, ...updates } : r)
      });
    }
  };

  const handleParameterChange = (ruleId: string, paramKey: string, value: any) => {
    if (localConfig) {
      setLocalConfig({
        ...localConfig,
        rules: localConfig.rules.map(r => {
          if (r.rule_id === ruleId) {
            const newParams = { ...r.parameters, [paramKey]: value };
            return { ...r, parameters: newParams };
          }
          return r;
        })
      });
    }
  };

  const handleSave = async () => {
    if (!localConfig) return;
    setIsSaving(true);
    try {
      await saveActiveConfiguration(localConfig);
      setShowRunJobDialog(true);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    if (activeConfigurationDetails) {
      setLocalConfig(JSON.parse(JSON.stringify(activeConfigurationDetails)));
      toast.info('Changes have been discarded.');
    }
  };

  const navigateToScheduling = () => {
    setCurrentPage('scheduling');
  };
  
  const handleOpenCreateModal = () => {
    if (activeConfigurationDetails) {
      const initialSelected = new Set<string>(
        activeConfigurationDetails.rules.filter(r => r.is_enabled).map(r => r.rule_id)
      );
      setSelectedRuleIds(initialSelected);
      setNewConfigData({ name: '', description: '' });
      setIsCreateModalOpen(true);
    } else {
      toast.error("Base configuration must be loaded before creating a new one.");
    }
  };

  const handleCreateNewConfiguration = async () => {
    if (!newConfigData.name.trim()) {
      toast.warning("Configuration Name is required.");
      return;
    }
    if (!activeConfigurationDetails) return;

    const allRules: RuleSetting[] = activeConfigurationDetails.rules.map(rule => ({
      rule_id: rule.rule_id,
      is_enabled: selectedRuleIds.has(rule.rule_id),
      weight: rule.weight,
      parameters: rule.parameters,
    }));

    const payload: SystemConfigSavePayload = {
      name: newConfigData.name,
      description: newConfigData.description,
      is_default: false,
      solver_parameters: activeConfigurationDetails.solver_parameters,
      rules: allRules,
    };

    setIsSaving(true);
    const success = await createNewConfiguration(payload);
    setIsSaving(false);
    if (success) {
      setIsCreateModalOpen(false);
    }
  };

  const handleSetDefault = async () => {
    if (!activeConfigurationId || localConfig?.is_default) return;
    setIsSaving(true);
    await setDefaultConfiguration(activeConfigurationId);
    setIsSaving(false);
  };


  if (!localConfig) {
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
          <p className="text-muted-foreground">Define rules and priorities for the scheduling solver.</p>
        </div>
        <div className="flex items-center space-x-3">
          <Select value={activeConfigurationId ?? ""} onValueChange={fetchAndSetActiveConfiguration}>
            <SelectTrigger className="w-64"><SelectValue placeholder="Select a configuration..." /></SelectTrigger>
            <SelectContent>
              {configurations.map(config => (
                <SelectItem key={config.id} value={config.id}>
                  <div className="flex items-center">
                    {config.name} {config.is_default && <Badge variant="secondary" className="ml-2">Default</Badge>}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleOpenCreateModal}><Plus className="h-4 w-4 mr-2" />Create New</Button>
          <Button variant="outline" onClick={handleReset} disabled={isSaving}><RotateCcw className="h-4 w-4 mr-2" />Discard</Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
            Save Changes
          </Button>
        </div>
      </div>
      
      <Card>
          <CardHeader>
              <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                        {localConfig.name}
                        {localConfig.is_default && <Badge>Default</Badge>}
                    </CardTitle>
                    <CardDescription>Edit the name, description, and solver settings for this profile.</CardDescription>
                  </div>
                  <Button variant="outline" onClick={handleSetDefault} disabled={isSaving || localConfig.is_default}>
                      <Star className="h-4 w-4 mr-2"/> Set as Default
                  </Button>
              </div>
          </CardHeader>
          <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                      <Label htmlFor="config-name">Configuration Name</Label>
                      <Input id="config-name" value={localConfig.name} onChange={(e) => handleFieldChange('name', e.target.value)} />
                  </div>
                  <div className="space-y-2">
                      <Label htmlFor="config-desc">Description</Label>
                      <Input id="config-desc" value={localConfig.description || ''} onChange={(e) => handleFieldChange('description', e.target.value)} />
                  </div>
              </div>
              <div className="space-y-2">
                  <Label htmlFor="solver-params" className="flex items-center gap-2"><FileJson className="w-4 h-4" />Solver Parameters (JSON)</Label>
                  <Textarea id="solver-params" value={JSON.stringify(localConfig.solver_parameters, null, 2)} onChange={(e) => {
                      try {
                          const parsedJson = JSON.parse(e.target.value);
                          handleFieldChange('solver_parameters', parsedJson);
                      } catch {
                          // Ignore invalid JSON while typing
                      }
                  }} rows={4} className="font-mono text-xs" />
              </div>
          </CardContent>
      </Card>

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2"><TabsTrigger value="general">Constraint Rules</TabsTrigger><TabsTrigger value="weights">Weights & Priorities</TabsTrigger></TabsList>
        <TabsContent value="general" className="space-y-6">
          <Alert><Info className="h-4 w-4" /><AlertDescription>Hard constraints must be satisfied. Soft constraints are preferences that the solver will try to optimize.</AlertDescription></Alert>
          {groupedRules.map(group => (
            <Card key={group.name}>
              <CardHeader><CardTitle className="flex items-center space-x-2"><Settings2 className="h-5 w-5" /><span>{group.name}</span></CardTitle></CardHeader>
              <CardContent className="space-y-4">
                {group.rules.map((rule, index) => (
                  <div key={rule.rule_id}>
                    <div className="flex items-start justify-between py-3">
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center space-x-3">
                          <h4 className="font-medium">{rule.name}</h4>
                          <Badge variant={rule.type === 'hard' ? 'destructive' : 'secondary'}>{rule.type}</Badge>
                          {/* --- START OF FIX: CLARIFICATION --- */}
                          {/* VISUAL FEEDBACK: This badge appears if a constraint is disabled. */}
                          {!rule.is_enabled && <Badge variant="outline">Disabled</Badge>}
                          {/* --- END OF FIX: CLARIFICATION --- */}
                        </div>
                        <p className="text-sm text-muted-foreground">{rule.description}</p>
                        {rule.is_enabled && Object.keys(rule.parameters).length > 0 && (
                          <div className="flex flex-wrap items-center gap-4 mt-2 pt-2">
                            {Object.entries(rule.parameters).map(([key, value]) => (
                              <div key={key} className="flex items-center space-x-2">
                                <Label htmlFor={`param-${rule.rule_id}-${key}`} className="text-sm capitalize">{key.replace(/_/g, ' ')}:</Label>
                                <Input id={`param-${rule.rule_id}-${key}`} type={typeof value === 'number' ? 'number' : 'text'} value={value} onChange={(e) => handleParameterChange(rule.rule_id, key, typeof value === 'number' ? parseInt(e.target.value) || 0 : e.target.value)} className="w-24" />
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      {/* --- START OF FIX: CLARIFICATION --- */}
                      {/*
                        INTERACTIVE TOGGLE: This Switch component allows you to enable or disable any constraint.
                        If a constraint is disabled, the switch will be off. You can click it to turn it on.
                        After making changes, click "Save Changes" to update the configuration.
                      */}
                      <Switch
                        checked={rule.is_enabled}
                        onCheckedChange={(enabled) => handleRuleChange(rule.rule_id, { is_enabled: enabled })}
                        className="data-[state=unchecked]:bg-gray-300 dark:data-[state=unchecked]:bg-input/80"
                      />
                      {/* --- END OF FIX: CLARIFICATION --- */}
                    </div>
                    {index < group.rules.length - 1 && <Separator />}
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </TabsContent>
        {/* ... (rest of the file is unchanged) ... */}
        <TabsContent value="weights" className="space-y-6">
          <Alert><Info className="h-4 w-4" /><AlertDescription>Adjust the relative importance of soft constraints. Higher weights mean higher priority.</AlertDescription></Alert>
          <Card>
            <CardHeader><CardTitle>Soft Constraint Priorities</CardTitle><CardDescription>Adjust weights for enabled soft constraints (e.g., 0-100).</CardDescription></CardHeader>
            <CardContent className="space-y-6 pt-6">
              {localConfig.rules.filter(c => c.type === 'soft' && c.is_enabled).map((rule) => (
                <div key={rule.rule_id} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div><h4 className="font-medium">{rule.name}</h4><p className="text-sm text-muted-foreground">{rule.description}</p></div>
                    <div className="text-right"><div className="text-sm font-medium">Weight: {rule.weight}</div></div>
                  </div>
                  <div className="px-2"><Slider value={[rule.weight]} onValueChange={([value]) => handleRuleChange(rule.rule_id, { weight: value })} max={100} step={5} /></div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <AlertDialog open={showRunJobDialog} onOpenChange={setShowRunJobDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Configuration Saved Successfully!</AlertDialogTitle>
            <AlertDialogDescription>
              Your changes to the '{localConfig.name}' configuration have been saved.
              Would you like to run a new scheduling job with this updated configuration now?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Not Now</AlertDialogCancel>
            <AlertDialogAction onClick={navigateToScheduling}>
              <Zap className="h-4 w-4 mr-2" />
              Go to Scheduling
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create New Constraint Configuration</DialogTitle>
            <DialogDescription>
              Provide a name and select the constraints to include in this new profile.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="new-config-name" className="text-right">Name</Label>
              <Input id="new-config-name" value={newConfigData.name} onChange={e => setNewConfigData({...newConfigData, name: e.target.value})} className="col-span-3" placeholder="e.g., Mid-Semester Exams Profile"/>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="new-config-desc" className="text-right">Description</Label>
              <Input id="new-config-desc" value={newConfigData.description} onChange={e => setNewConfigData({...newConfigData, description: e.target.value})} className="col-span-3" placeholder="A brief description of this profile's purpose"/>
            </div>
          </div>
          <Separator />
          <div className='space-y-2'>
            <Label>Select Constraints to Enable</Label>
            <ScrollArea className="h-72 w-full rounded-md border p-4">
              <div className='space-y-2'>
              {activeConfigurationDetails?.rules.sort((a, b) => a.name.localeCompare(b.name)).map(rule => (
                <div key={rule.rule_id} className="flex items-center space-x-2">
                    <Checkbox 
                      id={`check-${rule.rule_id}`}
                      checked={selectedRuleIds.has(rule.rule_id)}
                      onCheckedChange={(checked) => {
                        setSelectedRuleIds(prev => {
                          const newSet = new Set(prev);
                          if (checked) {
                            newSet.add(rule.rule_id);
                          } else {
                            newSet.delete(rule.rule_id);
                          }
                          return newSet;
                        });
                      }}
                    />
                    <label htmlFor={`check-${rule.rule_id}`} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                      {rule.name}
                      <Badge variant={rule.type === 'hard' ? 'destructive' : 'secondary'} className="ml-2">{rule.type}</Badge>
                    </label>
                </div>
              ))}
              </div>
            </ScrollArea>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateNewConfiguration} disabled={isSaving}>
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2"/> : null}
              Create Configuration
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}