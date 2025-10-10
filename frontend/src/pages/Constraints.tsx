// frontend/src/pages/Constraints.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { Sliders, Save, RotateCcw, Info, AlertTriangle, Settings2, Loader2, FileJson } from 'lucide-react';
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
import { RuleSettingRead, SystemConfigurationDetails } from '../store/types';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea'; // Import Textarea

// Helper to group rules by category
const groupRulesByCategory = (rules: RuleSettingRead[]) => {
  const categoriesMap: { [key: string]: { name: string, rules: RuleSettingRead[] } } = {};
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
  } = useAppStore();

  const [localConfig, setLocalConfig] = useState<SystemConfigurationDetails | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    // Sync local state when the global store's active configuration changes
    if (activeConfigurationDetails) {
      setLocalConfig(JSON.parse(JSON.stringify(activeConfigurationDetails)));
    }
  }, [activeConfigurationDetails]);

  const groupedRules = useMemo(() => {
    if (!localConfig?.rules) return [];
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
    await saveActiveConfiguration(localConfig);
    setIsSaving(false);
  };

  const handleReset = () => {
    if (activeConfigurationDetails) {
      setLocalConfig(JSON.parse(JSON.stringify(activeConfigurationDetails)));
      toast.info('Changes have been discarded.');
    }
  };

  if (!localConfig) {
    return (
      <div className="flex justify-center items-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="ml-4 text-muted-foreground">Loading configuration...</p>
      </div>
    );
  }

  const { rules } = localConfig;
  const hardConstraints = rules.filter(c => c.type === 'hard');
  const softConstraints = rules.filter(c => c.type === 'soft');
  const enabledHard = hardConstraints.filter(c => c.is_enabled).length;
  const enabledSoft = softConstraints.filter(c => c.is_enabled).length;

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
                <SelectItem key={config.id} value={config.id}>{config.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleReset} disabled={isSaving}><RotateCcw className="h-4 w-4 mr-2" />Discard</Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
            Save Changes
          </Button>
        </div>
      </div>
      
      {/* Configuration Details Card */}
      <Card>
          <CardHeader>
              <CardTitle>Configuration Profile</CardTitle>
              <CardDescription>Edit the name, description, and solver settings for this profile.</CardDescription>
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
                          handleFieldChange('solver_parameters', JSON.parse(e.target.value));
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
                        <div className="flex items-center space-x-3"><h4 className="font-medium">{rule.name}</h4><Badge variant={rule.type === 'hard' ? 'destructive' : 'secondary'}>{rule.type}</Badge>{!rule.is_enabled && <Badge variant="outline">Disabled</Badge>}</div>
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
                      <Switch checked={rule.is_enabled} onCheckedChange={(enabled) => handleRuleChange(rule.rule_id, { is_enabled: enabled })} />
                    </div>
                    {index < group.rules.length - 1 && <Separator />}
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </TabsContent>
        <TabsContent value="weights" className="space-y-6">
          <Alert><Info className="h-4 w-4" /><AlertDescription>Adjust the relative importance of soft constraints. Higher weights mean higher priority.</AlertDescription></Alert>
          <Card>
            <CardHeader><CardTitle>Soft Constraint Priorities</CardTitle><CardDescription>Adjust weights for enabled soft constraints (e.g., 0-1000).</CardDescription></CardHeader>
            <CardContent className="space-y-6 pt-6">
              {softConstraints.filter(c => c.is_enabled).map((rule) => (
                <div key={rule.rule_id} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div><h4 className="font-medium">{rule.name}</h4><p className="text-sm text-muted-foreground">{rule.description}</p></div>
                    <div className="text-right"><div className="text-sm font-medium">Weight: {rule.weight}</div></div>
                  </div>
                  <div className="px-2"><Slider value={[rule.weight]} onValueChange={([value]) => handleRuleChange(rule.rule_id, { weight: value })} max={1000} step={10} /></div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}