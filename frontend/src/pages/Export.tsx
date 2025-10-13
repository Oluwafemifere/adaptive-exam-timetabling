import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Download, Loader2, FileText, Building } from 'lucide-react';
import { useAppStore } from '../store';
import { PDFDownloadLink } from '@react-pdf/renderer';
import { TimetablePDFDocument } from '../components/TimetablePDF';

export function Export() {
  const { exams } = useAppStore();
  const [selectedDepartment, setSelectedDepartment] = useState<string>('');
  const [selectedFaculty, setSelectedFaculty] = useState<string>('');
  
  const { departments, faculties } = useMemo(() => {
    const deptSet = new Set<string>();
    const facultySet = new Set<string>();
    exams.forEach(exam => {
      exam.departments.forEach(dept => deptSet.add(dept));
      if (exam.facultyName) facultySet.add(exam.facultyName);
    });
    return {
      departments: Array.from(deptSet).sort(),
      faculties: Array.from(facultySet).sort(),
    };
  }, [exams]);

  const filteredByDepartmentExams = useMemo(() => {
    if (!selectedDepartment) return [];
    return exams.filter(exam => exam.departments.includes(selectedDepartment));
  }, [exams, selectedDepartment]);

  const filteredByFacultyExams = useMemo(() => {
    if (!selectedFaculty) return [];
    return exams.filter(exam => exam.facultyName === selectedFaculty);
  }, [exams, selectedFaculty]);
  
  const DownloadButton = ({ loading }: { loading: boolean }) => (
    <Button disabled={loading} className="w-full sm:w-auto">
      {loading ? (
        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
      ) : (
        <Download className="h-4 w-4 mr-2" />
      )}
      {loading ? 'Generating PDF...' : 'Download PDF'}
    </Button>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Export Timetables</h1>
          <p className="text-muted-foreground">Download timetables in PDF format for offline use and distribution.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FileText className="h-5 w-5"/>Complete Timetable</CardTitle>
          <CardDescription>Download the full exam schedule for the current active session.</CardDescription>
        </CardHeader>
        <CardContent>
          <PDFDownloadLink
            document={<TimetablePDFDocument exams={exams} title="Full Exam Timetable" />}
            fileName={`full-timetable-${new Date().toISOString().split('T')[0]}.pdf`}
          >
           {({ loading }) => <DownloadButton loading={loading} />}
          </PDFDownloadLink>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Building className="h-5 w-5"/>Department Timetable</CardTitle>
            <CardDescription>Download the schedule for a specific department.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="department-select">Select Department</Label>
              <Select value={selectedDepartment} onValueChange={setSelectedDepartment}>
                <SelectTrigger id="department-select"><SelectValue placeholder="Choose a department..." /></SelectTrigger>
                <SelectContent>
                  {departments.map(dept => <SelectItem key={dept} value={dept}>{dept}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {selectedDepartment && (
               <PDFDownloadLink
                document={
                  <TimetablePDFDocument 
                    exams={filteredByDepartmentExams} 
                    title={`Exam Timetable for ${selectedDepartment}`}
                  />
                }
                fileName={`${selectedDepartment.replace(/\s+/g, '_')}-timetable-${new Date().toISOString().split('T')[0]}.pdf`}
              >
                {({ loading }) => <DownloadButton loading={loading} />}
              </PDFDownloadLink>
            )}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Building className="h-5 w-5"/>Faculty Timetable</CardTitle>
            <CardDescription>Download the schedule for a specific faculty.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="faculty-select">Select Faculty</Label>
              <Select value={selectedFaculty} onValueChange={setSelectedFaculty}>
                <SelectTrigger id="faculty-select"><SelectValue placeholder="Choose a faculty..." /></SelectTrigger>
                <SelectContent>
                  {faculties.map(faculty => <SelectItem key={faculty} value={faculty}>{faculty}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {selectedFaculty && (
              <PDFDownloadLink
                document={
                  <TimetablePDFDocument 
                    exams={filteredByFacultyExams} 
                    title={`Exam Timetable for ${selectedFaculty}`}
                  />
                }
                fileName={`${selectedFaculty.replace(/\s+/g, '_')}-timetable-${new Date().toISOString().split('T')[0]}.pdf`}
              >
                {({ loading }) => <DownloadButton loading={loading} />}
              </PDFDownloadLink>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}