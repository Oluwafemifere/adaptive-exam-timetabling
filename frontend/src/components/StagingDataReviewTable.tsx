// frontend/src/components/StagingDataReviewTable.tsx
import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { useStagedData } from '../hooks/useApi';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Alert, AlertDescription } from './ui/alert';
import { Loader2, AlertTriangle, Database } from 'lucide-react';
import { toast } from 'sonner';

// --- Helper Functions ---
const formatHeader = (header: string) => {
  return header.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
};

// --- Data Viewer Component ---
const DataViewer = ({ entityType, sessionId }: { entityType: string; sessionId: string }) => {
  const { data, isLoading, error } = useStagedData(sessionId, entityType);

  // --- FIX START ---
  // The useMemo hook is moved to the top level of the component.
  // This ensures it is called on every render, satisfying the Rules of Hooks.
  // It also safely handles the case where 'data' is null or empty.
  const columns = useMemo(() => {
    if (!data || data.length === 0) {
      return [];
    }
    // Get columns from the first data row.
    return Object.keys(data[0] || {});
  }, [data]);
  // --- FIX END ---
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="ml-2 text-muted-foreground">Loading {formatHeader(entityType)} data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="mt-4">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          {error.message}
        </AlertDescription>
      </Alert>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex justify-center items-center h-64 flex-col">
         <Database className="h-8 w-8 text-muted-foreground mb-2"/>
        <p className="text-muted-foreground">No data found for {formatHeader(entityType)}.</p>
         <p className="text-sm text-muted-foreground">The file might be empty or still processing.</p>
      </div>
    );
  }

  return (
    <div className="mt-4 border rounded-lg overflow-auto max-h-[60vh]">
      <Table>
        <TableHeader className="sticky top-0 bg-background z-10">
          <TableRow>
            {columns.map(col => <TableHead key={col}>{formatHeader(col)}</TableHead>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {columns.map(col => (
                <TableCell key={`${rowIndex}-${col}`} className="text-sm">
                  {typeof row[col] === 'boolean' ? (row[col] ? 'Yes' : 'No') : row[col] ?? 'N/A'}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};


// --- Main Component ---
interface StagingDataReviewTableProps {
  sessionId: string | null;
  uploadedFiles: Record<string, any>;
}

export function StagingDataReviewTable({ sessionId, uploadedFiles }: StagingDataReviewTableProps) {
  const uploadedKeys = useMemo(() => Object.keys(uploadedFiles).filter(key => uploadedFiles[key]), [uploadedFiles]);

  if (!sessionId) {
    return <Alert variant="destructive"><AlertDescription>A session ID is required to review data.</AlertDescription></Alert>;
  }

  if (uploadedKeys.length === 0) {
    return (
       <div className="py-8 text-center border-2 border-dashed rounded-lg">
          <Database className="h-8 w-8 mx-auto text-muted-foreground mb-2"/>
          <p className="font-medium">Staging Data Review Table</p>
          <p className="text-sm text-muted-foreground">Upload files in the previous step to review them here.</p>
       </div>
    );
  }

  return (
    <Tabs defaultValue={uploadedKeys[0]} className="w-full">
      <TabsList>
        {uploadedKeys.map(fileKey => (
          <TabsTrigger key={fileKey} value={fileKey}>
            {formatHeader(fileKey)}
          </TabsTrigger>
        ))}
      </TabsList>
      {uploadedKeys.map(fileKey => (
        <TabsContent key={fileKey} value={fileKey}>
          <DataViewer entityType={fileKey} sessionId={sessionId} />
        </TabsContent>
      ))}
    </Tabs>
  );
}