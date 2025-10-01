// frontend/src/pages/Reports.tsx

import React, { useState } from 'react'
import { 
  FileText, 
  Download, 
  Calendar, 
  Users, 
  Building2, 
  AlertTriangle,
  Trash2
  // REMOVED: Eye, Filter, RefreshCw
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { Label } from '../components/ui/label'
import { Input } from '../components/ui/input'
import { Checkbox } from '../components/ui/checkbox'
import { Progress } from '../components/ui/progress'
import { useGenerateReport } from '../hooks/useApi'
// REMOVED: Unused 'cn' import

// Define a more specific type for report options
type ReportOptions = Record<string, string | boolean | number | undefined>;

interface ReportTemplate {
  id: string
  name: string
  description: string
  icon: React.ElementType
  type: 'student' | 'room' | 'conflicts' | 'instructor'
  options: Array<{
    name: string
    label: string
    type: 'text' | 'select' | 'checkbox' | 'date'
    required?: boolean
    options?: string[]
  }>
}

const reportTemplates: ReportTemplate[] = [
  {
    id: 'student-schedules',
    name: 'Student Schedules',
    description: 'Individual exam schedules for students',
    icon: Users,
    type: 'student',
    options: [
      { name: 'program', label: 'Program', type: 'select', options: ['All Programs', 'Computer Science', 'Mathematics', 'Physics'] },
      { name: 'year', label: 'Academic Year', type: 'select', options: ['All Years', 'Year 1', 'Year 2', 'Year 3', 'Year 4'] },
      { name: 'format', label: 'Include Format', type: 'checkbox' },
      { name: 'conflicts', label: 'Highlight Conflicts', type: 'checkbox' }
    ]
  },
  {
    id: 'room-utilization',
    name: 'Room Utilization',
    description: 'Room usage statistics and availability',
    icon: Building2,
    type: 'room',
    options: [
      { name: 'building', label: 'Building', type: 'select', options: ['All Buildings', 'Building A', 'Building B', 'Building C'] },
      { name: 'capacity', label: 'Min Capacity', type: 'text' },
      { name: 'utilization', label: 'Show Utilization %', type: 'checkbox' },
      { name: 'availability', label: 'Show Available Slots', type: 'checkbox' }
    ]
  },
  {
    id: 'conflicts-report',
    name: 'Conflicts Analysis',
    description: 'Detailed conflict analysis and resolution suggestions',
    icon: AlertTriangle,
    type: 'conflicts',
    options: [
      { name: 'type', label: 'Conflict Type', type: 'select', options: ['All Conflicts', 'Hard Conflicts', 'Soft Conflicts'] },
      { name: 'severity', label: 'Severity', type: 'select', options: ['All Severity', 'High', 'Medium', 'Low'] },
      { name: 'resolvable', label: 'Auto-resolvable Only', type: 'checkbox' },
      { name: 'suggestions', label: 'Include Suggestions', type: 'checkbox' }
    ]
  },
  {
    id: 'instructor-assignments',
    name: 'Instructor Assignments',
    description: 'Invigilation assignments and workload',
    icon: Calendar,
    type: 'instructor',
    options: [
      { name: 'department', label: 'Department', type: 'select', options: ['All Departments', 'Computer Science', 'Mathematics', 'Physics'] },
      { name: 'workload', label: 'Include Workload Stats', type: 'checkbox' },
      { name: 'availability', label: 'Show Availability', type: 'checkbox' },
      { name: 'conflicts', label: 'Flag Conflicts', type: 'checkbox' }
    ]
  }
]

interface ReportTemplate {
  id: string
  name: string
  description: string
  icon: React.ElementType
  type: 'student' | 'room' | 'conflicts' | 'instructor'
  options: Array<{
    name: string
    label: string
    type: 'text' | 'select' | 'checkbox' | 'date'
    required?: boolean
    options?: string[]
  }>
}
interface GeneratedReport {
  id: string
  name: string
  type: string
  generatedAt: string
  status: 'generating' | 'completed' | 'failed'
  progress: number
  downloadUrl?: string
  size?: string
}

function ReportTemplateCard({ 
  template, 
  onGenerate, 
  isGenerating 
}: { 
  template: ReportTemplate
  // FIXED: Replaced 'any' with the specific 'ReportOptions' type
  onGenerate: (template: ReportTemplate, options: ReportOptions) => void
  isGenerating: boolean 
}) {
  const [options, setOptions] = useState<ReportOptions>({})
  const Icon = template.icon

  // FIXED: Replaced 'any' with a more specific type for the value
  const handleOptionChange = (optionName: string, value: string | boolean | number) => {
    setOptions(prev => ({ ...prev, [optionName]: value }))
  }

  const handleGenerate = () => {
    onGenerate(template, options)
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center space-x-2">
          <Icon className="h-5 w-5" />
          <span>{template.name}</span>
        </CardTitle>
        <p className="text-sm text-gray-600">{template.description}</p>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Options */}
        <div className="space-y-3">
          {template.options.map((option) => (
            <div key={option.name} className="space-y-1">
              <Label className="text-sm font-medium">{option.label}</Label>
              
              {option.type === 'select' && (
                <Select
                  value={String(options[option.name] || option.options?.[0])}
                  onValueChange={(value) => handleOptionChange(option.name, value)}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {option.options?.map((opt) => (
                      <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              
              {option.type === 'text' && (
                <Input
                  placeholder={`Enter ${option.label.toLowerCase()}`}
                  value={String(options[option.name] || '')}
                  onChange={(e) => handleOptionChange(option.name, e.target.value)}
                />
              )}
              
              {option.type === 'checkbox' && (
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id={`${template.id}-${option.name}`}
                    checked={Boolean(options[option.name] || false)}
                    onCheckedChange={(checked) => handleOptionChange(option.name, checked)}
                  />
                  <Label 
                    htmlFor={`${template.id}-${option.name}`}
                    className="text-sm text-gray-600"
                  >
                    {option.label}
                  </Label>
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Generate Button */}
        <Button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="w-full"
        >
          <FileText className="h-4 w-4 mr-2" />
          {isGenerating ? 'Generating...' : 'Generate Report'}
        </Button>
      </CardContent>
    </Card>
  )
}

function GeneratedReportsSection({ reports }: { reports: GeneratedReport[] }) {
  const handleDownload = (report: GeneratedReport, format: string) => {
    // Mock download
    const blob = new Blob([`Mock ${format.toUpperCase()} report content for ${report.name}`], {
      type: format === 'pdf' ? 'application/pdf' : 'text/csv'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${report.name.toLowerCase().replace(/\s+/g, '-')}.${format}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDelete = (reportId: string) => {
    // Mock delete
    console.log('Deleting report:', reportId)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center">
            <Download className="h-5 w-5 mr-2" />
            Generated Reports
          </div>
          <Badge variant="outline">{reports.length} Reports</Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent>
        {reports.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FileText className="h-12 w-12 mx-auto mb-3 text-gray-400" />
            <p>No reports generated yet</p>
            <p className="text-sm">Generate your first report using the templates above</p>
          </div>
        ) : (
          <div className="space-y-3">
            {reports.map((report) => (
              <div key={report.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <h4 className="font-medium">{report.name}</h4>
                    <Badge variant={
                      report.status === 'completed' ? 'default' :
                      report.status === 'failed' ? 'destructive' : 'secondary'
                    }>
                      {report.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-500">
                    Generated on {new Date(report.generatedAt).toLocaleString()}
                    {report.size && ` • ${report.size}`}
                  </p>
                  
                  {report.status === 'generating' && (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span>Generating...</span>
                        <span>{report.progress}%</span>
                      </div>
                      <Progress value={report.progress} className="h-1" />
                    </div>
                  )}
                </div>
                
                <div className="flex items-center space-x-2">
                  {report.status === 'completed' && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownload(report, 'pdf')}
                      >
                        <Download className="h-3 w-3 mr-1" />
                        PDF
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownload(report, 'csv')}
                      >
                        <Download className="h-3 w-3 mr-1" />
                        CSV
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownload(report, 'xlsx')}
                      >
                        <Download className="h-3 w-3 mr-1" />
                        Excel
                      </Button>
                    </>
                  )}
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(report.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function Reports() {
  const generateReportMutation = useGenerateReport()
  const [generatedReports, setGeneratedReports] = useState<GeneratedReport[]>([
    {
      id: '1',
      name: 'Student Schedules - Computer Science',
      type: 'student',
      generatedAt: '2024-01-15T10:30:00Z',
      status: 'completed',
      progress: 100,
      size: '2.3 MB'
    },
    {
      id: '2',
      name: 'Room Utilization Report',
      type: 'room',
      generatedAt: '2024-01-15T09:15:00Z',
      status: 'completed',
      progress: 100,
      size: '1.1 MB'
    },
    {
      id: '3',
      name: 'Conflicts Analysis',
      type: 'conflicts',
      generatedAt: '2024-01-15T11:45:00Z',
      status: 'generating',
      progress: 67
    }
  ])

  // FIXED: Replaced 'any' with specific 'ReportOptions' type
  const handleGenerateReport = async (template: ReportTemplate, options: ReportOptions) => {
    const reportId = Math.random().toString(36).substr(2, 9)
    
    // Add to generated reports with generating status
    const newReport: GeneratedReport = {
      id: reportId,
      name: `${template.name} - ${new Date().toLocaleDateString()}`,
      type: template.type,
      generatedAt: new Date().toISOString(),
      status: 'generating',
      progress: 0
    }
    
    setGeneratedReports(prev => [newReport, ...prev])
    
    try {
      // FIXED: Changed 'type' to 'report_type'
      await generateReportMutation.mutateAsync({ report_type: template.type, options })
      
      // Update to completed status
      setGeneratedReports(prev => 
        prev.map(report => 
          report.id === reportId 
            ? { ...report, status: 'completed', progress: 100, size: '1.5 MB' }
            : report
        )
      )
    } catch (error) {
      // FIXED: Use the error variable, e.g., for logging
      console.error("Failed to generate report:", error);
      // Update to failed status
      setGeneratedReports(prev => 
        prev.map(report => 
          report.id === reportId 
            ? { ...report, status: 'failed', progress: 0 }
            : report
        )
      )
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Report Templates */}
      <div>
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-2">Report Templates</h2>
          <p className="text-gray-600">
            Generate comprehensive reports for different aspects of your exam timetabling system.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
          {reportTemplates.map((template) => (
            <ReportTemplateCard
              key={template.id}
              template={template}
              onGenerate={handleGenerateReport}
              isGenerating={generateReportMutation.isPending}
            />
          ))}
        </div>
      </div>

      {/* Generated Reports */}
      <GeneratedReportsSection reports={generatedReports} />

      {/* Export Options */}
      <Card>
        <CardHeader>
          <CardTitle>Export Options</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <h4 className="font-medium">PDF Reports</h4>
              <p className="text-sm text-gray-600">
                Professional formatted reports suitable for printing and official documentation.
              </p>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-medium">CSV Data</h4>
              <p className="text-sm text-gray-600">
                Raw data exports for further analysis in spreadsheet applications or databases.
              </p>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-medium">Excel Workbooks</h4>
              <p className="text-sm text-gray-600">
                Interactive spreadsheets with multiple sheets and formatted data tables.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}