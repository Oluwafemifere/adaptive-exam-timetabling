import React from 'react';
import { Page, Text, View, Document, StyleSheet, Font } from '@react-pdf/renderer';
import { RenderableExam } from '../store/types';

// Register fonts (optional but recommended for better rendering)
Font.register({
  family: 'Helvetica',
  fonts: [
    { src: 'https://cdn.jsdelivr.net/npm/@canvas-fonts/helvetica@1.0.4/Helvetica.ttf' },
    { src: 'https://cdn.jsdelivr.net/npm/@canvas-fonts/helvetica@1.0.4/Helvetica-Bold.ttf', fontWeight: 'bold' },
  ],
});

// Constants for grid calculation
const START_HOUR = 8; // 8:00 AM
const END_HOUR = 18;  // 6:00 PM
const TOTAL_HOURS = END_HOUR - START_HOUR;
const ROW_HEIGHT = 50; // Height of one visual row of exams
const SIDEBAR_WIDTH = 60;
const HEADER_HEIGHT = 30;

// Department Colors Mapping
const DEPT_COLORS: Record<string, string> = {
  BIO: '#F0F4C3', // Light Green
  CSC: '#FFCDD2', // Light Red
  ECO: '#FFE0B2', // Light Orange
  ACC: '#FFAB91', // Salmon
  MCS: '#E1BEE7', // Light Purple
  PL:  '#C5CAE9', // Light Indigo
  PHY: '#B2DFDB', // Light Teal
  BUS: '#FFECB3', // Light Amber
  STA: '#DCEDC8', // Pale Green
  BOT: '#F8BBD0', // Pink
  DEFAULT: '#E0E0E0', // Grey
};

const getDepartmentColor = (courseCode: string): string => {
  // Extract prefix (e.g., "BIO" from "BIO101" or "BZ-BIO" from "BZ-BIO101")
  const match = courseCode.match(/([A-Z]+)(?=\d)/);
  const prefix = match ? match[0] : 'DEFAULT';
  
  // Handle cases like BAZ-BIO where BIO is the distinct part, or just take the prefix
  const key = Object.keys(DEPT_COLORS).find(k => prefix.includes(k)) || 'DEFAULT';
  return DEPT_COLORS[key];
};

const styles = StyleSheet.create({
  page: {
    padding: 20,
    fontFamily: 'Helvetica',
    fontSize: 8,
    backgroundColor: '#ffffff',
    flexDirection: 'column',
  },
  mainTitle: {
    fontSize: 18,
    fontFamily: 'Helvetica-Bold',
    textAlign: 'center',
    marginBottom: 15,
  },
  tableContainer: {
    display: 'flex',
    flexDirection: 'column',
    borderTop: '1px solid #cccccc',
    borderLeft: '1px solid #cccccc',
  },
  // Header Row
  headerRow: {
    display: 'flex',
    flexDirection: 'row',
    height: HEADER_HEIGHT,
    backgroundColor: '#f3f4f6',
  },
  headerCorner: {
    width: SIDEBAR_WIDTH,
    borderRight: '1px solid #cccccc',
    borderBottom: '1px solid #cccccc',
  },
  timeHeaderContainer: {
    flex: 1,
    display: 'flex',
    flexDirection: 'row',
    position: 'relative',
  },
  timeLabel: {
    position: 'absolute',
    top: 8,
    textAlign: 'center',
    width: 40, // Width of label text area
    marginLeft: -20, // Center over grid line
    fontSize: 9,
    color: '#555',
  },
  gridLineVertical: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 1,
    backgroundColor: '#e0e0e0',
  },
  // Date Row
  dateRowContainer: {
    display: 'flex',
    flexDirection: 'row',
    borderBottom: '1px solid #cccccc',
  },
  dateSidebar: {
    width: SIDEBAR_WIDTH,
    borderRight: '1px solid #cccccc',
    padding: 5,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fafafa',
  },
  dateText: {
    fontFamily: 'Helvetica-Bold',
    fontSize: 9,
    textAlign: 'center',
  },
  timelineContainer: {
    flex: 1,
    position: 'relative', // Needed for absolute positioning of exams
    display: 'flex',
  },
  // Exam Block
  examBlock: {
    position: 'absolute',
    padding: 4,
    borderLeft: '3px solid rgba(0,0,0,0.1)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
  },
  courseCode: {
    fontFamily: 'Helvetica-Bold',
    fontSize: 9,
    color: '#333',
  },
  courseTitle: {
    fontSize: 7,
    color: '#555',
    textOverflow: 'ellipsis',
    maxLines: 1,
    marginTop: 1,
  },
  timeText: {
    fontSize: 7,
    color: '#666',
    marginTop: 2,
  }
});

// Helper: Time string "HH:MM" to minutes from midnight
const timeToMinutes = (time: string): number => {
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
};

// Helper: Calculate position and width percentages
const getPosition = (startTime: string, endTime: string) => {
  const startMinutes = timeToMinutes(startTime);
  const endMinutes = timeToMinutes(endTime);
  const dayStartMinutes = START_HOUR * 60;
  const totalDayMinutes = TOTAL_HOURS * 60;

  const left = ((startMinutes - dayStartMinutes) / totalDayMinutes) * 100;
  const width = ((endMinutes - startMinutes) / totalDayMinutes) * 100;

  return { left: `${left}%`, width: `${width}%` };
};

// Helper: Format date
const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return {
    day: date.toLocaleDateString('en-US', { weekday: 'short' }),
    date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  };
};

// Algorithm to stack exams vertically if they overlap in time on the same day
interface VisualRow {
  endTime: number;
  exams: (RenderableExam & { posConfig: any })[];
}

const packExamsIntoRows = (exams: RenderableExam[]) => {
  // Sort by start time, then longest duration
  const sorted = [...exams].sort((a, b) => {
    const startA = timeToMinutes(a.startTime);
    const startB = timeToMinutes(b.startTime);
    if (startA !== startB) return startA - startB;
    return timeToMinutes(b.endTime) - timeToMinutes(a.endTime);
  });

  const rows: VisualRow[] = [];

  sorted.forEach(exam => {
    const examStart = timeToMinutes(exam.startTime);
    const examEnd = timeToMinutes(exam.endTime);
    const posConfig = {
      ...getPosition(exam.startTime, exam.endTime),
      color: getDepartmentColor(exam.courseCode)
    };

    // Try to fit into an existing row
    let placed = false;
    for (let i = 0; i < rows.length; i++) {
      if (rows[i].endTime <= examStart) {
        rows[i].exams.push({ ...exam, posConfig });
        rows[i].endTime = examEnd;
        placed = true;
        break;
      }
    }

    // If not placed, create a new row
    if (!placed) {
      rows.push({
        endTime: examEnd,
        exams: [{ ...exam, posConfig }]
      });
    }
  });

  return rows;
};

interface TimetablePDFProps {
  exams: RenderableExam[];
  title?: string;
}

export const TimetablePDFDocument: React.FC<TimetablePDFProps> = ({ 
  exams, 
  title = "Examination Timetable" 
}) => {
  // Group exams by date
  const examsByDate: Record<string, RenderableExam[]> = {};
  exams.forEach(exam => {
    if (!examsByDate[exam.date]) examsByDate[exam.date] = [];
    examsByDate[exam.date].push(exam);
  });

  const sortedDates = Object.keys(examsByDate).sort();
  const timeHours = Array.from({ length: TOTAL_HOURS }, (_, i) => START_HOUR + i);

  return (
    <Document>
      <Page size="A3" orientation="landscape" style={styles.page}>
        <Text style={styles.mainTitle}>{title}</Text>

        <View style={styles.tableContainer}>
          {/* Header Row (Times) */}
          <View style={styles.headerRow}>
            <View style={styles.headerCorner} />
            <View style={styles.timeHeaderContainer}>
              {timeHours.map((hour) => {
                const leftPct = ((hour - START_HOUR) / TOTAL_HOURS) * 100;
                return (
                  <React.Fragment key={hour}>
                    {/* Grid line */}
                    <View style={[styles.gridLineVertical, { left: `${leftPct}%`, borderRight: '1px solid #cccccc' }]} />
                    {/* Time Label */}
                    <Text style={[styles.timeLabel, { left: `${leftPct}%` }]}>
                      {`${hour}:00`}
                    </Text>
                  </React.Fragment>
                );
              })}
              {/* Final closing line for the grid */}
              <View style={[styles.gridLineVertical, { left: '100%', borderRight: '1px solid #cccccc' }]} />
              <Text style={[styles.timeLabel, { left: '100%' }]}>{`${END_HOUR}:00`}</Text>
            </View>
          </View>

          {/* Date Rows */}
          {sortedDates.map((date) => {
            const visualRows = packExamsIntoRows(examsByDate[date]);
            const totalRowHeight = Math.max(visualRows.length * ROW_HEIGHT, ROW_HEIGHT);
            const fmtDate = formatDate(date);

            return (
              <View key={date} style={[styles.dateRowContainer, { height: totalRowHeight }]}>
                {/* Sidebar with Date */}
                <View style={styles.dateSidebar}>
                  <Text style={styles.dateText}>{fmtDate.day}</Text>
                  <Text style={{ fontSize: 8, color: '#666' }}>{fmtDate.date}</Text>
                </View>

                {/* Timeline Area */}
                <View style={styles.timelineContainer}>
                  {/* Background Grid Lines for this row */}
                  {timeHours.map((hour) => (
                    <View 
                      key={`grid-${hour}`} 
                      style={[
                        styles.gridLineVertical, 
                        { left: `${((hour - START_HOUR) / TOTAL_HOURS) * 100}%` }
                      ]} 
                    />
                  ))}
                  <View style={[styles.gridLineVertical, { left: '100%', borderRight: '1px solid #e0e0e0' }]} />

                  {/* Render Exams */}
                  {visualRows.map((row, rowIndex) => (
                    <React.Fragment key={rowIndex}>
                      {row.exams.map((exam) => (
                        <View
                          key={exam.id}
                          style={[
                            styles.examBlock,
                            {
                              left: exam.posConfig.left,
                              width: exam.posConfig.width,
                              backgroundColor: exam.posConfig.color,
                              top: rowIndex * ROW_HEIGHT,
                              height: ROW_HEIGHT - 2, // -2 for little gap
                              // Ensure it doesn't overflow horizontally due to math rounding
                              maxWidth: exam.posConfig.width, 
                            }
                          ]}
                        >
                          <Text style={styles.courseCode}>{exam.courseCode}</Text>
                          <Text style={styles.courseTitle}>{exam.courseName}</Text>
                          <Text style={styles.timeText}>
                            {exam.startTime} - {exam.endTime}
                          </Text>
                        </View>
                      ))}
                      {/* Line separator between visual rows if multiple exist */}
                      {rowIndex < visualRows.length - 1 && (
                        <View style={{
                          position: 'absolute',
                          left: 0, right: 0,
                          top: (rowIndex + 1) * ROW_HEIGHT,
                          height: 1,
                          backgroundColor: '#eee',
                          borderBottomStyle: 'dashed'
                        }} />
                      )}
                    </React.Fragment>
                  ))}
                </View>
              </View>
            );
          })}
        </View>
      </Page>
    </Document>
  );
};