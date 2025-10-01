import React, { useState } from 'react';
import { 
  GitCompare, 
  Play, 
  Copy, 
  Trash2, 
  Download,
  Eye,
  Settings,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle,
  Clock
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Progress } from '../components/ui/progress'
import { Separator } from '../components/ui/separator'
import { Alert, AlertDescription } from '../components/ui/alert'
import { useAppStore } from '../store'
import { toast } from 'sonner'
import { cn } from '../components/ui/utils'

interface Scenario {
  id: string;
  name: string;
  description: string;
  status: 'completed' | 'running' | 'failed' | 'queued';
  created: string;
  duration: string;
  metrics: {
    totalExams: number;
    hardConflicts: number;
    softConflicts: number;
    roomUtilization: number;
    studentSatisfaction: number;
    fitnessScore: number;
  };
  constraints: {
    name: string;
    enabled: boolean;
  }[];
}

export function Scenarios() {
  const { setCurrentPage } = useAppStore();
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>(['scenario-1', 'scenario-2']);
  
  const [scenarios] = useState<Scenario[]>([
    {
      id: 'scenario-1',
      name: 'Strict Student Rules',
      description: 'Prioritizes student convenience with minimal conflicts',
      status: 'completed',
      created: '2 hours ago',
      duration: '4m 32s',
      metrics: {
        totalExams: 142,
        hardConflicts: 0,
        softConflicts: 8,
        roomUtilization: 72.5,
        studentSatisfaction: 94,
        fitnessScore: 8.7
      },
      constraints: [
        { name: 'Student Conflicts', enabled: true },
        { name: 'Back-to-Back Prevention', enabled: true },
        { name: 'Room Capacity', enabled: true },
        { name: 'Spreading Exams', enabled: false }
      ]
    },
    {
      id: 'scenario-2',
      name: 'Balanced Load',
      description: 'Balances student needs with resource utilization',
      status: 'completed',
      created: '1 hour ago',
      duration: '6m 18s',
      metrics: {
        totalExams: 142,
        hardConflicts: 0,
        softConflicts: 15,
        roomUtilization: 87.2,
        studentSatisfaction: 89,
        fitnessScore: 7.9
      },
      constraints: [
        { name: 'Student Conflicts', enabled: true },
        { name: 'Back-to-Back Prevention', enabled: true },
        { name: 'Room Capacity', enabled: true },
        { name: 'Spreading Exams', enabled: true }
      ]
    },
    {
      id: 'scenario-3',
      name: 'Maximum Utilization',
      description: 'Optimizes for highest room and time slot usage',
      status: 'completed',
      created: '30 minutes ago',
      duration: '3m 45s',
      metrics: {
        totalExams: 142,
        hardConflicts: 0,
        softConflicts: 23,
        roomUtilization: 95.8,
        studentSatisfaction: 78,
        fitnessScore: 7.2
      },
      constraints: [
        { name: 'Student Conflicts', enabled: true },
        { name: 'Back-to-Back Prevention', enabled: false },
        { name: 'Room Capacity', enabled: true },
        { name: 'Spreading Exams', enabled: true }
      ]
    },
    {
      id: 'scenario-4',
      name: 'Custom Optimization',
      description: 'Currently running with custom constraint weights',
      status: 'running',
      created: '15 minutes ago',
      duration: '-',
      metrics: {
        totalExams: 0,
        hardConflicts: 0,
        softConflicts: 0,
        roomUtilization: 0,
        studentSatisfaction: 0,
        fitnessScore: 0
      },
      constraints: [
        { name: 'Student Conflicts', enabled: true },
        { name: 'Back-to-Back Prevention', enabled: true },
        { name: 'Room Capacity', enabled: true },
        { name: 'Spreading Exams', enabled: true }
      ]
    }
  ]);

  const completedScenarios = scenarios.filter(s => s.status === 'completed');
  const selectedScenarioData = completedScenarios.filter(s => selectedScenarios.includes(s.id));

  const toggleScenarioSelection = (scenarioId: string) => {
    if (selectedScenarios.includes(scenarioId)) {
      if (selectedScenarios.length > 1) {
        setSelectedScenarios(selectedScenarios.filter(id => id !== scenarioId));
      }
    } else {
      if (selectedScenarios.length < 3) {
        setSelectedScenarios([...selectedScenarios, scenarioId]);
      } else {
        toast.error('Maximum 3 scenarios can be compared at once');
      }
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300';
      case 'running': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300';
      case 'failed': return 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300';
      case 'queued': return 'bg-gray-100 text-gray-700 dark:bg-gray-900/50 dark:text-gray-300';
      default: return '';
    }
  };

  const getMetricComparison = (metric: keyof Scenario['metrics'], scenarios: Scenario[]) => {
    if (scenarios.length < 2) return {};
    
    const values = scenarios.map(s => s.metrics[metric]);
    const best = Math.max(...values);
    const worst = Math.min(...values);
    
    return scenarios.reduce((acc, scenario, index) => {
      const value = scenario.metrics[metric];
      let trend: 'up' | 'down' | 'neutral' = 'neutral';
      
      if (value === best && best !== worst) trend = 'up';
      else if (value === worst && best !== worst) trend = 'down';
      
      acc[scenario.id] = trend;
      return acc;
    }, {} as Record<string, 'up' | 'down' | 'neutral'>);
  };

  const hardConflictsComparison = getMetricComparison('hardConflicts', selectedScenarioData);
  const softConflictsComparison = getMetricComparison('softConflicts', selectedScenarioData);
  const roomUtilizationComparison = getMetricComparison('roomUtilization', selectedScenarioData);
  const studentSatisfactionComparison = getMetricComparison('studentSatisfaction', selectedScenarioData);
  const fitnessScoreComparison = getMetricComparison('fitnessScore', selectedScenarioData);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Scenario Comparison</h1>
          <p className="text-muted-foreground">Compare different timetable solutions side-by-side</p>
        </div>
        <div className="flex items-center space-x-3">
          <Button variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            Generate New Scenario
          </Button>
          <Button>
            <Play className="h-4 w-4 mr-2" />
            Run Optimization
          </Button>
        </div>
      </div>

      {/* Scenario List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <GitCompare className="h-5 w-5 mr-2" />
            Available Scenarios
          </CardTitle>
          <CardDescription>
            Select up to 3 scenarios to compare. Click on a scenario to toggle selection.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {scenarios.map((scenario) => (
              <Card 
                key={scenario.id} 
                className={cn(
                  "cursor-pointer transition-all hover:shadow-md",
                  selectedScenarios.includes(scenario.id) && scenario.status === 'completed' 
                    ? "ring-2 ring-primary" 
                    : "",
                  scenario.status !== 'completed' ? "opacity-60" : ""
                )}
                onClick={() => scenario.status === 'completed' && toggleScenarioSelection(scenario.id)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h4 className="font-medium">{scenario.name}</h4>
                      <p className="text-sm text-muted-foreground mt-1">
                        {scenario.description}
                      </p>
                    </div>
                    <Badge className={getStatusColor(scenario.status)}>
                      {scenario.status}
                    </Badge>
                  </div>
                  
                  <div className="flex items-center justify-between text-sm text-muted-foreground mb-3">
                    <span>Created {scenario.created}</span>
                    <span>Duration: {scenario.duration}</span>
                  </div>

                  {scenario.status === 'running' && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span>Progress</span>
                        <span>67%</span>
                      </div>
                      <Progress value={67} className="h-2" />
                    </div>
                  )}

                  {scenario.status === 'completed' && (
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-muted-foreground">Hard Conflicts:</span>
                        <span className="ml-2 font-medium">{scenario.metrics.hardConflicts}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Soft Conflicts:</span>
                        <span className="ml-2 font-medium">{scenario.metrics.softConflicts}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Room Util:</span>
                        <span className="ml-2 font-medium">{scenario.metrics.roomUtilization}%</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Fitness:</span>
                        <span className="ml-2 font-medium">{scenario.metrics.fitnessScore}/10</span>
                      </div>
                    </div>
                  )}

                  {scenario.status === 'completed' && (
                    <div className="flex items-center justify-end space-x-2 mt-3 pt-3 border-t">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setCurrentPage('timetable');
                        }}
                      >
                        <Eye className="h-3 w-3 mr-1" />
                        View
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          toast.success('Scenario duplicated');
                        }}
                      >
                        <Copy className="h-3 w-3 mr-1" />
                        Copy
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          toast.success('Scenario exported');
                        }}
                      >
                        <Download className="h-3 w-3 mr-1" />
                        Export
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Comparison View */}
      {selectedScenarioData.length >= 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Scenario Comparison</CardTitle>
            <CardDescription>
              Key performance indicators comparison for selected scenarios
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">Metric</th>
                    {selectedScenarioData.map(scenario => (
                      <th key={scenario.id} className="text-center py-3 px-4 min-w-[140px]">
                        <div>
                          <div className="font-medium">{scenario.name}</div>
                          <div className="text-xs text-muted-foreground font-normal">
                            {scenario.created}
                          </div>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">Total Exams</td>
                    {selectedScenarioData.map(scenario => (
                      <td key={scenario.id} className="text-center py-3 px-4">
                        {scenario.metrics.totalExams}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">Hard Conflicts</td>
                    {selectedScenarioData.map(scenario => (
                      <td key={scenario.id} className="text-center py-3 px-4">
                        <div className="flex items-center justify-center space-x-1">
                          <span className={cn(
                            scenario.metrics.hardConflicts === 0 ? "text-green-600" : "text-red-600"
                          )}>
                            {scenario.metrics.hardConflicts}
                          </span>
                          {hardConflictsComparison[scenario.id] === 'up' && <TrendingUp className="h-3 w-3 text-green-500" />}
                          {hardConflictsComparison[scenario.id] === 'down' && <TrendingDown className="h-3 w-3 text-red-500" />}
                          {hardConflictsComparison[scenario.id] === 'neutral' && <Minus className="h-3 w-3 text-gray-400" />}
                        </div>
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">Soft Conflicts</td>
                    {selectedScenarioData.map(scenario => (
                      <td key={scenario.id} className="text-center py-3 px-4">
                        <div className="flex items-center justify-center space-x-1">
                          <span>{scenario.metrics.softConflicts}</span>
                          {softConflictsComparison[scenario.id] === 'up' && <TrendingDown className="h-3 w-3 text-red-500" />}
                          {softConflictsComparison[scenario.id] === 'down' && <TrendingUp className="h-3 w-3 text-green-500" />}
                          {softConflictsComparison[scenario.id] === 'neutral' && <Minus className="h-3 w-3 text-gray-400" />}
                        </div>
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">Room Utilization</td>
                    {selectedScenarioData.map(scenario => (
                      <td key={scenario.id} className="text-center py-3 px-4">
                        <div className="flex items-center justify-center space-x-1">
                          <span>{scenario.metrics.roomUtilization}%</span>
                          {roomUtilizationComparison[scenario.id] === 'up' && <TrendingUp className="h-3 w-3 text-green-500" />}
                          {roomUtilizationComparison[scenario.id] === 'down' && <TrendingDown className="h-3 w-3 text-red-500" />}
                          {roomUtilizationComparison[scenario.id] === 'neutral' && <Minus className="h-3 w-3 text-gray-400" />}
                        </div>
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">Student Satisfaction</td>
                    {selectedScenarioData.map(scenario => (
                      <td key={scenario.id} className="text-center py-3 px-4">
                        <div className="flex items-center justify-center space-x-1">
                          <span>{scenario.metrics.studentSatisfaction}%</span>
                          {studentSatisfactionComparison[scenario.id] === 'up' && <TrendingUp className="h-3 w-3 text-green-500" />}
                          {studentSatisfactionComparison[scenario.id] === 'down' && <TrendingDown className="h-3 w-3 text-red-500" />}
                          {studentSatisfactionComparison[scenario.id] === 'neutral' && <Minus className="h-3 w-3 text-gray-400" />}
                        </div>
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-3 px-4 font-medium">Overall Fitness Score</td>
                    {selectedScenarioData.map(scenario => (
                      <td key={scenario.id} className="text-center py-3 px-4">
                        <div className="flex items-center justify-center space-x-1">
                          <span className="font-medium">{scenario.metrics.fitnessScore}/10</span>
                          {fitnessScoreComparison[scenario.id] === 'up' && <TrendingUp className="h-3 w-3 text-green-500" />}
                          {fitnessScoreComparison[scenario.id] === 'down' && <TrendingDown className="h-3 w-3 text-red-500" />}
                          {fitnessScoreComparison[scenario.id] === 'neutral' && <Minus className="h-3 w-3 text-gray-400" />}
                        </div>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="mt-6 pt-6 border-t">
              <h4 className="font-medium mb-3">Best Performing Scenario</h4>
              <div className="flex items-center space-x-3">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <div>
                  <p className="font-medium">
                    {selectedScenarioData.reduce((best, current) => 
                      current.metrics.fitnessScore > best.metrics.fitnessScore ? current : best
                    ).name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Highest overall fitness score with minimal conflicts
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {selectedScenarioData.length < 2 && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Select at least 2 completed scenarios to view comparison metrics.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}