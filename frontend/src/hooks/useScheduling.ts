import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { schedulingApi } from '../services/scheduling';
import { validateFile, type FileValidationResult } from '../utils/validation';
import { UPLOAD_CONFIG } from '../utils/constants';

// Types
export interface UploadProgress {
  [fileName: string]: number;
}

export interface UploadStatus {
  isUploading: boolean;
  progress: UploadProgress;
  results: FileValidationResult[];
  errors: string[];
  completed: boolean;
}

export interface UseFileUploadOptions {
  maxFiles?: number;
  acceptedFormats?: string[];
  maxFileSize?: number;
  onUploadStart?: () => void;
  onUploadComplete?: (results: FileValidationResult[]) => void;
  onUploadError?: (error: string) => void;
  onFileValidation?: (file: File, validation: FileValidationResult) => void;
}

export interface UseFileUploadReturn {
  // State
  uploadStatus: UploadStatus;
  acceptedFiles: File[];
  rejectedFiles: Array<{
    file: File;
    errors: Array<{ code: string; message: string }>;
  }>;
  
  // Actions
  uploadFiles: (files?: File[]) => Promise<void>;
  clearFiles: () => void;
  removeFile: (fileName: string) => void;
  retryUpload: () => Promise<void>;
  
  // Dropzone props
  getRootProps: () => any;
  getInputProps: () => any;
  isDragActive: boolean;
  isDragAccept: boolean;
  isDragReject: boolean;
}

export const useFileUpload = (options: UseFileUploadOptions = {}): UseFileUploadReturn => {
  const {
    maxFiles = 10,
    acceptedFormats = UPLOAD_CONFIG.ACCEPTED_FORMATS,
    maxFileSize = UPLOAD_CONFIG.MAX_FILE_SIZE,
    onUploadStart,
    onUploadComplete,
    onUploadError,
    onFileValidation,
  } = options;

  // State
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>({
    isUploading: false,
    progress: {},
    results: [],
    errors: [],
    completed: false,
  });

  const [files, setFiles] = useState<File[]>([]);

  // File validation function
  const validateFiles = useCallback((filesToValidate: File[]) => {
    const validFiles: File[] = [];
    const rejectedFiles: Array<{
      file: File;
      errors: Array<{ code: string; message: string }>;
    }> = [];

    filesToValidate.forEach(file => {
      const validation = validateFile(file);
      
      // Call validation callback
      if (onFileValidation) {
        onFileValidation(file, validation);
      }

      if (validation.isValid) {
        validFiles.push(file);
      } else {
        rejectedFiles.push({
          file,
          errors: validation.errors.map(error => ({
            code: 'validation-error',
            message: error,
          })),
        });
      }
    });

    return { validFiles, rejectedFiles };
  }, [onFileValidation]);

  // Upload progress handler
  const handleProgress = useCallback((fileIndex: number, progress: number) => {
    const fileName = files[fileIndex]?.name;
    if (fileName) {
      setUploadStatus(prev => ({
        ...prev,
        progress: {
          ...prev.progress,
          [fileName]: progress,
        },
      }));
    }
  }, [files]);

  // Upload files function
  const uploadFiles = useCallback(async (filesToUpload?: File[]) => {
    const targetFiles = filesToUpload || files;
    
    if (targetFiles.length === 0) {
      onUploadError?.('No files selected for upload');
      return;
    }

    // Validate files before upload
    const { validFiles, rejectedFiles } = validateFiles(targetFiles);
    
    if (validFiles.length === 0) {
      const errorMessage = 'No valid files to upload';
      setUploadStatus(prev => ({
        ...prev,
        errors: [errorMessage, ...rejectedFiles.map(rf => rf.errors[0]?.message).filter(Boolean)],
      }));
      onUploadError?.(errorMessage);
      return;
    }

    // Start upload
    setUploadStatus({
      isUploading: true,
      progress: {},
      results: [],
      errors: [],
      completed: false,
    });

    onUploadStart?.();

    try {
      const result = await schedulingApi.uploadFiles(validFiles, handleProgress);
      
      setUploadStatus(prev => ({
        ...prev,
        isUploading: false,
        results: result.files,
        completed: true,
        errors: result.overallValid ? [] : ['Some files have validation issues'],
      }));

      onUploadComplete?.(result.files);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      
      setUploadStatus(prev => ({
        ...prev,
        isUploading: false,
        errors: [errorMessage],
        completed: false,
      }));

      onUploadError?.(errorMessage);
    }
  }, [files, validateFiles, handleProgress, onUploadStart, onUploadComplete, onUploadError]);

  // Clear files
  const clearFiles = useCallback(() => {
    setFiles([]);
    setUploadStatus({
      isUploading: false,
      progress: {},
      results: [],
      errors: [],
      completed: false,
    });
  }, []);

  // Remove specific file
  const removeFile = useCallback((fileName: string) => {
    setFiles(prev => prev.filter(file => file.name !== fileName));
    setUploadStatus(prev => ({
      ...prev,
      progress: Object.fromEntries(
        Object.entries(prev.progress).filter(([name]) => name !== fileName)
      ),
      results: prev.results.filter(result => result.fileName !== fileName),
    }));
  }, []);

  // Retry upload
  const retryUpload = useCallback(async () => {
    await uploadFiles();
  }, [uploadFiles]);

  // Dropzone configuration
  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Validate and add accepted files
    const { validFiles } = validateFiles(acceptedFiles);
    
    setFiles(prev => {
      const newFiles = [...prev, ...validFiles];
      return newFiles.slice(0, maxFiles); // Respect max files limit
    });

    // Handle rejected files
    if (rejectedFiles.length > 0) {
      const rejectionErrors = rejectedFiles.map(rejection => 
        rejection.errors.map((error: any) => error.message).join(', ')
      );
      
      setUploadStatus(prev => ({
        ...prev,
        errors: [...prev.errors, ...rejectionErrors],
      }));
    }
  }, [validateFiles, maxFiles]);

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragAccept,
    isDragReject,
    acceptedFiles,
    fileRejections,
  } = useDropzone({
    onDrop,
    accept: acceptedFormats.reduce((acc, format) => {
      acc[format] = [];
      return acc;
    }, {} as Record<string, string[]>),
    maxSize: maxFileSize,
    maxFiles,
    multiple: true,
  });

  return {
    // State
    uploadStatus,
    acceptedFiles: files,
    rejectedFiles: fileRejections,
    
    // Actions
    uploadFiles,
    clearFiles,
    removeFile,
    retryUpload,
    
    // Dropzone props
    getRootProps,
    getInputProps,
    isDragActive,
    isDragAccept,
    isDragReject,
  };
};

// Hook for single file upload
export const useSingleFileUpload = (
  fileType: string,
  options: Omit<UseFileUploadOptions, 'maxFiles'> = {}
) => {
  const singleFileOptions = {
    ...options,
    maxFiles: 1,
  };

  const fileUpload = useFileUpload(singleFileOptions);

  const uploadSingleFile = useCallback(async (file: File) => {
    try {
      fileUpload.uploadStatus.isUploading = true;
      
      const result = await schedulingApi.uploadSingleFile(
        file,
        fileType,
        (progress) => fileUpload.uploadStatus.progress[file.name] = progress
      );

      fileUpload.uploadStatus.isUploading = false;
      fileUpload.uploadStatus.results = [result];
      fileUpload.uploadStatus.completed = true;

      options.onUploadComplete?.([result]);

      return result;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      fileUpload.uploadStatus.isUploading = false;
      fileUpload.uploadStatus.errors = [errorMessage];
      
      options.onUploadError?.(errorMessage);
      throw error;
    }
  }, [fileType, fileUpload.uploadStatus, options]);

  return {
    ...fileUpload,
    uploadSingleFile,
  };
};

// Hook for batch file upload with progress tracking
export const useBatchFileUpload = () => {
  const [batchStatus, setBatchStatus] = useState({
    isProcessing: false,
    totalFiles: 0,
    processedFiles: 0,
    successfulFiles: 0,
    failedFiles: 0,
    results: [] as FileValidationResult[],
    errors: [] as string[],
  });

  const uploadBatch = useCallback(async (
    files: Array<{ file: File; type: string }>,
    onProgress?: (progress: { completed: number; total: number }) => void
  ) => {
    setBatchStatus({
      isProcessing: true,
      totalFiles: files.length,
      processedFiles: 0,
      successfulFiles: 0,
      failedFiles: 0,
      results: [],
      errors: [],
    });

    const results: FileValidationResult[] = [];
    const errors: string[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const { file, type } = files[i];
      
      try {
        const result = await schedulingApi.uploadSingleFile(file, type);
        results.push(result);
        
        setBatchStatus(prev => ({
          ...prev,
          processedFiles: i + 1,
          successfulFiles: prev.successfulFiles + 1,
          results: [...prev.results, result],
        }));

      } catch (error) {
        const errorMessage = `Failed to upload ${file.name}: ${
          error instanceof Error ? error.message : 'Unknown error'
        }`;
        errors.push(errorMessage);
        
        setBatchStatus(prev => ({
          ...prev,
          processedFiles: i + 1,
          failedFiles: prev.failedFiles + 1,
          errors: [...prev.errors, errorMessage],
        }));
      }

      // Report progress
      onProgress?.({ completed: i + 1, total: files.length });
    }

    setBatchStatus(prev => ({
      ...prev,
      isProcessing: false,
    }));

    return { results, errors };
  }, []);

  const resetBatch = useCallback(() => {
    setBatchStatus({
      isProcessing: false,
      totalFiles: 0,
      processedFiles: 0,
      successfulFiles: 0,
      failedFiles: 0,
      results: [],
      errors: [],
    });
  }, []);

  return {
    batchStatus,
    uploadBatch,
    resetBatch,
  };
};