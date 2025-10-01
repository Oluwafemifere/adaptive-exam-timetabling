# Comprehensive Exam Timetabling System Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [User Roles & Authentication](#user-roles--authentication)
4. [Data Structures & Types](#data-structures--types)
5. [System Navigation & Routing](#system-navigation--routing)
6. [Administrator Portal](#administrator-portal)
7. [Student Portal](#student-portal)
8. [Staff Portal](#staff-portal)
9. [Core Components](#core-components)
10. [State Management](#state-management)
11. [API Architecture & Stubbed Functionality](#api-architecture--stubbed-functionality)
12. [Scheduling Engine](#scheduling-engine)
13. [Conflict Management](#conflict-management)
14. [User Interface Components](#user-interface-components)
15. [Utilities & Helpers](#utilities--helpers)
16. [Configuration](#configuration)
17. [Theme System](#theme-system)
18. [Flow Diagrams](#flow-diagrams)
19. [Feature Completeness Status](#feature-completeness-status)
20. [Future Development Roadmap](#future-development-roadmap)

---

## System Overview

The **Exam Timetabling System** is a comprehensive, multi-user web application designed to manage and automate the scheduling of academic examinations. Built with React, TypeScript, and Tailwind CSS, it provides role-based access control for three distinct user types: Students, Staff, and Administrators.

### Key Capabilities
- **Multi-role access control** with distinct interfaces for different user types
- **Advanced timetable grid visualization** with drag-and-drop functionality
- **Sophisticated conflict detection and resolution** with automatic and manual options
- **AI-powered scheduling jobs** using CP-SAT and genetic algorithms
- **Real-time notifications and updates** via WebSocket-like functionality
- **Comprehensive audit trails and history tracking**
- **Export capabilities** for various formats
- **Mobile-responsive design** with optimized layouts
- **Advanced filtering and search** across all data types
- **Analytics and reporting dashboard** with KPIs and visualizations

---

## Architecture & Technology Stack

### Frontend Technologies
- **React 18** with functional components and hooks
- **TypeScript** for type safety and developer experience
- **Tailwind CSS v4** for styling with custom design system
- **Zustand** for global state management
- **Recharts** for data visualization and analytics
- **Lucide React** for consistent iconography
- **Shadcn/ui** component library for UI consistency
- **Sonner** for toast notifications
- **React Hook Form** for form management
- **Motion/React** (Framer Motion) for animations

### Architecture Patterns
- **Component-based architecture** with reusable UI components
- **State management pattern** using Zustand store
- **Role-based access control (RBAC)** for security
- **Separation of concerns** with dedicated service layers
- **Responsive design pattern** for multi-device support
- **Event-driven architecture** for real-time updates

### File Structure
```
├── App.tsx                 # Main application entry point
├── components/             # Reusable UI components
│   ├── ui/                # Shadcn/ui component library
│   └── [Core Components]  # Application-specific components
├── pages/                 # Route-based page components
├── store/                 # Zustand state management
├── hooks/                 # Custom React hooks
├── services/              # API service layer
├── utils/                 # Utility functions
├── data/                  # Mock data and types
├── config/                # Configuration files
└── styles/                # Global CSS and theme definitions
```

---

## User Roles & Authentication

### Authentication System
The system implements a role-based authentication mechanism with three distinct user roles:

#### Demo Credentials
- **Administrator**: `admin@baze.edu` / `demo`
- **Staff**: `staff@baze.edu` / `demo`
- **Student**: `student@baze.edu` / `demo`

#### Authentication Flow
1. **Login Page**: Users enter credentials with role-specific quick login buttons
2. **Credential Validation**: Handled by `useAuth` hook with mock API integration
3. **Role-based Routing**: Automatic redirection to appropriate portal based on user role
4. **Session Management**: Persistent login state with logout functionality
5. **Security**: Protected routes prevent unauthorized access

#### User Data Structure
```typescript
interface User {
  id: string;
  name: string;
  email: string;
  role: 'student' | 'staff' | 'administrator';
  department?: string;
  studentId?: string; // For students only
  staffId?: string;   // For staff only
}
```

---

## Data Structures & Types

### Core Exam Entity
```typescript
interface Exam {
  id: string;
  courseCode: string;        // e.g., "CS101"
  courseName: string;        // e.g., "Introduction to Computer Science"
  date: string;             // ISO date format
  startTime: string;        // 24-hour format "HH:MM"
  endTime: string;          // 24-hour format "HH:MM"
  duration: number;         // Duration in minutes
  expectedStudents: number; // Expected enrollment
  room: string;             // Room identifier
  roomCapacity: number;     // Maximum room capacity
  building: string;         // Building name
  invigilator: string;      // Assigned invigilator
  departments: string[];    // Associated departments
  level: string;            // Academic level (100, 200, 300, 400)
  semester: string;         // Semester identifier
  academicYear: string;     // Academic year
}
```

### Conflict Management
```typescript
interface Conflict {
  id: string;
  type: 'hard' | 'soft';           // Constraint violation severity
  severity: 'high' | 'medium' | 'low'; // Priority level
  message: string;                  // Human-readable description
  examIds: string[];               // Affected exam IDs
  autoResolvable: boolean;         // Can be auto-resolved
}
```

### Scheduling Job Management
```typescript
interface SchedulingStatus {
  isRunning: boolean;
  phase: 'cp-sat' | 'genetic-algorithm' | 'completed' | 'failed' | 'cancelled' | 'idle';
  progress: number;              // 0-100 percentage
  jobId: string | null;
  startTime?: string;
  estimatedEndTime?: string;
  canPause: boolean;
  canResume: boolean;
  canCancel: boolean;
  metrics: {
    hard_constraints_violations?: number;
    soft_constraints_violations?: number;
    fitness_score?: number;
    generation?: number;
    error_message?: string;
    processed_exams?: number;
    total_exams?: number;
  };
}
```

### Student-specific Data
```typescript
interface StudentExam {
  id: string;
  courseCode: string;
  courseName: string;
  date: string;
  startTime: string;
  endTime: string;
  room: string;
  building: string;
  duration: number;
}

interface ConflictReport {
  id: string;
  studentId: string;
  examId: string;
  courseCode: string;
  description: string;
  status: 'pending' | 'reviewed' | 'resolved';
  submittedAt: string;
}
```

### Staff-specific Data
```typescript
interface StaffAssignment {
  id: string;
  examId: string;
  courseCode: string;
  courseName: string;
  date: string;
  startTime: string;
  endTime: string;
  room: string;
  building: string;
  role: 'instructor' | 'invigilator' | 'lead-invigilator';
  status: 'assigned' | 'change-requested' | 'confirmed';
}

interface ChangeRequest {
  id: string;
  staffId: string;
  assignmentId: string;
  courseCode: string;
  reason: string;
  description?: string;
  status: 'pending' | 'approved' | 'denied';
  submittedAt: string;
  reviewedAt?: string;
  reviewedBy?: string;
  reviewNotes?: string;
}
```

---

## System Navigation & Routing

### Route Management
The application uses a custom routing system based on the `currentPage` state variable rather than traditional React Router. This allows for fine-grained control over navigation and role-based access.

#### Administrator Routes
- `'dashboard'` → Dashboard with KPIs and system overview
- `'scheduling'` → Scheduling jobs and timetable generation
- `'timetable'` → Interactive timetable grid with editing capabilities
- `'constraints'` → Constraint configuration and management
- `'scenarios'` → Scenario comparison and what-if analysis
- `'analytics'` → Analytics dashboard with reports and visualizations
- `'session-setup'` → Academic session configuration
- `'user-management'` → User account and role management
- `'notifications'` → System notifications and alerts center
- `'history'` → Audit trail and change history

#### Navigation Components
- **Sidebar Navigation**: Collapsible sidebar with tooltips and keyboard shortcuts
- **Breadcrumb Navigation**: Context-aware breadcrumb trails
- **Quick Actions**: Floating action buttons for common operations
- **Global Search**: Cross-module search functionality
- **User Menu**: Profile, settings, and logout options

---

## Administrator Portal

### Dashboard (`/pages/Dashboard.tsx`)
The central command center for system administrators with comprehensive KPIs and system health monitoring.

#### Key Performance Indicators (KPIs)
- **Total Exams Scheduled**: Count of scheduled examinations
- **Hard Constraint Violations**: Critical conflicts requiring immediate attention
- **Soft Constraint Violations**: Non-critical optimization opportunities
- **Room Utilization**: Percentage of available room capacity being used
- **System Status**: Real-time constraint engine and sync status
- **Recent Activity Feed**: Live updates of system changes

#### Dashboard Features
- **Real-time Status Updates**: Live system health monitoring
- **Quick Action Buttons**: Direct access to common operations
- **Conflict Hotspot Visualization**: Identify problematic time slots and dates
- **Bottleneck Analysis**: Identify over-allocated resources
- **Trend Analytics**: Historical performance tracking
- **Notification Center Integration**: Unread alerts and action items

#### Mock Data Integration
The dashboard displays both real-time data from the Zustand store and mock data for demonstration purposes, including:
- Conflict hotspots by day and time
- Resource bottlenecks and allocation issues
- Scheduling job history and performance metrics

### Scheduling Page (`/pages/Scheduling.tsx`)
Advanced scheduling job management with real-time progress tracking and control capabilities.

#### Scheduling Engine Integration
- **Job Creation**: Configure and launch new scheduling jobs
- **Algorithm Selection**: Choose between CP-SAT and genetic algorithm approaches
- **Real-time Progress**: Live updates via WebSocket-like functionality
- **Job Control**: Pause, resume, and cancel running jobs
- **Result Comparison**: Compare multiple scheduling results
- **Export Options**: Download results in various formats

#### Job Management Features
- **Job Queue**: View pending and running jobs
- **Progress Tracking**: Detailed metrics and phase information
- **Error Handling**: Graceful error recovery and reporting
- **Performance Metrics**: Fitness scores, constraint violations, and optimization statistics
- **Historical Results**: Archive of previous scheduling runs

#### Stubbed Functionality
- **WebSocket Integration**: Real-time job updates (currently simulated)
- **Advanced Algorithm Parameters**: Detailed configuration options
- **Distributed Processing**: Multi-node job execution
- **Custom Constraint Weights**: Fine-tuning optimization parameters

### Timetable Page (`/pages/Timetable.tsx`)
Interactive timetable visualization with advanced editing and conflict management capabilities.

#### Grid Functionality
- **Drag-and-Drop**: Move exams between time slots and dates
- **Visual Conflict Detection**: Color-coded conflict indicators
- **Multi-view Support**: General overview and department-specific views
- **Dynamic Row Heights**: Accommodate varying exam durations
- **Responsive Layout**: Optimized for different screen sizes

#### Editing Capabilities
- **In-place Editing**: Direct modification of exam details
- **Bulk Operations**: Multi-select for batch changes
- **Conflict Resolution**: Auto-suggest alternatives for conflicted exams
- **Version Control**: Track changes with rollback capabilities
- **Validation**: Real-time constraint checking during edits

#### View Modes
- **General View**: All exams with department color coding
- **Department View**: Filtered view for specific departments
- **Room View**: Focus on specific rooms and their utilization
- **Instructor View**: Show assignments for specific staff members

### Constraints Page (`/pages/Constraints.tsx`)
Comprehensive constraint configuration and management system.

#### Constraint Types
- **Hard Constraints**: Must be satisfied (no exam overlaps, room capacity)
- **Soft Constraints**: Optimization preferences (instructor availability, student preferences)
- **Custom Constraints**: User-defined business rules
- **Temporal Constraints**: Time-based restrictions and preferences

#### Configuration Interface
- **Visual Constraint Builder**: Drag-and-drop constraint creation
- **Weight Management**: Priority adjustment for soft constraints
- **Validation Rules**: Constraint consistency checking
- **Import/Export**: Share constraint configurations
- **Templates**: Pre-defined constraint sets for common scenarios

### Scenarios Page (`/pages/Scenarios.tsx`)
What-if analysis and scenario comparison capabilities.

#### Scenario Management
- **Scenario Creation**: Generate alternative scheduling solutions
- **Comparison Tools**: Side-by-side analysis of different outcomes
- **Impact Analysis**: Understand the effects of constraint changes
- **Decision Support**: Recommendations based on scenario analysis

### Analytics Page (`/pages/Analytics.tsx`)
Comprehensive reporting and analytics dashboard.

#### Report Types
- **Utilization Reports**: Room and time slot usage statistics
- **Conflict Analysis**: Detailed breakdown of constraint violations
- **Performance Metrics**: System efficiency and optimization results
- **Trend Analysis**: Historical data and patterns
- **Custom Reports**: User-defined analytics queries

#### Visualization Components
- **Interactive Charts**: Recharts-based visualizations
- **Heat Maps**: Identify high-conflict periods and locations
- **Gantt Charts**: Timeline-based exam scheduling views
- **Statistical Dashboards**: KPI tracking and monitoring

### Session Setup Page (`/pages/SessionSetup.tsx`)
Academic session configuration and management.

#### Session Management
- **Session Creation**: Define new academic periods
- **Calendar Integration**: Academic calendar alignment
- **Holiday Management**: Exclude non-examination days
- **Template Application**: Apply previous session configurations

### User Management Page (`/pages/UserManagement.tsx`)
Comprehensive user account and role management system.

#### User Administration
- **Account Creation**: Add new system users
- **Role Assignment**: Configure user permissions and access levels
- **Bulk Operations**: Import/export user data
- **Access Control**: Fine-grained permission management

### Notifications Page (`/pages/Notifications.tsx`)
Centralized notification and alert management system.

#### Notification Types
- **Conflict Reports**: Student-submitted exam conflicts
- **Change Requests**: Staff assignment modification requests
- **System Alerts**: Automated system notifications
- **Job Completion**: Scheduling job status updates

#### Management Features
- **Priority Filtering**: Focus on urgent notifications
- **Batch Operations**: Mark multiple notifications as read
- **Response Actions**: Quick resolution of actionable items
- **Notification Settings**: Configure alert preferences

### History Page (`/pages/History.tsx`)
Comprehensive audit trail and change tracking system.

#### Audit Capabilities
- **Change Tracking**: Detailed before/after comparisons
- **User Attribution**: Track who made what changes
- **Timestamp Logging**: Complete chronological record
- **Entity Tracking**: Follow changes across different data types
- **Rollback Support**: Revert to previous states

---

## Student Portal

### Student Portal Overview (`/pages/StudentPortal.tsx`)
Dedicated interface for students to view their examination schedule and report conflicts.

#### Core Features
- **Personal Exam Schedule**: View all enrolled course examinations
- **Calendar Integration**: Visual calendar representation of exam dates
- **Conflict Reporting**: Submit conflicts with detailed descriptions
- **Schedule Export**: Download personal exam schedule
- **Notification Center**: Receive updates about schedule changes

#### Student Dashboard Components
- **Upcoming Exams Widget**: Next 5 upcoming examinations
- **Conflict Status Tracker**: Monitor submitted conflict reports
- **Quick Actions**: Common tasks like conflict reporting and schedule export
- **Academic Calendar View**: Monthly calendar with exam highlights

#### Exam Schedule Management
```typescript
// Student exam data structure
interface StudentExam {
  id: string;
  courseCode: string;      // "CS101"
  courseName: string;      // "Introduction to Computer Science"
  date: string;           // "2024-12-15"
  startTime: string;      // "09:00"
  endTime: string;        // "12:00"
  room: string;           // "A101"
  building: string;       // "Engineering Building"
  duration: number;       // 180 minutes
}
```

#### Conflict Reporting System
Students can report various types of conflicts:
- **Time Conflicts**: Overlapping exam schedules
- **Personal Conflicts**: Medical appointments, family emergencies
- **Academic Conflicts**: Course withdrawal, academic accommodation needs
- **Technical Issues**: Room accessibility, special requirements

#### Student Data Flow
1. **Authentication**: Student logs in with university credentials
2. **Data Retrieval**: System fetches enrolled courses and exam schedules
3. **Schedule Display**: Present exams in chronological order with visual calendar
4. **Conflict Submission**: Students submit conflict reports with detailed information
5. **Status Tracking**: Monitor resolution status of submitted conflicts
6. **Notifications**: Receive updates about schedule changes or conflict resolutions

### Student Portal Components
- **Exam List View**: Tabular display of all exams with filtering options
- **Calendar View**: Monthly/weekly calendar with exam blocks
- **Conflict Form**: Comprehensive form for reporting scheduling conflicts
- **Status Dashboard**: Track the status of submitted requests
- **Export Functions**: Download schedule in PDF, ICS, or CSV formats

---

## Staff Portal

### Staff Portal Overview (`/pages/StaffPortal.tsx`) 
Specialized interface for academic staff to manage their examination assignments and submit change requests.

#### Core Features
- **Assignment Dashboard**: View all invigilation and instruction assignments
- **Schedule Management**: Request changes to assigned examination slots
- **Availability Management**: Set availability preferences for future scheduling
- **Assignment History**: Track past and current examination assignments
- **Notification System**: Receive assignment updates and change confirmations

#### Staff Dashboard Components
- **Active Assignments**: Current semester examination duties
- **Pending Requests**: Status of submitted change requests
- **Upcoming Assignments**: Next 10 upcoming examination duties
- **Quick Actions**: Submit change requests, update availability, export schedule

#### Assignment Types
```typescript
interface StaffAssignment {
  id: string;
  examId: string;
  courseCode: string;
  courseName: string;
  date: string;
  startTime: string;
  endTime: string;
  room: string;
  building: string;
  role: 'instructor' | 'invigilator' | 'lead-invigilator';
  status: 'assigned' | 'change-requested' | 'confirmed';
}
```

#### Assignment Roles
- **Instructor**: Course instructor responsible for the examination
- **Invigilator**: Staff member supervising the examination
- **Lead Invigilator**: Senior staff member coordinating multiple invigilators

#### Change Request System
Staff can submit requests for assignment modifications:
- **Time Conflicts**: Request different time slots due to conflicts
- **Emergency Leave**: Submit urgent change requests for personal emergencies
- **Medical Accommodations**: Request assignment changes due to health issues
- **Academic Conflicts**: Research commitments, conference attendance
- **Availability Updates**: Change previously stated availability

#### Change Request Workflow
1. **Request Submission**: Staff submits detailed change request with justification
2. **Admin Review**: Administrator reviews request and assesses impact
3. **Alternative Assignment**: System suggests alternative staff assignments
4. **Approval/Denial**: Admin approves or denies with explanatory notes
5. **Notification**: Staff receives notification of decision
6. **Schedule Update**: Approved changes are reflected in the schedule

#### Staff Data Management
- **Personal Schedule**: Comprehensive view of all academic commitments
- **Preference Settings**: Set preferred time slots, rooms, and examination types
- **Historical Data**: Track assignment history and performance metrics
- **Communication Log**: Record of all interactions with administration

---

## Core Components

### TimetableGrid Component (`/components/TimetableGrid.tsx`)
The heart of the visual scheduling interface with sophisticated positioning and conflict detection.

#### Grid Architecture
- **Column-based Layout**: Time slots as columns, dates as major sections
- **Dynamic Row Heights**: Automatically adjust for exam duration
- **Collision Detection**: Prevent overlapping exam placements
- **Stack Management**: Handle multiple exams in the same time slot
- **Color Coding**: Department-based or exam-specific color schemes

#### Positioning Algorithm
```typescript
interface PositionedExam extends Exam {
  startColumn: number;    // Starting time slot column
  spanColumns: number;    // Number of time slots spanned
  stackLevel: number;     // Vertical stacking level for conflicts
  examIndex: number;      // Unique identifier for color assignment
}
```

The component implements a sophisticated positioning algorithm that:
1. **Calculates time slot spans** based on exam duration
2. **Detects temporal overlaps** between exams
3. **Assigns stack levels** to prevent visual conflicts
4. **Optimizes layout density** to minimize grid height

#### Drag and Drop Functionality
- **Drag Initiation**: Click and hold on exam blocks
- **Visual Feedback**: Highlight valid drop zones during drag
- **Snap to Grid**: Automatic alignment to time slot boundaries
- **Conflict Prevention**: Block invalid drops that would create conflicts
- **Undo/Redo**: Support for reverting drag operations

#### View Modes
- **General View**: All exams with department-based color coding
- **Department View**: Focus on specific departments with distinct colors for each exam
- **Resource View**: Highlight room and instructor utilization
- **Conflict View**: Emphasize areas with scheduling conflicts

### ExamBlock Component (`/components/ExamBlock.tsx`)
Individual exam representation within the timetable grid with rich interaction capabilities.

#### Visual Design
- **Responsive Layout**: Adapts to available space and screen size
- **Information Hierarchy**: Clear presentation of exam details
- **Status Indicators**: Visual cues for conflicts, assignments, and special requirements
- **Interactive Elements**: Hover states, selection indicators, and action buttons

#### Data Display
- **Primary Information**: Course code, name, and time
- **Secondary Details**: Room, instructor, student count
- **Contextual Metadata**: Department, building, special notes
- **Dynamic Styling**: Color coding based on view mode and conflict status

#### Interaction Capabilities
- **Hover Tooltips**: Detailed information on mouse hover
- **Click Actions**: Selection, editing, and context menu activation
- **Drag Handles**: Visual indicators for drag-and-drop operations
- **Keyboard Navigation**: Full accessibility support

### ExamBlockTooltip Component (`/components/ExamBlockTooltip.tsx`)
Rich tooltip component providing detailed exam information and quick actions.

#### Information Display
- **Complete Exam Details**: All relevant exam information
- **Conflict Indicators**: Visual warnings about scheduling conflicts
- **Resource Information**: Room capacity, building location, accessibility features
- **Historical Context**: Previous scheduling history and changes

#### Quick Actions
- **Edit Exam**: Direct access to exam editing interface
- **View Conflicts**: Detailed conflict analysis and resolution options
- **Reschedule**: Quick rescheduling with alternative suggestions
- **Export Details**: Single exam export in various formats

### ConflictPanel Component (`/components/ConflictPanel.tsx`)
Comprehensive conflict detection and resolution interface.

#### Conflict Detection
- **Real-time Analysis**: Continuous monitoring of scheduling conflicts
- **Severity Classification**: Automatic categorization of conflict types
- **Impact Assessment**: Analysis of conflict effects on overall scheduling
- **Resolution Suggestions**: AI-powered recommendations for conflict resolution

#### Resolution Tools
- **Automatic Resolution**: One-click fixes for simple conflicts
- **Manual Override**: Admin tools for complex conflict resolution
- **Alternative Suggestions**: Multiple options for conflict resolution
- **Impact Preview**: Show effects of proposed changes before implementation

#### Conflict Types
- **Hard Conflicts**: Must be resolved (room double-booking, instructor conflicts)
- **Soft Conflicts**: Optimization opportunities (student preferences, room preferences)
- **Resource Conflicts**: Over-allocation of rooms, equipment, or staff
- **Temporal Conflicts**: Time-based conflicts and constraints

### FilterControls Component (`/components/FilterControls.tsx`)
Advanced filtering interface with multi-select capabilities and preset management.

#### Filter Categories
- **Department Filters**: Multi-select department filtering
- **Faculty Filters**: Faculty-level filtering options
- **Room Filters**: Specific room and building filters
- **Date Range**: Flexible date range selection
- **Time Slot Filters**: Specific time period filtering
- **Status Filters**: Filter by exam status and conflict state

#### Preset Management
- **Saved Filters**: Store frequently used filter combinations
- **Quick Presets**: One-click access to common filter sets
- **Shared Presets**: Department-wide filter sharing
- **Filter History**: Recently used filter combinations

#### Advanced Features
- **Boolean Logic**: AND/OR combinations for complex filtering
- **Search Integration**: Text-based filtering within categories
- **Export Filters**: Save and share filter configurations
- **Performance Optimization**: Efficient filtering for large datasets

### GlobalSearch Component (`/components/GlobalSearch.tsx`)
Comprehensive search functionality across all system entities.

#### Search Capabilities
- **Cross-Entity Search**: Search across exams, rooms, instructors, and students
- **Intelligent Ranking**: Relevance-based result ordering
- **Real-time Suggestions**: Auto-complete and search suggestions
- **Advanced Queries**: Support for complex search patterns

#### Search Categories
- **Exam Search**: Course codes, names, instructors, rooms
- **People Search**: Students, staff, instructors by name or ID
- **Room Search**: Buildings, room numbers, capacity ranges
- **Time Search**: Date ranges, time slots, duration filters

#### Keyboard Shortcuts (`/components/KeyboardShortcuts.tsx`)
Comprehensive keyboard navigation and shortcut system.

#### Global Shortcuts
- **Ctrl+K**: Open global search
- **Ctrl+/**: Show keyboard shortcuts help
- **Ctrl+Shift+D**: Toggle dark/light theme
- **Esc**: Close active modals and panels

#### Navigation Shortcuts
- **G+D**: Go to Dashboard
- **G+S**: Go to Scheduling
- **G+T**: Go to Timetable  
- **G+C**: Go to Constraints
- **G+A**: Go to Analytics

#### Action Shortcuts
- **Ctrl+S**: Save current changes
- **Ctrl+Z**: Undo last action
- **Ctrl+Y**: Redo last undone action
- **Ctrl+F**: Focus filter controls

### Layout Component (`/components/Layout.tsx`)
Main application layout with navigation, header, and responsive design.

#### Navigation System
- **Sidebar Navigation**: Collapsible sidebar with role-based menu items
- **Breadcrumb Trail**: Context-aware navigation breadcrumbs
- **User Menu**: Profile, settings, and logout functionality
- **Notification Badge**: Real-time notification count display

#### Responsive Design
- **Mobile Optimization**: Collapsible navigation for mobile devices
- **Tablet Adaptation**: Optimized layouts for tablet-sized screens
- **Desktop Experience**: Full-featured desktop interface
- **Touch Support**: Touch-friendly interactions on mobile devices

#### Theme Integration
- **Dark/Light Toggle**: Seamless theme switching
- **System Preference**: Automatic theme detection
- **Theme Persistence**: Remember user theme preferences
- **Custom CSS Variables**: Consistent theming across components

---

## State Management

### Zustand Store Architecture (`/store/index.ts`)
The application uses Zustand for global state management, providing a centralized, type-safe state solution.

#### Store Structure
```typescript
interface AppState {
  // Navigation
  currentPage: string;
  
  // Authentication
  isAuthenticated: boolean;
  user: User | null;
  
  // Core Data
  exams: Exam[];
  conflicts: Conflict[];
  activeSessionId: string | null;
  
  // Role-specific Data
  studentExams: StudentExam[];
  staffAssignments: StaffAssignment[];
  conflictReports: ConflictReport[];
  changeRequests: ChangeRequest[];
  
  // Admin Features
  notifications: Notification[];
  history: HistoryEntry[];
  jobResults: JobResult[];
  filterOptions: FilterOptions;
  
  // System Status
  systemStatus: SystemStatus;
  schedulingStatus: SchedulingStatus;
  uploadStatus: UploadStatus;
  
  // Settings
  settings: AppSettings;
}
```

#### State Management Patterns
- **Immutable Updates**: All state changes create new objects
- **Derived State**: Computed values based on base state
- **Action Creators**: Standardized methods for state updates
- **Type Safety**: Full TypeScript integration for type checking
- **Performance Optimization**: Selective subscriptions to prevent unnecessary re-renders

#### Key State Actions
- **Navigation**: `setCurrentPage(page: string)`
- **Authentication**: `setAuthenticated(isAuth: boolean, user?: User)`
- **Data Management**: `setExams()`, `setConflicts()`, `updateFilterOptions()`
- **Status Updates**: `setSystemStatus()`, `setSchedulingStatus()`
- **Role-specific Actions**: `addConflictReport()`, `addChangeRequest()`

#### Real-time State Updates
The store implements patterns for real-time updates:
- **WebSocket Integration Points**: Prepared for real-time data synchronization
- **Optimistic Updates**: Immediate UI updates with server reconciliation
- **Conflict Resolution**: Handle concurrent updates gracefully
- **Error Recovery**: Rollback capabilities for failed operations

---

## API Architecture & Stubbed Functionality

### Current API Layer (`/services/api.ts`)
The application includes a comprehensive API service layer that currently operates with mock data but is designed for easy integration with real backend services.

#### API Service Structure
```typescript
class ApiService {
  // Authentication
  async login(email: string, password: string): Promise<AuthResponse>
  async logout(): Promise<void>
  async refreshToken(): Promise<TokenResponse>
  
  // Exam Management
  async getExams(sessionId: string): Promise<Exam[]>
  async createExam(exam: CreateExamRequest): Promise<Exam>
  async updateExam(id: string, updates: UpdateExamRequest): Promise<Exam>
  async deleteExam(id: string): Promise<void>
  
  // Scheduling
  async startSchedulingJob(params: SchedulingParams): Promise<JobResponse>
  async getJobStatus(jobId: string): Promise<JobStatus>
  async cancelJob(jobId: string): Promise<void>
  
  // Conflict Management
  async getConflicts(sessionId: string): Promise<Conflict[]>
  async resolveConflict(conflictId: string, resolution: ConflictResolution): Promise<void>
  
  // User Management
  async getUsers(): Promise<User[]>
  async createUser(user: CreateUserRequest): Promise<User>
  async updateUser(id: string, updates: UpdateUserRequest): Promise<User>
}
```

#### Mock Data Integration
Currently, all API calls are stubbed with realistic mock data:
- **Response Simulation**: Realistic response times and data structures
- **Error Simulation**: Mock error conditions for testing error handling
- **State Consistency**: Mock responses maintain data consistency
- **Pagination Support**: Mock pagination for large datasets

#### WebSocket Architecture (Stubbed)
Designed for real-time updates with WebSocket integration:
```typescript
interface WebSocketService {
  // Connection Management
  connect(): Promise<void>
  disconnect(): void
  
  // Event Subscriptions
  onSchedulingUpdate(callback: (update: SchedulingUpdate) => void): void
  onConflictDetected(callback: (conflict: Conflict) => void): void
  onNotification(callback: (notification: Notification) => void): void
  
  // Real-time Data
  subscribeToExamUpdates(sessionId: string): void
  subscribeToJobProgress(jobId: string): void
}
```

#### Backend Integration Points
The API layer is designed for seamless integration with various backend technologies:
- **RESTful API**: Standard HTTP-based API integration
- **GraphQL**: Query-based data fetching support
- **WebSocket**: Real-time bidirectional communication
- **Server-Sent Events**: One-way real-time updates
- **Microservices**: Support for distributed backend architecture

### Expected Backend Services

#### Authentication Service
- **JWT Token Management**: Secure token-based authentication
- **Role-Based Access Control**: Permission management
- **Session Management**: User session tracking
- **Password Recovery**: Secure password reset functionality

#### Scheduling Engine Service
- **Constraint Solver Integration**: CP-SAT or similar constraint programming
- **Genetic Algorithm**: Alternative optimization approach
- **Job Queue Management**: Async job processing
- **Result Comparison**: Multi-solution analysis

#### Data Management Service
- **CRUD Operations**: Full exam lifecycle management
- **Conflict Detection**: Real-time constraint violation detection
- **Data Validation**: Server-side data integrity checking
- **Audit Logging**: Comprehensive change tracking

#### Notification Service
- **Email Notifications**: Automated email alerts
- **Push Notifications**: Browser push notification support
- **SMS Integration**: Critical alert SMS delivery
- **Notification Preferences**: User-configurable alert settings

---

## Scheduling Engine

### Algorithm Integration
The system is designed to integrate with sophisticated scheduling algorithms for optimal timetable generation.

#### CP-SAT (Constraint Programming)
- **Hard Constraint Satisfaction**: Guaranteed constraint adherence
- **Optimization Objectives**: Minimize soft constraint violations
- **Scalability**: Handle large-scale scheduling problems
- **Exact Solutions**: Find optimal solutions when possible

#### Genetic Algorithm
- **Population-based Search**: Evolve solutions over generations
- **Crossover Operations**: Combine successful scheduling patterns
- **Mutation Strategies**: Introduce scheduling variations
- **Fitness Evaluation**: Multi-objective optimization scoring

#### Hybrid Approaches
- **Two-phase Optimization**: CP-SAT for feasibility, GA for optimization
- **Constraint Relaxation**: Gradual constraint loosening for difficult problems
- **Local Search**: Refinement of existing solutions
- **Parallel Processing**: Multi-core algorithm execution

### Job Management System
The scheduling system includes comprehensive job management capabilities:

#### Job Lifecycle
1. **Job Creation**: Configure scheduling parameters and constraints
2. **Validation**: Verify input data and constraint consistency
3. **Execution**: Run scheduling algorithm with progress tracking
4. **Monitoring**: Real-time progress updates and metric collection
5. **Completion**: Result generation and quality assessment
6. **Storage**: Persistent storage of results and metadata

#### Progress Tracking
```typescript
interface SchedulingProgress {
  phase: 'initialization' | 'cp-sat' | 'genetic-algorithm' | 'finalization';
  progress: number;        // 0-100 percentage
  metrics: {
    processed_exams: number;
    total_exams: number;
    hard_constraints_violations: number;
    soft_constraints_violations: number;
    fitness_score: number;
    generation?: number;    // For genetic algorithm
    error_message?: string;
  };
  estimatedTimeRemaining: number; // Seconds
}
```

#### Job Control
- **Pause/Resume**: Interrupt and continue job execution
- **Cancellation**: Terminate running jobs with cleanup
- **Priority Management**: Queue management for multiple jobs
- **Resource Allocation**: CPU and memory management for jobs

---

## Conflict Management

### Conflict Detection System
The application implements a comprehensive conflict detection system that identifies and categorizes scheduling violations.

#### Conflict Types
- **Room Double-booking**: Multiple exams scheduled in the same room at the same time
- **Instructor Conflicts**: Single instructor assigned to multiple simultaneous exams
- **Student Conflicts**: Students enrolled in overlapping examinations
- **Capacity Violations**: More students than room capacity
- **Time Constraint Violations**: Exams scheduled outside allowed time windows
- **Equipment Conflicts**: Specialized equipment double-booked

#### Conflict Severity Levels
- **High Severity**: Critical conflicts that prevent exam execution
- **Medium Severity**: Conflicts that significantly impact scheduling quality
- **Low Severity**: Minor optimization opportunities

#### Detection Algorithms
```typescript
interface ConflictDetector {
  detectRoomConflicts(exams: Exam[]): Conflict[]
  detectInstructorConflicts(exams: Exam[]): Conflict[]
  detectStudentConflicts(exams: Exam[], enrollments: Enrollment[]): Conflict[]
  detectCapacityViolations(exams: Exam[]): Conflict[]
  validateTimeConstraints(exams: Exam[], constraints: TimeConstraint[]): Conflict[]
}
```

### Conflict Resolution System
The system provides both automatic and manual conflict resolution capabilities.

#### Automatic Resolution
- **Time Slot Adjustment**: Automatically reschedule conflicted exams
- **Room Reassignment**: Move exams to available rooms
- **Instructor Substitution**: Assign alternative qualified instructors
- **Capacity Optimization**: Split large exams across multiple rooms

#### Manual Resolution Tools
- **Conflict Panel**: Comprehensive interface for conflict management
- **Alternative Suggestions**: AI-powered resolution recommendations
- **Impact Analysis**: Preview effects of proposed changes
- **Batch Resolution**: Resolve multiple related conflicts simultaneously

#### Resolution Workflow
1. **Conflict Identification**: Automatic detection and categorization
2. **Impact Assessment**: Analyze effects on overall schedule
3. **Solution Generation**: Create multiple resolution options
4. **Administrative Review**: Human oversight for complex conflicts
5. **Implementation**: Apply approved resolutions
6. **Verification**: Confirm conflict resolution success

---

## User Interface Components

### Shadcn/ui Component Library
The application leverages the Shadcn/ui component library for consistent, accessible, and customizable UI components.

#### Available Components
- **Layout Components**: Card, Separator, Tabs, Accordion
- **Form Components**: Input, Textarea, Select, Checkbox, Radio Group
- **Feedback Components**: Alert, Toast (Sonner), Progress, Badge
- **Navigation Components**: Breadcrumb, Pagination, Command Menu
- **Overlay Components**: Dialog, Popover, Tooltip, Sheet
- **Data Display**: Table, Calendar, Chart
- **Interactive Components**: Button, Toggle, Slider, Switch

#### Customization System
All components are customized through the CSS variable system defined in `/styles/globals.css`:
- **Color System**: Semantic color tokens for consistent theming
- **Typography**: Font size, weight, and line height variables
- **Spacing**: Consistent spacing scale throughout the application
- **Border Radius**: Unified border radius system
- **Shadows**: Elevation system for depth and hierarchy

#### Accessibility Features
- **Keyboard Navigation**: Full keyboard accessibility for all interactive elements
- **Screen Reader Support**: Proper ARIA labels and descriptions
- **Focus Management**: Visible focus indicators and logical tab order
- **Color Contrast**: WCAG compliant color contrast ratios
- **Responsive Design**: Mobile-first responsive layouts

### Custom Components
Beyond the Shadcn/ui library, the application includes several custom components tailored for exam scheduling:

#### ExamBlock Component
Specialized component for displaying exam information in the timetable grid:
- **Responsive Layout**: Adapts to available space and screen size
- **Information Density**: Efficiently displays essential exam details
- **Interactive States**: Hover, selected, and dragging states
- **Accessibility**: Full keyboard and screen reader support

#### TimetableGrid Component
Complex grid component for visualizing and editing exam schedules:
- **Dynamic Layout**: Automatically adjusts to exam data and constraints
- **Drag-and-Drop**: Intuitive exam rescheduling interface
- **Conflict Visualization**: Color-coded conflict indicators
- **Performance Optimization**: Efficient rendering for large datasets

#### ConflictPanel Component
Sophisticated interface for managing scheduling conflicts:
- **Real-time Updates**: Live conflict detection and display
- **Resolution Tools**: Interactive conflict resolution interface
- **Batch Operations**: Handle multiple conflicts simultaneously
- **Historical Tracking**: Track conflict resolution history

---

## Utilities & Helpers

### Timetable Utilities (`/utils/timetableUtils.ts`)
Comprehensive utility functions for timetable calculations and manipulations.

#### Time Slot Management
```typescript
function getTimeSlot(time: string): number
function calculateDuration(startTime: string, endTime: string): number
function formatTimeRange(startTime: string, endTime: string): string
function validateTimeSlot(time: string): boolean
```

#### Color Generation
```typescript
function generateDepartmentColors(departments: string[]): Record<string, string>
function generateDistinctColors(count: number): string[]
function getColorForDepartment(department: string, colors: Record<string, string>): string
```

#### Conflict Detection Utilities
```typescript
function detectTimeOverlap(exam1: Exam, exam2: Exam): boolean
function calculateConflictSeverity(conflict: Conflict): number
function groupConflictsByType(conflicts: Conflict[]): Record<string, Conflict[]>
```

#### Layout Calculations
```typescript
function calculateExamPosition(exam: Exam, timeSlots: string[]): ExamPosition
function optimizeGridLayout(exams: Exam[]): OptimizedLayout
function calculateStackLevels(overlappingExams: Exam[]): StackLevel[]
```

### API Utilities (`/hooks/useApi.ts`)
Custom React hooks for API integration with loading states, error handling, and caching.

#### Data Fetching Hooks
```typescript
function useExams(sessionId: string): ApiResponse<Exam[]>
function useConflicts(sessionId: string): ApiResponse<Conflict[]>
function useKPIData(): ApiResponse<KPIData>
function useSchedulingJobs(): ApiResponse<SchedulingJob[]>
```

#### Mutation Hooks
```typescript
function useCreateExam(): MutationHook<CreateExamRequest, Exam>
function useUpdateExam(): MutationHook<UpdateExamRequest, Exam>
function useResolveConflict(): MutationHook<ConflictResolution, void>
```

### Authentication Utilities (`/hooks/useAuth.ts`)
Authentication management with secure token handling and role-based access control.

#### Authentication Hook
```typescript
function useAuth(): {
  user: User | null;
  isAuthenticated: boolean;
  isLoggingIn: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}
```

---

## Configuration

### Application Configuration (`/config/index.ts`)
Centralized configuration management for environment-specific settings.

#### Configuration Structure
```typescript
interface AppConfig {
  api: {
    baseUrl: string;
    timeout: number;
    retryAttempts: number;
  };
  scheduling: {
    defaultAlgorithm: 'cp-sat' | 'genetic';
    maxJobDuration: number;
    parallelJobs: number;
  };
  ui: {
    itemsPerPage: number;
    autoSaveInterval: number;
    tooltipDelay: number;
  };
  features: {
    enableWebSockets: boolean;
    enableNotifications: boolean;
    enableAnalytics: boolean;
  };
}
```

#### Environment Support
- **Development**: Local development configuration
- **Staging**: Pre-production testing environment
- **Production**: Live production environment
- **Testing**: Automated testing configuration

---

## Theme System

### CSS Variable System (`/styles/globals.css`)
The application uses CSS variables for a consistent, customizable theme system.

#### Color Tokens
```css
:root {
  --background: #ffffff;
  --foreground: oklch(0.145 0 0);
  --primary: #030213;
  --secondary: oklch(0.95 0.0058 264.53);
  --muted: #ececf0;
  --border: rgba(0, 0, 0, 0.1);
  /* ... additional color tokens */
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  /* ... dark theme overrides */
}
```

#### Typography System
```css
h1 { font-size: var(--text-2xl); font-weight: var(--font-weight-medium); }
h2 { font-size: var(--text-xl); font-weight: var(--font-weight-medium); }
h3 { font-size: var(--text-lg); font-weight: var(--font-weight-medium); }
p { font-size: var(--text-base); font-weight: var(--font-weight-normal); }
```

#### Theme Management
- **Automatic Detection**: System preference detection
- **User Preference**: Manual theme selection with persistence
- **Smooth Transitions**: Animated theme switching
- **Component Integration**: Seamless theme integration across all components

---

## Flow Diagrams

### User Authentication Flow
```
1. User accesses application
2. Check authentication state
3. If not authenticated → Show Login page
4. User enters credentials
5. Validate credentials (API call)
6. If valid → Set user state and redirect to role-specific portal
7. If invalid → Show error message
```

### Admin Scheduling Job Flow
```
1. Admin navigates to Scheduling page
2. Configure job parameters (algorithm, constraints, session)
3. Validate configuration
4. Submit job to scheduling engine
5. Display real-time progress updates
6. Handle job completion/failure
7. Present results with conflict analysis
8. Allow result comparison and export
```

### Student Conflict Reporting Flow
```
1. Student logs into portal
2. View personal exam schedule
3. Identify scheduling conflict
4. Navigate to conflict reporting form
5. Fill out detailed conflict information
6. Submit conflict report
7. Generate admin notification
8. Track resolution status
9. Receive resolution notification
```

### Staff Change Request Flow
```
1. Staff member logs into portal
2. View current assignments
3. Identify need for change
4. Submit change request with justification
5. Generate admin notification
6. Admin reviews request and impact
7. Admin approves/denies with notes
8. Staff receives notification of decision
9. If approved, schedule is updated
```

---

## Feature Completeness Status

### ✅ Fully Implemented Features
- **Multi-role Authentication System**: Complete login/logout with role-based routing
- **Interactive Timetable Grid**: Drag-and-drop functionality with conflict detection
- **Conflict Management Panel**: Real-time conflict detection and resolution tools
- **Global Search System**: Cross-entity search with intelligent ranking
- **Keyboard Shortcuts**: Comprehensive shortcut system with help overlay
- **Theme System**: Dark/light theme with system preference detection
- **Responsive Design**: Mobile-optimized layouts for all screen sizes
- **State Management**: Zustand-based state with type safety
- **Component Library**: Shadcn/ui integration with custom components
- **Filter System**: Advanced multi-select filtering with presets
- **Notification System**: Real-time notifications with action buttons
- **Audit Trail**: Complete history tracking with change attribution
- **Student Portal**: Personal schedule viewing and conflict reporting
- **Staff Portal**: Assignment management and change requests

### 🔄 Partially Implemented (Stubbed)
- **API Integration**: Mock API responses with realistic data structures
- **Scheduling Engine**: Simulated job execution with progress tracking
- **WebSocket Communication**: Stubbed real-time updates
- **Export Functionality**: UI components ready, actual export logic stubbed
- **Email Notifications**: Notification generation without actual email sending
- **Advanced Analytics**: Chart components with mock data
- **Bulk Operations**: UI ready, backend operations stubbed
- **File Upload**: Drag-and-drop interface without file processing

### ❌ Not Yet Implemented
- **Real Backend Integration**: Actual API endpoints and database connections
- **Advanced Constraint Programming**: Integration with CP-SAT or similar solvers
- **WebSocket Server**: Real-time communication infrastructure
- **Email/SMS Services**: Actual notification delivery systems
- **File Processing**: Excel/CSV import/export functionality
- **Advanced Reporting**: PDF generation and complex report creation
- **Mobile App**: Native mobile application
- **Offline Support**: Offline-first architecture with sync capabilities

---

## Future Development Roadmap

### Phase 1: Backend Integration (Priority: High)
- **Database Design**: Design and implement database schema
- **API Development**: Create RESTful API endpoints
- **Authentication Service**: Implement JWT-based authentication
- **WebSocket Server**: Real-time communication infrastructure
- **File Upload Service**: Handle Excel/CSV import/export

### Phase 2: Advanced Scheduling (Priority: High)
- **Constraint Solver Integration**: Integrate CP-SAT or similar
- **Genetic Algorithm Implementation**: Alternative optimization approach
- **Job Queue System**: Robust job management and execution
- **Performance Optimization**: Handle large-scale scheduling problems
- **Algorithm Comparison**: Side-by-side algorithm performance analysis

### Phase 3: Enhanced User Experience (Priority: Medium)
- **Mobile Application**: Native iOS/Android applications
- **Offline Support**: Offline-first architecture with sync
- **Advanced Visualization**: Enhanced charts and analytics
- **Collaboration Tools**: Multi-user editing and comments
- **Integration APIs**: Connect with other academic systems

### Phase 4: Enterprise Features (Priority: Medium)
- **Multi-tenant Architecture**: Support multiple institutions
- **Advanced Security**: Role-based permissions and audit logs
- **Compliance Features**: FERPA, GDPR compliance tools
- **Scalability Improvements**: Handle thousands of concurrent users
- **Monitoring and Alerting**: Comprehensive system monitoring

### Phase 5: AI and Machine Learning (Priority: Low)
- **Predictive Analytics**: Forecast scheduling challenges
- **Automated Optimization**: AI-powered constraint tuning
- **Pattern Recognition**: Identify recurring scheduling patterns
- **Intelligent Suggestions**: AI-powered scheduling recommendations
- **Natural Language Processing**: Voice-based scheduling commands

---

## Technical Specifications

### Performance Requirements
- **Page Load Time**: < 2 seconds for initial load
- **Interactive Response**: < 100ms for user interactions
- **Scheduling Job Processing**: Handle 1000+ exams within 5 minutes
- **Concurrent Users**: Support 500+ simultaneous users
- **Data Volume**: Handle 10,000+ exams per academic session

### Browser Support
- **Chrome**: Version 90+
- **Firefox**: Version 88+
- **Safari**: Version 14+
- **Edge**: Version 90+
- **Mobile Safari**: iOS 14+
- **Chrome Mobile**: Android 8+

### Accessibility Compliance
- **WCAG 2.1 AA**: Full compliance with accessibility guidelines
- **Keyboard Navigation**: Complete keyboard accessibility
- **Screen Reader Support**: Optimized for assistive technologies
- **Color Contrast**: Minimum 4.5:1 contrast ratio
- **Focus Management**: Clear focus indicators and logical tab order

### Security Considerations
- **Authentication**: JWT tokens with secure storage
- **Authorization**: Role-based access control (RBAC)
- **Data Validation**: Client and server-side input validation
- **XSS Prevention**: Content Security Policy implementation
- **CSRF Protection**: Anti-CSRF token implementation
- **Data Encryption**: HTTPS/TLS for all communications

---

## Conclusion

This Exam Timetabling System represents a comprehensive solution for academic examination scheduling with sophisticated features for conflict management, real-time collaboration, and intelligent optimization. The system's modular architecture, extensive use of modern web technologies, and focus on user experience make it suitable for institutions of various sizes.

The current implementation provides a solid foundation with core functionality fully operational, while maintaining clear separation between implemented features and stubbed functionality to facilitate future development. The role-based access control ensures appropriate functionality for each user type, while the advanced scheduling capabilities provide administrators with powerful tools for managing complex examination schedules.

The system's design prioritizes scalability, maintainability, and extensibility, making it well-positioned for future enhancements and integrations with existing academic management systems.