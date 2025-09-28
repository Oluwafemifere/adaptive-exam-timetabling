import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  LinearProgress,
  Alert,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  GetApp as DownloadIcon,
  Description as FileIcon,
} from '@mui/icons-material';
import { useFileUpload } from '@hooks/useFileUpload';
import { useSchedulingStore } from '@store/schedulingSlice';
import { UPLOAD_CONFIG } from '@utils/constants';
import { formatFileSize } from '@utils/formatting';
import { useNavigate } from 'react-router-dom';

// File Requirements Component
const FileRequirements: React.FC = () => {
  const requirements = [
    {
      file: 'students.csv',
      description: 'Student information (ID, name, programme, level)',
      required: true,
      example: 'studentid,firstname,lastname,email,programme,level',
    },
    {
      file: 'courses.csv',
      description: 'Course details (code, title, units, level)',
      required: true,
      example: 'coursecode,title,units,level,semester',
    },
    {
      file: 'registrations.csv',
      description: 'Student course registrations',
      required: true,
      example: 'studentid,coursecode,semester,academicyear',
    },
    {
      file: 'rooms.csv',
      description: 'Room information (code, building, capacity)',
      required: true,
      example: 'roomcode,building,capacity,type,facilities',
    },
    {
      file: 'invigilators.csv',
      description: 'Staff availability for invigilation',
      required: false,
      example: 'staffid,name,email,department,maxexamsperday',
    },
    {
      file: 'constraints.json',
      description: 'Custom constraint configurations',
      required: false,
      example: '{"examDistribution": 0.8, "roomUtilization": 0.6}',
    },
  ];

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          File Requirements
        </Typography>
        <List dense>
          {requirements.map((req, index) => (
            <ListItem key={index} divider={index < requirements.length - 1}>
              <ListItemIcon>
                {req.required ? (
                  <CheckIcon color="success" />
                ) : (
                  <FileIcon color="action" />
                )}
              </ListItemIcon>
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="subtitle2">{req.file}</Typography>
                    <Chip
                      size="small"
                      label={req.required ? 'Required' : 'Optional'}
                      color={req.required ? 'error' : 'default'}
                      variant="outlined"
                    />
                  </Box>
                }
                secondary={
                  <Box>
                    <Typography variant="body2" color="text.secondary" mb={0.5}>
                      {req.description}
                    </Typography>
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        fontFamily: 'monospace', 
                        backgroundColor: 'grey.100', 
                        p: 0.5,
                        borderRadius: 0.5,
                        display: 'block',
                      }}
                    >
                      {req.example}
                    </Typography>
                  </Box>
                }
              />
            </ListItem>
          ))}
        </List>
        
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>Tips:</strong>
            <br />• Files must be in CSV format (except constraints.json)
            <br />• Maximum file size: {formatFileSize(UPLOAD_CONFIG.MAX_FILE_SIZE)}
            <br />• Ensure column headers match the examples exactly
            <br />• Remove any special characters or extra spaces
          </Typography>
        </Alert>
      </CardContent>
    </Card>
  );
};

// Upload Progress Component
interface UploadProgressProps {
  uploadStatus: any;
  acceptedFiles: File[];
  onRemoveFile: (fileName: string) => void;
  onRetryUpload: () => void;
}

const UploadProgress: React.FC<UploadProgressProps> = ({
  uploadStatus,
  acceptedFiles,
  onRemoveFile,
  onRetryUpload,
}) => {
  if (acceptedFiles.length === 0 && !uploadStatus.completed) {
    return null;
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Upload Progress
          </Typography>
          {uploadStatus.errors.length > 0 && !uploadStatus.isUploading && (
            <Button
              size="small"
              startIcon={<RefreshIcon />}
              onClick={onRetryUpload}
              color="primary"
            >
              Retry
            </Button>
          )}
        </Box>

        <List>
          {acceptedFiles.map((file, index) => {
            const progress = uploadStatus.progress[file.name] || 0;
            const result = uploadStatus.results.find((r: any) => r.fileName === file.name);
            
            return (
              <ListItem key={file.name} divider={index < acceptedFiles.length - 1}>
                <ListItemIcon>
                  {result ? (
                    result.isValid ? (
                      <CheckIcon color="success" />
                    ) : (
                      <ErrorIcon color="error" />
                    )
                  ) : uploadStatus.isUploading ? (
                    <UploadIcon color="primary" />
                  ) : (
                    <FileIcon />
                  )}
                </ListItemIcon>
                
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" justifyContent="space-between">
                      <Typography variant="subtitle2">{file.name}</Typography>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="caption" color="text.secondary">
                          {formatFileSize(file.size)}
                        </Typography>
                        {!uploadStatus.isUploading && !result && (
                          <IconButton
                            size="small"
                            onClick={() => onRemoveFile(file.name)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        )}
                      </Box>
                    </Box>
                  }
                  secondary={
                    <Box>
                      {uploadStatus.isUploading && (
                        <Box sx={{ mt: 1 }}>
                          <LinearProgress 
                            variant="determinate" 
                            value={progress} 
                            sx={{ height: 6, borderRadius: 3 }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {Math.round(progress)}% complete
                          </Typography>
                        </Box>
                      )}
                      
                      {result && (
                        <Box sx={{ mt: 1 }}>
                          {result.errors.length > 0 && (
                            <Alert severity="error" sx={{ mt: 1 }}>
                              <Typography variant="caption">
                                {result.errors[0]} {result.errors.length > 1 && `(+${result.errors.length - 1} more)`}
                              </Typography>
                            </Alert>
                          )}
                          {result.warnings.length > 0 && (
                            <Alert severity="warning" sx={{ mt: 1 }}>
                              <Typography variant="caption">
                                {result.warnings[0]} {result.warnings.length > 1 && `(+${result.warnings.length - 1} more)`}
                              </Typography>
                            </Alert>
                          )}
                          {result.isValid && (
                            <Typography variant="caption" color="success.main">
                              ✓ Validation successful - {result.recordCount} records
                            </Typography>
                          )}
                        </Box>
                      )}
                    </Box>
                  }
                />
              </ListItem>
            );
          })}
        </List>

        {uploadStatus.errors.length > 0 && (
          <Alert severity="error" sx={{ mt: 2 }}>
            <Typography variant="body2">
              {uploadStatus.errors[0]}
            </Typography>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

// Main Upload Component
const Upload: React.FC = () => {
  const navigate = useNavigate();
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);
  
  const {
    uploadStatus,
    acceptedFiles,
    rejectedFiles,
    uploadFiles,
    clearFiles,
    removeFile,
    retryUpload,
    getRootProps,
    getInputProps,
    isDragActive,
    isDragAccept,
    isDragReject,
  } = useFileUpload({
    maxFiles: 6,
    onUploadComplete: (results) => {
      // Store results in scheduling store
      useSchedulingStore.getState().setValidationResults(
        results.reduce((acc, result) => {
          acc[result.fileName] = result;
          return acc;
        }, {} as any)
      );
    },
  });

  const handleGenerateSchedule = () => {
    navigate('/scheduling');
  };

  const handleDownloadTemplate = (fileName: string) => {
    // In a real app, this would download a CSV template
    const templates: Record<string, string> = {
      'students.csv': 'studentid,firstname,lastname,email,programme,level\nSTU001,John,Doe,john.doe@example.com,Computer Science,300',
      'courses.csv': 'coursecode,title,units,level,semester\nCSC301,Database Systems,3,300,1',
      'registrations.csv': 'studentid,coursecode,semester,academicyear\nSTU001,CSC301,1,2023/24',
      'rooms.csv': 'roomcode,building,capacity,type,facilities\nA-01,Main Building,50,Classroom,Projector;AC',
    };

    const content = templates[fileName] || '';
    const blob = new Blob([content], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  const getDropzoneStyle = () => {
    let backgroundColor = 'background.default';
    let borderColor = 'divider';
    
    if (isDragActive) {
      if (isDragAccept) {
        backgroundColor = 'primary.50';
        borderColor = 'primary.main';
      } else if (isDragReject) {
        backgroundColor = 'error.50';
        borderColor = 'error.main';
      }
    }
    
    return { backgroundColor, borderColor };
  };

  const allFilesValid = uploadStatus.completed && 
    uploadStatus.results.length > 0 &&
    uploadStatus.results.every((r: any) => r.isValid) &&
    uploadStatus.results.some((r: any) => UPLOAD_CONFIG.REQUIRED_FILES.some(req => r.fileName.includes(req.replace('.csv', ''))));

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      {/* Header */}
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          Upload Data
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload your CSV files to get started with exam timetabling.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Upload Area */}
        <Grid item xs={12} md={8}>
          {/* Drag & Drop Zone */}
          <Paper
            {...getRootProps()}
            sx={{
              p: 4,
              mb: 3,
              textAlign: 'center',
              border: '2px dashed',
              borderRadius: 2,
              cursor: 'pointer',
              transition: 'all 0.2s',
              ...getDropzoneStyle(),
            }}
          >
            <input {...getInputProps()} />
            <UploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
            
            {isDragActive ? (
              <Typography variant="h6" color="primary">
                {isDragAccept ? 'Drop files here...' : 'Some files are not supported'}
              </Typography>
            ) : (
              <Box>
                <Typography variant="h6" gutterBottom>
                  Drop files here or click to browse
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  Supported formats: {UPLOAD_CONFIG.ACCEPTED_FORMATS.join(', ')} 
                  (Max {formatFileSize(UPLOAD_CONFIG.MAX_FILE_SIZE)})
                </Typography>
                <Button variant="outlined" size="large">
                  Select Files
                </Button>
              </Box>
            )}
          </Paper>

          {/* Template Download */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="h6" gutterBottom>
                    Need templates?
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Download CSV templates with the correct format and sample data.
                  </Typography>
                </Box>
                <Button
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  onClick={() => setShowTemplateDialog(true)}
                >
                  Download Templates
                </Button>
              </Box>
            </CardContent>
          </Card>

          {/* Upload Progress */}
          <UploadProgress
            uploadStatus={uploadStatus}
            acceptedFiles={acceptedFiles}
            onRemoveFile={removeFile}
            onRetryUpload={retryUpload}
          />

          {/* Action Buttons */}
          {acceptedFiles.length > 0 && (
            <Box display="flex" gap={2} mt={3}>
              <Button
                variant="contained"
                size="large"
                disabled={uploadStatus.isUploading}
                onClick={() => uploadFiles()}
                sx={{ minWidth: 120 }}
              >
                {uploadStatus.isUploading ? 'Uploading...' : 'Upload Files'}
              </Button>
              
              <Button
                variant="outlined"
                size="large"
                onClick={clearFiles}
                disabled={uploadStatus.isUploading}
              >
                Clear All
              </Button>
              
              {allFilesValid && (
                <Button
                  variant="contained"
                  color="success"
                  size="large"
                  onClick={handleGenerateSchedule}
                >
                  Generate Schedule
                </Button>
              )}
            </Box>
          )}
        </Grid>

        {/* File Requirements */}
        <Grid item xs={12} md={4}>
          <FileRequirements />
        </Grid>
      </Grid>

      {/* Template Download Dialog */}
      <Dialog open={showTemplateDialog} onClose={() => setShowTemplateDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Download CSV Templates</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Click on any template to download it with sample data:
          </Typography>
          <List>
            {UPLOAD_CONFIG.REQUIRED_FILES.concat(UPLOAD_CONFIG.OPTIONAL_FILES).map((file, index) => (
              <ListItem 
                key={file}
                button
                onClick={() => handleDownloadTemplate(file)}
                divider={index < UPLOAD_CONFIG.REQUIRED_FILES.length + UPLOAD_CONFIG.OPTIONAL_FILES.length - 1}
              >
                <ListItemIcon>
                  <DownloadIcon />
                </ListItemIcon>
                <ListItemText
                  primary={file}
                  secondary={UPLOAD_CONFIG.REQUIRED_FILES.includes(file) ? 'Required' : 'Optional'}
                />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTemplateDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Upload;