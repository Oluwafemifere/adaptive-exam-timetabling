// src/components/scheduling/ConflictResolutionPanel.tsx

import { 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Zap,
  X
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { ScrollArea } from '../ui/scroll-area'
import { Separator } from '../ui/separator'
import { useResolveConflict } from '../../hooks/useApi'
import type { Conflict } from '../../store/types'
import { cn } from '../ui/utils'

interface ConflictItemProps {
  conflict: Conflict
  onResolve: (conflictId: string, resolution?: Record<string, boolean>) => void
  isResolving: boolean
}

function ConflictItem({ conflict, onResolve, isResolving }: ConflictItemProps) {
  const getSeverityColor = (severity: string, type: string) => {
    if (type === 'hard') {
      return severity === 'high' ? 'text-red-600 bg-red-100' :
             severity === 'medium' ? 'text-red-500 bg-red-50' : 'text-red-400 bg-red-25'
    } else {
      return severity === 'high' ? 'text-amber-600 bg-amber-100' :
             severity === 'medium' ? 'text-amber-500 bg-amber-50' : 'text-amber-400 bg-amber-25'
    }
  }

  const getTypeIcon = (type: string) => {
    return type === 'hard' ? 
      <AlertTriangle className="h-4 w-4" /> : 
      <Clock className="h-4 w-4" />
  }

  return (
    <Card className={cn(
      "mb-3 border-l-4",
      conflict.type === 'hard' ? "border-l-red-500" : "border-l-amber-500"
    )}>
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Conflict Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-2">
              <div className={cn(
                "p-1.5 rounded-full",
                getSeverityColor(conflict.severity, conflict.type)
              )}>
                {getTypeIcon(conflict.type)}
              </div>
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <Badge variant={conflict.type === 'hard' ? "destructive" : "secondary"}>
                    {conflict.type.toUpperCase()}
                  </Badge>
                  <Badge variant="outline" className={cn(getSeverityColor(conflict.severity, conflict.type))}>
                    {conflict.severity}
                  </Badge>
                  {conflict.autoResolvable && (
                    <Badge variant="default" className="bg-green-100 text-green-800">
                      <Zap className="h-3 w-3 mr-1" />
                      Auto-Fix
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-gray-900 font-medium">{conflict.message}</p>
              </div>
            </div>
          </div>

          {/* Affected Exams */}
          <div className="pl-8">
            <p className="text-xs text-gray-600 mb-2">Affected Exams:</p>
            <div className="flex flex-wrap gap-1">
              {conflict.examIds.map((examId) => (
                <Badge key={examId} variant="outline" className="text-xs">
                  {examId.substring(0, 8)}...
                </Badge>
              ))}
            </div>
          </div>

          {/* Resolution Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-gray-100">
            <div className="flex items-center space-x-2">
              {conflict.autoResolvable && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => onResolve(conflict.id, { autoResolve: true })}
                  disabled={isResolving}
                  className="h-7 text-xs"
                >
                  <Zap className="h-3 w-3 mr-1" />
                  Auto-Fix
                </Button>
              )}
              <Button
                size="sm"
                variant="outline"
                // onClick={() => onResolve(conflict.id)} // Manual resolve would open a modal
                disabled={isResolving}
                className="h-7 text-xs"
              >
                Manual Resolve
              </Button>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onResolve(conflict.id, { dismiss: true })}
              disabled={isResolving}
              className="h-7 w-7 p-0"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ... (ConflictStats component remains the same)
interface ConflictStatsProps {
  conflicts: Conflict[]
}

function ConflictStats({ conflicts }: ConflictStatsProps) {
  const hardConflicts = conflicts.filter(c => c.type === 'hard').length
  const softConflicts = conflicts.filter(c => c.type === 'soft').length
  const autoResolvable = conflicts.filter(c => c.autoResolvable).length

  return (
    <div className="grid grid-cols-3 gap-3 mb-4">
      <div className="text-center p-3 bg-red-50 rounded-lg border border-red-200">
        <div className="text-lg font-semibold text-red-600">{hardConflicts}</div>
        <div className="text-xs text-red-600">Hard Conflicts</div>
      </div>
      <div className="text-center p-3 bg-amber-50 rounded-lg border border-amber-200">
        <div className="text-lg font-semibold text-amber-600">{softConflicts}</div>
        <div className="text-xs text-amber-600">Soft Conflicts</div>
      </div>
      <div className="text-center p-3 bg-green-50 rounded-lg border border-green-200">
        <div className="text-lg font-semibold text-green-600">{autoResolvable}</div>
        <div className="text-xs text-green-600">Auto-Fixable</div>
      </div>
    </div>
  )
}

interface ConflictResolutionPanelProps {
  conflicts: Conflict[]
  onAutoResolveAll: () => void
  className?: string
}

export function ConflictResolutionPanel({ 
  conflicts, 
  onAutoResolveAll, 
  className 
}: ConflictResolutionPanelProps) {
  const resolveMutation = useResolveConflict()

  const handleResolveConflict = (conflictId: string, resolution: Record<string, boolean> = {}) => {
    resolveMutation.mutate({ conflictId, resolution })
  }

  const autoResolvableCount = conflicts.filter(c => c.autoResolvable).length
  const sortedConflicts = [...conflicts].sort((a, b) => {
    if (a.type !== b.type) {
      return a.type === 'hard' ? -1 : 1
    }
    const severityOrder = { high: 0, medium: 1, low: 2 }
    return severityOrder[a.severity as keyof typeof severityOrder] - 
           severityOrder[b.severity as keyof typeof severityOrder]
  })

  return (
    <Card className={cn("w-96 h-full", className)}>
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 mr-2" />
            Conflicts
          </div>
          <Badge variant="outline">
            {conflicts.length} Total
          </Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="px-4 pb-4">
        {conflicts.length === 0 ? (
          <div className="text-center py-8">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
            <p className="text-green-600 font-medium">No Conflicts Detected</p>
            <p className="text-sm text-gray-500">Your timetable is conflict-free!</p>
          </div>
        ) : (
          <>
            <ConflictStats conflicts={conflicts} />
            
            {autoResolvableCount > 0 && (
              <>
                <Button
                  onClick={onAutoResolveAll}
                  className="w-full mb-4"
                  disabled={resolveMutation.isPending}
                >
                  <Zap className="h-4 w-4 mr-2" />
                  Auto-Resolve All ({autoResolvableCount})
                </Button>
                <Separator className="mb-4" />
              </>
            )}

            <ScrollArea className="h-[400px] -mx-4 px-4">
              <div className="space-y-3">
                {sortedConflicts.map((conflict) => (
                  <ConflictItem
                    key={conflict.id}
                    conflict={conflict}
                    onResolve={handleResolveConflict}
                    isResolving={resolveMutation.isPending}
                  />
                ))}
              </div>
            </ScrollArea>
          </>
        )}
      </CardContent>
    </Card>
  )
}