import React from 'react'
import { 
  Play, 
  Pause, 
  Square, 
  Settings, 
  Activity, 
  Clock,
  CheckCircle,
  AlertTriangle,
  BarChart3
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Progress } from '../components/ui/progress'
import { Slider } from '../components/ui/slider'
import { Badge } from '../components/ui/badge'
import { Label } from '../components/ui/label'
import { Separator } from '../components/ui/separator'
import { useAppStore } from '../store'
import { useScheduling } from '../hooks/useApi'
import { cn } from '../components/ui/utils'

interface ConstraintSliderProps {
  label: string
  description: string
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
  step?: number
}

function ConstraintSlider({ label, description, value, onChange, min = 0, max = 1, step = 0.1 }: ConstraintSliderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <Label className="font-medium">{label}</Label>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
        <Badge variant="outline" className="min-w-16 justify-center">
          {value.toFixed(1)}
        </Badge>
      </div>
      <Slider
        value={[value]}
        onValueChange={([newValue]) => onChange(newValue)}
        min={min}
        max={max}
        step={step}
        className="w-full"
      />
    </div>
  )
}

interface PhaseIndicatorProps {
  phase: string
  isActive: boolean
  isCompleted: boolean
  duration?: string
}

function PhaseIndicator({ phase, isActive, isCompleted, duration }: PhaseIndicatorProps) {
  return (
    <div className={cn(
      "flex items-center space-x-3 p-4 rounded-lg border",
      isActive && "bg-blue-50 border-blue-200",
      isCompleted && "bg-green-50 border-green-200",
      !isActive && !isCompleted && "bg-gray-50 border-gray-200"
    )}>
      <div className={cn(
        "w-3 h-3 rounded-full",
        isActive && "bg-blue-500 animate-pulse",
        isCompleted && "bg-green-500",
        !isActive && !isCompleted && "bg-gray-300"
      )} />
      <div className="flex-1">
        <p className={cn(
          "font-medium",
          isActive && "text-blue-900",
          isCompleted && "text-green-900",
          !isActive && !isCompleted && "text-gray-600"
        )}>
          {phase}
        </p>
        {duration && (
          <p className="text-sm text-gray-500">{duration}</p>
        )}
      </div>
      {isActive && <Activity className="h-4 w-4 text-blue-500 animate-pulse" />}
      {isCompleted && <CheckCircle className="h-4 w-4 text-green-500" />}
    </div>
  )
}

export function Scheduling() {
  const { schedulingStatus, settings, updateSettings } = useAppStore()
  const { startScheduling, pauseScheduling, cancelScheduling } = useScheduling()

  const handleConstraintWeightChange = (constraint: string, value: number) => {
    updateSettings({
      constraintWeights: {
        ...settings.constraintWeights,
        [constraint]: value
      }
    })
  }

  const handleStartScheduling = () => {
    startScheduling.mutate({
      constraints: settings.constraintWeights,
      options: {
        maxIterations: 10000,
        timeLimit: 300, // 5 minutes
        populationSize: 50
      }
    })
  }

  const phases = [
    {
      name: 'Constraint Propagation (CP-SAT)',
      description: 'Initial constraint satisfaction',
      active: schedulingStatus.phase === 'cp-sat',
      completed: ['genetic-algorithm', 'completed'].includes(schedulingStatus.phase),
      estimatedDuration: '30-60 seconds'
    },
    {
      name: 'Genetic Algorithm Optimization',
      description: 'Evolutionary optimization',
      active: schedulingStatus.phase === 'genetic-algorithm',
      completed: schedulingStatus.phase === 'completed',
      estimatedDuration: '60-120 seconds'
    }
  ]

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Panel - Constraint Configuration */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Settings className="h-5 w-5 mr-2" />
                Constraint Weights
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <ConstraintSlider
                label="No Overlap"
                description="Prevent student exam conflicts"
                value={settings.constraintWeights.noOverlap}
                onChange={(value) => handleConstraintWeightChange('noOverlap', value)}
              />
              
              <ConstraintSlider
                label="Room Capacity"
                description="Ensure adequate room size"
                value={settings.constraintWeights.roomCapacity}
                onChange={(value) => handleConstraintWeightChange('roomCapacity', value)}
              />
              
              <ConstraintSlider
                label="Instructor Availability"
                description="Respect instructor schedules"
                value={settings.constraintWeights.instructorAvailability}
                onChange={(value) => handleConstraintWeightChange('instructorAvailability', value)}
              />
              
              <ConstraintSlider
                label="Student Conflicts"
                description="Minimize back-to-back exams"
                value={settings.constraintWeights.studentConflicts}
                onChange={(value) => handleConstraintWeightChange('studentConflicts', value)}
              />
            </CardContent>
          </Card>

          {/* Algorithm Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Algorithm Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Time Limit</Label>
                <div className="flex items-center space-x-2">
                  <Slider value={[5]} min={1} max={30} step={1} className="flex-1" />
                  <span className="text-sm text-gray-500 min-w-12">5 min</span>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Population Size</Label>
                <div className="flex items-center space-x-2">
                  <Slider value={[50]} min={10} max={200} step={10} className="flex-1" />
                  <span className="text-sm text-gray-500 min-w-12">50</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Progress Tracking */}
        <div className="lg:col-span-2 space-y-6">
          {/* Phase Progress */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center">
                  <Clock className="h-5 w-5 mr-2" />
                  Scheduling Progress
                </div>
                {schedulingStatus.isRunning && (
                  <Badge variant="default" className="animate-pulse">
                    Running
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Overall Progress */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Overall Progress</span>
                    <span className="text-sm text-gray-500">{schedulingStatus.progress}%</span>
                  </div>
                  <Progress value={schedulingStatus.progress} className="h-2" />
                </div>

                <Separator />

                {/* Phase Indicators */}
                <div className="space-y-3">
                  {phases.map((phase, index) => (
                    <PhaseIndicator
                      key={index}
                      phase={phase.name}
                      isActive={phase.active}
                      isCompleted={phase.completed}
                      duration={phase.estimatedDuration}
                    />
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Live Solver Metrics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <BarChart3 className="h-5 w-5 mr-2" />
                Live Solver Metrics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Constraints Satisfied</span>
                      <span className="text-sm text-gray-500">
                        {schedulingStatus.metrics.constraintsSatisfied}/{schedulingStatus.metrics.totalConstraints}
                      </span>
                    </div>
                    <Progress 
                      value={schedulingStatus.metrics.totalConstraints > 0 
                        ? (schedulingStatus.metrics.constraintsSatisfied / schedulingStatus.metrics.totalConstraints) * 100 
                        : 0
                      } 
                      className="h-2" 
                    />
                  </div>
                  
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Iterations Completed</span>
                      <span className="text-sm text-gray-500">
                        {schedulingStatus.metrics.iterationsCompleted.toLocaleString()}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400">
                      Average: {schedulingStatus.metrics.iterationsCompleted > 0 
                        ? Math.round(schedulingStatus.metrics.iterationsCompleted / Math.max(1, schedulingStatus.progress / 10)) 
                        : 0}/sec
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Best Solution Score</span>
                      <span className={cn(
                        "text-sm font-medium",
                        schedulingStatus.metrics.bestSolution > 80 ? "text-green-600" :
                        schedulingStatus.metrics.bestSolution > 60 ? "text-amber-600" : "text-red-600"
                      )}>
                        {schedulingStatus.metrics.bestSolution.toFixed(1)}%
                      </span>
                    </div>
                    <Progress 
                      value={schedulingStatus.metrics.bestSolution} 
                      className="h-2" 
                    />
                  </div>
                  
                  <div>
                    <div className="text-sm font-medium mb-2">Status</div>
                    <div className="flex items-center space-x-2">
                      {schedulingStatus.phase === 'completed' ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : schedulingStatus.phase === 'error' ? (
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                      ) : (
                        <Activity className="h-4 w-4 text-blue-500 animate-pulse" />
                      )}
                      <span className="text-sm capitalize">
                        {schedulingStatus.phase === 'cp-sat' ? 'Constraint Solving' :
                         schedulingStatus.phase === 'genetic-algorithm' ? 'Optimizing' :
                         schedulingStatus.phase}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Control Panel */}
          <Card>
            <CardHeader>
              <CardTitle>Controls</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-4">
                {!schedulingStatus.isRunning ? (
                  <Button 
                    onClick={handleStartScheduling}
                    disabled={startScheduling.isPending}
                    className="min-w-32"
                  >
                    <Play className="h-4 w-4 mr-2" />
                    Start Scheduling
                  </Button>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      onClick={pauseScheduling}
                      disabled={!schedulingStatus.canPause}
                    >
                      <Pause className="h-4 w-4 mr-2" />
                      Pause
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={cancelScheduling}
                      disabled={!schedulingStatus.canCancel}
                    >
                      <Square className="h-4 w-4 mr-2" />
                      Cancel
                    </Button>
                  </>
                )}
              </div>
              
              {schedulingStatus.phase === 'completed' && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center">
                    <CheckCircle className="h-5 w-5 text-green-500 mr-3" />
                    <div>
                      <p className="font-medium text-green-800">Scheduling Completed Successfully!</p>
                      <p className="text-sm text-green-600">
                        Generated timetable with {schedulingStatus.metrics.bestSolution.toFixed(1)}% optimization score.
                        You can now view the results in the Timetable page.
                      </p>
                    </div>
                  </div>
                </div>
              )}
              
              {schedulingStatus.phase === 'error' && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-center">
                    <AlertTriangle className="h-5 w-5 text-red-500 mr-3" />
                    <div>
                      <p className="font-medium text-red-800">Scheduling Failed</p>
                      <p className="text-sm text-red-600">
                        An error occurred during the scheduling process. Please check your constraints and try again.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}