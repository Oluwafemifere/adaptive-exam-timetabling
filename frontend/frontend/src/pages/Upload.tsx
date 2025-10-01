// src/pages/Upload.tsx
import React, { useState, useCallback } from 'react';
import { 
  Upload as UploadIcon, 
  FileText, 
  CheckCircle, 
  X,
  Download,
  Loader2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { useAppStore } from '../store';
import { useFileUpload } from '../hooks/useApi';
import { cn } from '../components/ui/utils';
import { toast } from 'sonner';

// ... (FileRequirement and DropZone components remain unchanged)
interface FileRequirement {
  name: string
  entityType: string
  required: boolean
  description: string
  format: string
}

const fileRequirements: FileRequirement[] = [
  { name: 'Students', entityType: 'students', required: true, description: 'Student enrollment data', format: '.csv' },
  { name: 'Courses', entityType: 'courses', required: true, description: 'Course information', format: '.csv' },
  { name: 'Registrations', entityType: 'registrations', required: true, description: 'Student course registrations', format: '.csv' },
  { name: 'Rooms', entityType: 'rooms', required: true, description: 'Available rooms and capacities', format: '.csv' },
  { name: 'Invigilators', entityType: 'invigilators', required: false, description: 'Staff availability for invigilation', format: '.csv' },
  { name: 'Constraints', entityType: 'constraints', required: false, description: 'Custom scheduling constraints', format: '.json' },
]

interface DropZoneProps {
  onFilesSelected: (files: FileList) => void;
  isDragActive: boolean;
  onDragEnter: () => void;
  onDragLeave: () => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
}

function DropZone({ onFilesSelected, isDragActive, ...dragProps }: DropZoneProps) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  return (
    <div
      className={cn( "border-2 border-dashed rounded-lg p-12 text-center transition-colors", isDragActive ? "border-primary bg-primary/10" : "border-border hover:border-muted-foreground" )}
      {...dragProps}
    >
      <UploadIcon className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-lg font-medium mb-2">Drop files here or click to browse</h3>
      <p className="text-sm text-muted-foreground mb-4">Upload CSV and JSON files. Max file size: 10MB each.</p>
      <Button onClick={() => fileInputRef.current?.click()} variant="outline">Browse Files</Button>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".csv,.json"
        className="hidden"
        onChange={(e) => e.target.files && onFilesSelected(e.target.files)}
      />
    </div>
  );
}


function FileValidationItem({ fileName, onRemove }: { fileName: string, onRemove: () => void }) {
  return (
    <div className="flex items-center justify-between space-x-3 p-3 border rounded-lg">
      <div className="flex items-center space-x-3 min-w-0">
        <FileText className="h-5 w-5 text-muted-foreground flex-shrink-0" />
        <span className="text-sm font-medium truncate">{fileName}</span>
      </div>
      <Button variant="ghost" size="sm" onClick={onRemove} className="h-6 w-6 p-0">
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}


export function Upload() {
  const { uploadStatus, setUploadStatus } = useAppStore();
  const uploadMutation = useFileUpload();
  const [isDragActive, setIsDragActive] = useState(false);
  const [stagedFiles, setStagedFiles] = useState<{ [key: string]: File }>({});

  const handleFilesSelected = (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    const newStagedFiles = { ...stagedFiles };

    files.forEach(file => {
      const fileName = file.name.toLowerCase();
      const requirement = fileRequirements.find(req => fileName.includes(req.entityType));
      if (requirement) {
        newStagedFiles[requirement.entityType] = file;
      } else {
        toast.warning(`Could not identify file type for "${file.name}".`);
      }
    });
    setStagedFiles(newStagedFiles);
  };
  
  const handleRemoveFile = (entityType: string) => {
    const newFiles = { ...stagedFiles };
    delete newFiles[entityType];
    setStagedFiles(newFiles);
  };

  const handleUploadAll = async () => {
    const requiredFilesMet = fileRequirements
      .filter(req => req.required)
      .every(req => stagedFiles[req.entityType]);

    if (!requiredFilesMet) {
      toast.error("Please select all required files before uploading.");
      return;
    }

    setUploadStatus({ isUploading: true, progress: 0 });
    const totalFiles = Object.keys(stagedFiles).length;
    let uploadedCount = 0;

    for (const [entityType, file] of Object.entries(stagedFiles)) {
      const formData = new FormData();
      formData.append('file', file);
      try {
        await uploadMutation.mutateAsync({ formData, entityType });
        uploadedCount++;
        setUploadStatus({ progress: (uploadedCount / totalFiles) * 100 });
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      } catch (error) {
        setUploadStatus({ isUploading: false });
        // The error toast is already handled in the useFileUpload hook
        break; // Stop on first error
      }
    }

    if (uploadedCount === totalFiles) {
        setUploadStatus({ isUploading: false });
        setStagedFiles({}); // Clear staged files on success
    }
  };

  // Drag and drop handlers
  const handleDragEnter = useCallback(() => setIsDragActive(true), []);
  const handleDragLeave = useCallback(() => setIsDragActive(false), []);
  const handleDragOver = useCallback((e: React.DragEvent) => e.preventDefault(), []);
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    handleFilesSelected(e.dataTransfer.files);
  }, []);


  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>File Requirements</CardTitle>
          <CardDescription>Upload the following files to provide data for the scheduling engine. Required files are marked with an asterisk.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {fileRequirements.map((req) => {
              const isStaged = !!stagedFiles[req.entityType];
              return (
                <div key={req.entityType} className={cn("flex items-start space-x-3 p-3 border rounded-lg", isStaged && "border-green-500 bg-green-50 dark:bg-green-900/20")}>
                  <div className="flex-shrink-0 mt-1">
                    {isStaged ? <CheckCircle className="h-5 w-5 text-green-500" /> : <div className="h-5 w-5 border-2 border-muted-foreground rounded-full" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="font-medium">{req.name}{req.required && <span className="text-destructive">*</span>}</span>
                    <p className="text-sm text-muted-foreground">{req.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Upload Files</CardTitle></CardHeader>
        <CardContent>
          <DropZone onFilesSelected={handleFilesSelected} isDragActive={isDragActive} onDragEnter={handleDragEnter} onDragLeave={handleDragLeave} onDragOver={handleDragOver} onDrop={handleDrop} />
        </CardContent>
      </Card>
      
      {Object.keys(stagedFiles).length > 0 && (
        <Card>
          <CardHeader><CardTitle>Staged Files</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(stagedFiles).map(([type, file]) => (
              <FileValidationItem key={type} fileName={file.name} onRemove={() => handleRemoveFile(type)} />
            ))}
          </CardContent>
        </Card>
      )}

      {uploadStatus.isUploading && (
        <Card>
            <CardContent className="pt-6">
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <p className="text-sm font-medium">Uploading & Processing Files...</p>
                        <p className="text-sm text-muted-foreground">{Math.round(uploadStatus.progress)}%</p>
                    </div>
                    <Progress value={uploadStatus.progress} />
                </div>
            </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={() => window.open('/templates/exam-timetabling-template.zip', '_blank')}>
          <Download className="h-4 w-4 mr-2" />
          Download Templates
        </Button>
        <Button onClick={handleUploadAll} disabled={uploadStatus.isUploading || Object.keys(stagedFiles).length === 0} className="min-w-32">
          {uploadStatus.isUploading ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Processing...</> : <><UploadIcon className="h-4 w-4 mr-2" /> Upload & Validate</>}
        </Button>
      </div>
    </div>
  );
}