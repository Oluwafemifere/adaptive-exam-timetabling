// frontend/src/components/StagingDataReviewTable.tsx
import React, { useMemo, useState, useEffect } from 'react';
import { useAllStagedData, useStagedData } from '../hooks/useApi';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from './ui/accordion';
import { Alert, AlertDescription } from './ui/alert';
import { Loader2, AlertTriangle, Database, PlusCircle, Pencil, Trash2, Search } from 'lucide-react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { Input } from './ui/input';
import { StagingRecord } from '../store/types';
import { StagingDataForm } from './StagingDataForm';
import { EditableStagingDataRow } from './EditableStagingDataRow';
import { formatHeader } from '../utils/utils';
import { Badge } from './ui/badge';

// --- Configuration for Primary Keys ---
const ENTITY_PRIMARY_KEYS: Record<string, string[]> = {
  buildings: ['code'],
  courses: ['code'],
  departments: ['code'],
  faculties: ['code'],
  programmes: ['code'],
  rooms: ['code'],
  staff: ['staff_number'],
  students: ['matric_number'],
  course_departments: ['course_code', 'department_code'],
  course_faculties: ['course_code', 'faculty_code'],
  course_instructors: ['staff_number', 'course_code'],
  course_registrations: ['student_matric_number', 'course_code'],
  staff_unavailability: ['staff_number', 'unavailable_date', 'period_name'],
};

// --- Entities to be displayed in a grouped view ---
const GROUPED_ENTITIES = ['course_registrations', 'course_instructors'];

// --- Type definitions ---
interface SimpleCourse { code: string; title: string; course_level: number; semester: number; }
interface SimpleStudent { matric_number: string; first_name: string; last_name: string; }
interface SimpleStaff { staff_number: string; first_name: string; last_name: string; }

// --- Generic Flat Data Viewer ---
const FlatDataViewer = ({ entityType, data, sessionId, allData, onRefetch }: { entityType: string; data: StagingRecord[]; sessionId: string; allData: any; onRefetch: () => Promise<void> }) => {
  const { addRecord, updateRecord, deleteRecord, setRefetch } = useStagedData(sessionId, entityType);
  useEffect(() => { setRefetch(onRefetch) }, [onRefetch, setRefetch]);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<StagingRecord | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  const primaryKeys = useMemo(() => ENTITY_PRIMARY_KEYS[entityType] || ['code'], [entityType]);
  
  const columns = useMemo(() => {
    if (!allData[entityType] || allData[entityType].length === 0) return [];
    
    const allKeys = Object.keys(allData[entityType][0] || {});
    
    const filteredKeys = allKeys.filter(c => 
        c.toLowerCase() !== 'id' && 
        !c.toLowerCase().endsWith('_id') &&
        !c.toLowerCase().endsWith('_at')
    );
    
    // Define a preferred order for common fields to ensure consistency
    const preferredOrder = [
        'code', 'name', 'title', 'first_name', 'last_name', 'email', 
        'staff_number', 'matric_number', 'course_code', 'department_code', 
        'faculty_code', 'programme_code', 'building_code', 'room_code',
        'capacity', 'course_level', 'semester'
    ];

    return [...filteredKeys].sort((a, b) => {
        const indexA = preferredOrder.indexOf(a);
        const indexB = preferredOrder.indexOf(b);
        if (indexA !== -1 && indexB !== -1) return indexA - indexB;
        if (indexA !== -1) return -1;
        if (indexB !== -1) return 1;
        return a.localeCompare(b);
    });
  }, [allData, entityType]);

  const handleCreate = () => {
    const newRecordTemplate = columns.reduce((acc, col) => ({ ...acc, [col]: '' }), {});
    setSelectedRecord(newRecordTemplate as StagingRecord);
    setIsEditing(false);
    setIsFormOpen(true);
  };
  
  const handleEdit = (record: StagingRecord) => {
    setSelectedRecord(record);
    setIsEditing(true);
    setIsFormOpen(true);
  };
  
  const handleDelete = (record: StagingRecord) => {
    setSelectedRecord(record);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (selectedRecord) {
      const pks = primaryKeys.map(pk => selectedRecord[pk]);
      await deleteRecord(pks);
      setIsDeleteDialogOpen(false);
      setSelectedRecord(null);
    }
  };
  
  const handleSave = async (formData: StagingRecord) => {
    if (isEditing && selectedRecord) {
        const pks = primaryKeys.map(pk => selectedRecord[pk]);
        await updateRecord(pks, formData);
    } else {
        await addRecord(formData);
    }
    setIsFormOpen(false);
    setSelectedRecord(null);
  };
  
  return (
    <div className="mt-4">
       <div className="flex justify-end mb-4">
          <Button onClick={handleCreate}><PlusCircle className="h-4 w-4 mr-2" />Add New {formatHeader(entityType)}</Button>
      </div>
      
      {!data || data.length === 0 ? (
        <div className="flex justify-center items-center h-64 flex-col border-2 border-dashed rounded-lg">
          <Database className="h-8 w-8 text-muted-foreground mb-2"/><p className="text-muted-foreground">No matching data found for {formatHeader(entityType)}.</p>
        </div>
      ) : (
        <div className="border rounded-lg overflow-auto max-h-[60vh]">
          <Table>
            <TableHeader className="sticky top-0 bg-background z-10">
              <TableRow>
                {columns.map(col => <TableHead key={col}>{formatHeader(col)}</TableHead>)}
                <TableHead className="sticky right-0 bg-background">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>{data.map((row, index) => (<EditableStagingDataRow key={index} row={row} columns={columns} onEdit={handleEdit} onDelete={handleDelete} />))}</TableBody>
          </Table>
        </div>
      )}

      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}><DialogContent className="max-w-3xl">
          <DialogHeader><DialogTitle>{isEditing ? 'Edit' : 'Create'} {formatHeader(entityType)} Record</DialogTitle></DialogHeader>
          {selectedRecord && <StagingDataForm record={selectedRecord} entityType={entityType} columns={columns} primaryKeys={primaryKeys} allData={allData} onSave={handleSave} onCancel={() => setIsFormOpen(false)} isEditing={isEditing} />}
      </DialogContent></Dialog>
      
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}><AlertDialogContent>
          <AlertDialogHeader><AlertDialogTitle>Are you sure?</AlertDialogTitle><AlertDialogDescription>This action cannot be undone. This will permanently delete the record.</AlertDialogDescription></AlertDialogHeader>
          <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={handleConfirmDelete}>Continue</AlertDialogAction></AlertDialogFooter>
      </AlertDialogContent></AlertDialog>
    </div>
  );
};


// --- Specialized Grouped Data Viewer ---
const GroupedDataViewer = ({ entityType, allData, sessionId, searchTerm, onRefetch }: { entityType: string; allData: any; sessionId: string; searchTerm: string; onRefetch: () => Promise<void> }) => {
    const { addRecord, updateRecord, deleteRecord, setRefetch } = useStagedData(sessionId, entityType);
    useEffect(() => { setRefetch(onRefetch) }, [onRefetch, setRefetch]);

    const [isFormOpen, setIsFormOpen] = useState(false);
    const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
    const [selectedRecord, setSelectedRecord] = useState<StagingRecord | null>(null);
    const [isEditing, setIsEditing] = useState(false);

    const primaryKeys = useMemo(() => ENTITY_PRIMARY_KEYS[entityType] || [], [entityType]);

    const { groupedData, columns, childEntityName } = useMemo(() => {
        if (!allData) return { groupedData: [], columns: [], childEntityName: '' };

        const courseMap = new Map<string, SimpleCourse>(allData.courses?.map((c: SimpleCourse) => [c.code, c]) || []);
        const studentMap = new Map<string, SimpleStudent>(allData.students?.map((s: SimpleStudent) => [s.matric_number, s]) || []);
        const staffMap = new Map<string, SimpleStaff>(allData.staff?.map((s: SimpleStaff) => [s.staff_number, s]) || []);

        const result = new Map<string, { course: SimpleCourse; relations: any[] }>();
        let relationColumns: string[] = [];
        let name = '';

        if (entityType === 'course_registrations') {
            name = 'Student';
            relationColumns = ['student_matric_number', 'student_name', 'registration_type'];
            allData.course_registrations?.forEach((reg: any) => {
                const course = courseMap.get(reg.course_code);
                if (!course) return;
                if (!result.has(reg.course_code)) result.set(reg.course_code, { course, relations: [] });
                const student = studentMap.get(reg.student_matric_number);
                result.get(reg.course_code)?.relations.push({ ...reg, student_name: student ? `${student.first_name} ${student.last_name}` : 'Unknown' });
            });
        } else if (entityType === 'course_instructors') {
            name = 'Instructor';
            relationColumns = ['staff_number', 'staff_name'];
            allData.course_instructors?.forEach((inst: any) => {
                const course = courseMap.get(inst.course_code);
                if (!course) return;
                if (!result.has(inst.course_code)) result.set(inst.course_code, { course, relations: [] });
                const staff = staffMap.get(inst.staff_number);
                result.get(inst.course_code)?.relations.push({ ...inst, staff_name: staff ? `${staff.first_name} ${staff.last_name}` : 'Unknown' });
            });
        }
        
        const lowercasedSearchTerm = searchTerm.toLowerCase();
        const filteredResult = Array.from(result.values()).filter(({ course, relations }) => {
            if (!searchTerm) return true;
            if (course.code.toLowerCase().includes(lowercasedSearchTerm) || course.title.toLowerCase().includes(lowercasedSearchTerm)) {
                return true;
            }
            return relations.some(rel => Object.values(rel).some(val => String(val).toLowerCase().includes(lowercasedSearchTerm)));
        });

        return { groupedData: filteredResult, columns: relationColumns, childEntityName: name };
    }, [allData, entityType, searchTerm]);

    const handleCreate = (courseCode: string) => {
        const newRecordTemplate = primaryKeys.reduce((acc, pk) => ({ ...acc, [pk]: pk === 'course_code' ? courseCode : '' }), {});
        setSelectedRecord(newRecordTemplate as StagingRecord);
        setIsEditing(false);
        setIsFormOpen(true);
    };
    const handleEdit = (record: StagingRecord) => { setSelectedRecord(record); setIsEditing(true); setIsFormOpen(true); };
    const handleDelete = (record: StagingRecord) => { setSelectedRecord(record); setIsDeleteDialogOpen(true); };

    const handleConfirmDelete = async () => {
        if (selectedRecord) {
            const pks = primaryKeys.map(pk => selectedRecord[pk]);
            await deleteRecord(pks);
            setIsDeleteDialogOpen(false);
            setSelectedRecord(null);
        }
    };
    const handleSave = async (formData: StagingRecord) => {
        if (isEditing && selectedRecord) {
            const oldPks = primaryKeys.map(pk => selectedRecord[pk]);
            await updateRecord(oldPks, formData);
        } else {
            await addRecord(formData);
        }
        setIsFormOpen(false);
        setSelectedRecord(null);
    };

    const formColumns = useMemo(() => {
        if (!allData || !allData[entityType]?.[0]) return [];
        const allKeys = Object.keys(allData[entityType][0] || {});
        return allKeys.filter(c => c.toLowerCase() !== 'id' && !c.toLowerCase().endsWith('_id') && !c.toLowerCase().endsWith('_at'));
    }, [allData, entityType]);

    return (
        <div className="mt-4">
            {groupedData.length === 0 ? (
                <div className="flex justify-center items-center h-64 flex-col border-2 border-dashed rounded-lg">
                    <Database className="h-8 w-8 text-muted-foreground mb-2"/><p className="text-muted-foreground">No matching data found for {formatHeader(entityType)}.</p>
                </div>
            ) : (
                <Accordion type="single" collapsible className="w-full">
                    {groupedData.map(({ course, relations }) => (
                        <AccordionItem value={course.code} key={course.code}>
                            <AccordionTrigger>
                                <div className="flex items-center justify-between w-full pr-4">
                                    <div className="flex flex-col items-start text-left">
                                        <span className="font-semibold">{course.code} - {course.title}</span>
                                        <span className="text-sm text-muted-foreground">{course.course_level} Level, {course.semester === 1 ? '1st' : '2nd'} Semester</span>
                                    </div>
                                    <Badge variant="secondary">{relations.length} {childEntityName}{relations.length !== 1 && 's'}</Badge>
                                </div>
                            </AccordionTrigger>
                            <AccordionContent>
                                <div className="p-2 bg-muted/50 rounded-md">
                                    <div className="flex justify-end mb-2">
                                        <Button size="sm" onClick={() => handleCreate(course.code)}><PlusCircle className="h-4 w-4 mr-2" />Add {childEntityName}</Button>
                                    </div>
                                    <div className="overflow-auto border rounded-lg">
                                      <Table>
                                          <TableHeader><TableRow>{columns.map(c => <TableHead key={c}>{formatHeader(c)}</TableHead>)}<TableHead>Actions</TableHead></TableRow></TableHeader>
                                          <TableBody>
                                              {relations.map((rel, idx) => (
                                                  <TableRow key={idx}>
                                                      {columns.map(col => <TableCell key={col}>{rel[col]}</TableCell>)}
                                                      <TableCell><div className="flex items-center space-x-2">
                                                          <Button variant="outline" size="icon" onClick={() => handleEdit(rel)}><Pencil className="h-4 w-4" /></Button>
                                                          <Button variant="destructive" size="icon" onClick={() => handleDelete(rel)}><Trash2 className="h-4 w-4" /></Button>
                                                      </div></TableCell>
                                                  </TableRow>
                                              ))}
                                          </TableBody>
                                      </Table>
                                    </div>
                                </div>
                            </AccordionContent>
                        </AccordionItem>
                    ))}
                </Accordion>
            )}

            <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}><DialogContent className="max-w-3xl">
                <DialogHeader><DialogTitle>{isEditing ? `Edit ${childEntityName}` : `Add ${childEntityName}`}</DialogTitle></DialogHeader>
                {selectedRecord && <StagingDataForm record={selectedRecord} entityType={entityType} columns={formColumns} primaryKeys={primaryKeys} allData={allData} onSave={handleSave} onCancel={() => setIsFormOpen(false)} isEditing={isEditing} />}
            </DialogContent></Dialog>
      
            <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}><AlertDialogContent>
                <AlertDialogHeader><AlertDialogTitle>Are you sure?</AlertDialogTitle><AlertDialogDescription>This will permanently remove this relationship.</AlertDialogDescription></AlertDialogHeader>
                <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={handleConfirmDelete}>Continue</AlertDialogAction></AlertDialogFooter>
            </AlertDialogContent></AlertDialog>
        </div>
    );
};

// --- Main Component ---
export function StagingDataReviewTable({ sessionId, uploadedEntityTypes }: { sessionId: string | null; uploadedEntityTypes: string[]; }) {
  const { data: allData, isLoading, error, refetch } = useAllStagedData(sessionId);
  const [activeTab, setActiveTab] = useState(uploadedEntityTypes[0] || '');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (uploadedEntityTypes.length > 0 && !uploadedEntityTypes.includes(activeTab)) {
      setActiveTab(uploadedEntityTypes[0]);
    }
  }, [uploadedEntityTypes, activeTab]);

  const filteredData = useMemo(() => {
    if (!allData || !activeTab || !allData[activeTab]) return [];
    if (!searchTerm) return allData[activeTab];
    const lowercasedSearchTerm = searchTerm.toLowerCase();
    return allData[activeTab].filter((record: StagingRecord) => 
      Object.values(record).some(value => 
        String(value).toLowerCase().includes(lowercasedSearchTerm)
      )
    );
  }, [allData, activeTab, searchTerm]);

  if (!sessionId) return <Alert variant="destructive"><AlertDescription>A session ID is required to review data.</AlertDescription></Alert>;
  if (isLoading) return <div className="flex justify-center items-center h-64"><Loader2 className="h-8 w-8 animate-spin text-primary" /><p className="ml-2">Loading Staged Data...</p></div>;
  if (error) return <Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertDescription>{error.message}</AlertDescription></Alert>;
  if (!allData || uploadedEntityTypes.length === 0) {
    return (
       <div className="py-8 text-center border-2 border-dashed rounded-lg">
          <Database className="h-8 w-8 mx-auto text-muted-foreground mb-2"/>
          <p className="font-medium">Staging Data Review Table</p>
          <p className="text-sm text-muted-foreground">Upload files in the previous step to review them here.</p>
       </div>
    );
  }

  return (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
      <TabsList className="flex-wrap h-auto">
        {uploadedEntityTypes.map(entityType => (
          <TabsTrigger key={entityType} value={entityType}>{formatHeader(entityType)}</TabsTrigger>
        ))}
      </TabsList>

      <div className="relative my-4">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          type="search"
          placeholder={`Search ${formatHeader(activeTab)}...`}
          className="w-full rounded-lg bg-background pl-8"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {uploadedEntityTypes.map(entityType => (
        <TabsContent key={entityType} value={entityType}>
          {GROUPED_ENTITIES.includes(entityType) ? (
            <GroupedDataViewer entityType={entityType} sessionId={sessionId} allData={allData} searchTerm={searchTerm} onRefetch={refetch} />
          ) : (
            <FlatDataViewer entityType={entityType} data={filteredData} sessionId={sessionId} allData={allData} onRefetch={refetch} />
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}