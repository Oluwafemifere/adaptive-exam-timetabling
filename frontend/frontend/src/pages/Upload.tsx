import React, { useState, useCallback } from 'react'
import { 
  Upload as UploadIcon, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  X,
  Download
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Progress } from '../components/ui/progress'
import { Badge } from '../components/ui/badge'
import { Alert, AlertDescription } from '../components/ui/alert'
import { useAppStore } from '../store'
import { useFileUpload } from '../hooks/useApi'
import { cn } from '../components/ui/utils'

interface FileRequirement {
  name: string
  required: boolean
  description: string
  format: string
  example: string
}

const fileRequirements: FileRequirement[] = [
  {
    name: 'Students',
    required: true,
    description: 'Student enrollment data with IDs and programs',
    format: 'students.csv',
    example: 'student_id,name,program,year,email'
  },
  {
    name: 'Courses',
    required: true,
    description: 'Course information and requirements',
    format: 'courses.csv',
    example: 'course_code,name,credits,department,instructor_id'
  },
  {
    name: 'Registrations',
    required: true,
    description: 'Student course registrations',
    format: 'registrations.csv',
    example: 'student_id,course_code,semester,year'
  },
  {
    name: 'Rooms',
    required: true,
    description: 'Available rooms and capacities',
    format: 'rooms.csv',
    example: 'room_id,name,capacity,type,facilities'
  },
  {
    name: 'Invigilators',
    required: false,
    description: 'Instructor availability for invigilation',
    format: 'invigilators.csv',
    example: 'instructor_id,name,department,available_slots'
  },
  {
    name: 'Constraints',
    required: false,
    description: 'Custom scheduling constraints',
    format: 'constraints.json',
    example: '{"hard_constraints": [...], "soft_constraints": [...]}'
  }
]

interface DropZoneProps {
  onFilesSelected: (files: FileList) => void
  isDragActive: boolean
  onDragEnter: () => void
  onDragLeave: () => void
  onDragOver: (e: React.DragEvent) => void
  onDrop: (e: React.DragEvent) => void
}

function DropZone({ onFilesSelected, isDragActive, onDragEnter, onDragLeave, onDragOver, onDrop }: DropZoneProps) {
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  return (
    <div
      className={cn(
        "border-2 border-dashed rounded-lg p-12 text-center transition-colors",
        isDragActive 
          ? "border-blue-500 bg-blue-50" 
          : "border-gray-300 hover:border-gray-400"
      )}
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <UploadIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
      <h3 className="text-lg font-medium text-gray-900 mb-2">
        Drop files here or click to browse
      </h3>
      <p className="text-sm text-gray-500 mb-4">
        Upload CSV files and JSON constraints. Maximum file size: 10MB
      </p>
      <Button 
        onClick={() => fileInputRef.current?.click()}
        variant="outline"
      >
        Browse Files
      </Button>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".csv,.json"
        className="hidden"
        onChange={(e) => e.target.files && onFilesSelected(e.target.files)}
      />
    </div>
  )
}

interface FileValidationProps {
  fileName: string
  isValid: boolean
  errors: string[]
  onRemove: () => void
}

function FileValidationItem({ fileName, isValid, errors, onRemove }: FileValidationProps) {
  return (
    <div className="flex items-start space-x-3 p-4 border border-gray-200 rounded-lg">
      <div className="flex-shrink-0 mt-1">
        {isValid ? (
          <CheckCircle className="h-5 w-5 text-green-500" />
        ) : (
          <AlertCircle className="h-5 w-5 text-red-500" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-900">{fileName}</span>
            <Badge variant={isValid ? "default" : "destructive"}>
              {isValid ? "Valid" : "Error"}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onRemove}
            className="h-6 w-6 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        {!isValid && errors.length > 0 && (
          <div className="mt-2 space-y-1">
            {errors.map((error, index) => (
              <p key={index} className="text-xs text-red-600">
                • {error}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function Upload() {
  const { uploadStatus, setUploadStatus } = useAppStore()
  const uploadMutation = useFileUpload()
  const [isDragActive, setIsDragActive] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<{ [key: string]: File }>({})

  const handleDragEnter = useCallback(() => setIsDragActive(true), [])
  const handleDragLeave = useCallback(() => setIsDragActive(false), [])
  
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragActive(false)
    
    const files = Array.from(e.dataTransfer.files)
    handleFilesSelected(files)
  }, [])

  const handleFilesSelected = (fileList: FileList | File[]) => {
    const files = Array.from(fileList)
    const newUploadedFiles = { ...uploadedFiles }
    
    files.forEach(file => {
      // Determine file type based on name
      const fileName = file.name.toLowerCase()
      let fileType = ''
      
      if (fileName.includes('student')) fileType = 'students'
      else if (fileName.includes('course')) fileType = 'courses'
      else if (fileName.includes('registration')) fileType = 'registrations'
      else if (fileName.includes('room')) fileType = 'rooms'
      else if (fileName.includes('invigilator')) fileType = 'invigilators'
      else if (fileName.includes('constraint')) fileType = 'constraints'
      
      if (fileType) {
        newUploadedFiles[fileType] = file
      }
    })
    
    setUploadedFiles(newUploadedFiles)
    
    // Update store
    setUploadStatus({
      files: {
        ...uploadStatus.files,
        ...Object.fromEntries(
          Object.entries(newUploadedFiles).map(([key, file]) => [key, file])
        )
      }
    })
    
    // Validate files
    validateFiles(newUploadedFiles)
  }

  const validateFiles = (files: { [key: string]: File }) => {
    const validation = { ...uploadStatus.validation }
    
    Object.entries(files).forEach(([type, file]) => {
      // Mock validation logic
      const isCSV = file.name.endsWith('.csv')
      const isJSON = file.name.endsWith('.json')
      const isValidType = (type === 'constraints' && isJSON) || (type !== 'constraints' && isCSV)
      
      validation[type as keyof typeof validation] = {
        valid: isValidType && file.size > 0 && file.size < 10 * 1024 * 1024, // < 10MB
        errors: isValidType ? [] : [`Invalid file format. Expected ${type === 'constraints' ? '.json' : '.csv'}`]
      }
    })
    
    setUploadStatus({ validation })
  }

  const handleRemoveFile = (fileType: string) => {
    const newFiles = { ...uploadedFiles }
    delete newFiles[fileType]
    setUploadedFiles(newFiles)
    
    const newUploadFiles = { ...uploadStatus.files }
    newUploadFiles[fileType as keyof typeof newUploadFiles] = null
    
    setUploadStatus({ files: newUploadFiles })
  }

  const handleUpload = () => {
    const formData = new FormData()
    Object.entries(uploadedFiles).forEach(([type, file]) => {
      formData.append(type, file)
    })
    
    uploadMutation.mutate(formData)
  }

  const isReadyToUpload = fileRequirements
    .filter(req => req.required)
    .every(req => {
      const key = req.name.toLowerCase()
      return uploadedFiles[key] && uploadStatus.validation[key as keyof typeof uploadStatus.validation]?.valid
    })

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* File Requirements Checklist */}
      <Card>
        <CardHeader>
          <CardTitle>File Requirements</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {fileRequirements.map((req) => {
              const key = req.name.toLowerCase()
              const isUploaded = !!uploadedFiles[key]
              const isValid = uploadStatus.validation[key as keyof typeof uploadStatus.validation]?.valid
              
              return (
                <div key={req.name} className="flex items-start space-x-3 p-3 border border-gray-200 rounded-lg">
                  <div className="flex-shrink-0 mt-1">
                    {isUploaded && isValid ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : isUploaded ? (
                      <AlertCircle className="h-5 w-5 text-red-500" />
                    ) : (
                      <div className="h-5 w-5 border-2 border-gray-300 rounded-full" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium">{req.name}</span>
                      <Badge variant={req.required ? "destructive" : "secondary"}>
                        {req.required ? "Required" : "Optional"}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-500">{req.description}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Format: {req.format}
                    </p>
                    <p className="text-xs text-gray-400">
                      Example: {req.example}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Upload Area */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Files</CardTitle>
        </CardHeader>
        <CardContent>
          <DropZone
            onFilesSelected={handleFilesSelected}
            isDragActive={isDragActive}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          />
        </CardContent>
      </Card>

      {/* File Validation Display */}
      {Object.keys(uploadedFiles).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Uploaded Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(uploadedFiles).map(([type, file]) => {
                const validation = uploadStatus.validation[type as keyof typeof uploadStatus.validation]
                return (
                  <FileValidationItem
                    key={type}
                    fileName={file.name}
                    isValid={validation?.valid || false}
                    errors={validation?.errors || []}
                    onRemove={() => handleRemoveFile(type)}
                  />
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upload Progress */}
      {uploadStatus.isUploading && (
        <Alert>
          <UploadIcon className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span>Uploading files...</span>
                <span>{uploadStatus.progress}%</span>
              </div>
              <Progress value={uploadStatus.progress} />
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            onClick={() => {
              const link = document.createElement('a')
              link.href = '/templates/exam-timetabling-template.zip'
              link.download = 'exam-timetabling-template.zip'
              link.click()
            }}
          >
            <Download className="h-4 w-4 mr-2" />
            Download Templates
          </Button>
        </div>
        
        <Button
          onClick={handleUpload}
          disabled={!isReadyToUpload || uploadStatus.isUploading}
          className="min-w-32"
        >
          {uploadStatus.isUploading ? (
            <>Processing...</>
          ) : (
            <>
              <UploadIcon className="h-4 w-4 mr-2" />
              Upload & Validate
            </>
          )}
        </Button>
      </div>
    </div>
  )
}