// frontend/src/pages/Settings.tsx

import React, { useState } from 'react'
import { 
  User, 
  Bell, 
  Palette, 
  Database,
  Shield,
  Sliders,
  Save,
  RotateCcw,
  Trash2,
  Download,
  Upload
  // REMOVED: Settings as SettingsIcon
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Switch } from '../components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
// REMOVED: Unused 'Slider' import
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Badge } from '../components/ui/badge'
import { Separator } from '../components/ui/separator'
import { useAppStore } from '../store'
import { toast } from 'sonner'

interface UserProfile {
  id: string
  name: string
  email: string
  role: 'admin' | 'exam_officer' | 'hod' | 'dean' | 'registry'
  department: string
  permissions: string[]
}

const constraintTemplates = [
  {
    id: 'balanced',
    name: 'Balanced',
    description: 'Equal weight to all constraints',
    weights: {
      noOverlap: 1.0,
      roomCapacity: 0.9,
      instructorAvailability: 0.8,
      studentConflicts: 0.95
    }
  },
  {
    id: 'strict',
    name: 'Strict',
    description: 'Prioritize hard constraints',
    weights: {
      noOverlap: 1.0,
      roomCapacity: 1.0,
      instructorAvailability: 0.6,
      studentConflicts: 1.0
    }
  },
  {
    id: 'flexible',
    name: 'Flexible',
    description: 'Allow more soft constraint violations',
    weights: {
      noOverlap: 1.0,
      roomCapacity: 0.7,
      instructorAvailability: 0.5,
      studentConflicts: 0.8
    }
  }
]

function UserProfileSection() {
  const [profile, setProfile] = useState<UserProfile>({
    id: '1',
    name: 'John Doe',
    email: 'john.doe@university.edu',
    role: 'admin',
    department: 'Computer Science',
    permissions: ['create', 'read', 'update', 'delete', 'export']
  })

  const [isEditing, setIsEditing] = useState(false)

  const handleSave = () => {
    setIsEditing(false)
    toast.success('Profile updated successfully!')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center">
            <User className="h-5 w-5 mr-2" />
            User Profile
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEditing(!isEditing)}
          >
            {isEditing ? 'Cancel' : 'Edit'}
          </Button>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input
              value={profile.name}
              onChange={(e) => setProfile(prev => ({ ...prev, name: e.target.value }))}
              disabled={!isEditing}
            />
          </div>
          
          <div className="space-y-2">
            <Label>Email</Label>
            <Input
              value={profile.email}
              onChange={(e) => setProfile(prev => ({ ...prev, email: e.target.value }))}
              disabled={!isEditing}
            />
          </div>
          
          <div className="space-y-2">
            <Label>Role</Label>
            <Select
              value={profile.role}
              // FIXED: Replaced 'any' with a type assertion
              onValueChange={(value) => setProfile(prev => ({ ...prev, role: value as UserProfile['role'] }))}
              disabled={!isEditing}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Administrator</SelectItem>
                <SelectItem value="exam_officer">Exam Officer</SelectItem>
                <SelectItem value="hod">Head of Department</SelectItem>
                <SelectItem value="dean">Dean</SelectItem>
                <SelectItem value="registry">Registry Staff</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="space-y-2">
            <Label>Department</Label>
            <Input
              value={profile.department}
              onChange={(e) => setProfile(prev => ({ ...prev, department: e.target.value }))}
              disabled={!isEditing}
            />
          </div>
        </div>
        
        {/* Permissions */}
        <div className="space-y-2">
          <Label>Permissions</Label>
          <div className="flex flex-wrap gap-2">
            {profile.permissions.map((permission) => (
              <Badge key={permission} variant="default">
                {permission}
              </Badge>
            ))}
          </div>
        </div>
        
        {isEditing && (
          <Button onClick={handleSave}>
            <Save className="h-4 w-4 mr-2" />
            Save Changes
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

function NotificationSettings() {
  const { settings, updateSettings } = useAppStore()
  const [localSettings, setLocalSettings] = useState({
    emailNotifications: true,
    conflictAlerts: true,
    schedulingUpdates: true,
    reportGeneration: false,
    systemMaintenance: true
  })

  const handleSave = () => {
    updateSettings({
      notifications: settings.notifications
    })
    toast.success('Notification settings saved!')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <Bell className="h-5 w-5 mr-2" />
          Notification Preferences
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {Object.entries(localSettings).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between">
            <div>
              <Label className="font-medium capitalize">
                {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
              </Label>
              <p className="text-sm text-gray-500">
                {key === 'emailNotifications' && 'Receive notifications via email'}
                {key === 'conflictAlerts' && 'Get alerted when conflicts are detected'}
                {key === 'schedulingUpdates' && 'Updates on scheduling progress'}
                {key === 'reportGeneration' && 'Notifications when reports are ready'}
                {key === 'systemMaintenance' && 'System maintenance announcements'}
              </p>
            </div>
            <Switch
              checked={value}
              onCheckedChange={(checked) => 
                setLocalSettings(prev => ({ ...prev, [key]: checked }))
              }
            />
          </div>
        ))}
        
        <Button onClick={handleSave} className="w-full">
          <Save className="h-4 w-4 mr-2" />
          Save Notification Settings
        </Button>
      </CardContent>
    </Card>
  )
}

function ConstraintTemplates() {
  const { updateSettings } = useAppStore()
  const [selectedTemplate, setSelectedTemplate] = useState('balanced')

  const applyTemplate = (templateId: string) => {
    const template = constraintTemplates.find(t => t.id === templateId)
    if (template) {
      updateSettings({
        constraintWeights: template.weights
      })
      toast.success(`Applied ${template.name} constraint template!`)
    }
  }

  const resetToDefaults = () => {
    updateSettings({
      constraintWeights: {
        noOverlap: 1.0,
        roomCapacity: 0.9,
        instructorAvailability: 0.8,
        studentConflicts: 0.95
      }
    })
    toast.success('Reset to default constraint weights!')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <Sliders className="h-5 w-5 mr-2" />
          Constraint Templates
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {constraintTemplates.map((template) => (
            <Card 
              key={template.id} 
              className={`cursor-pointer transition-colors ${
                selectedTemplate === template.id ? 'ring-2 ring-blue-500' : ''
              }`}
              onClick={() => setSelectedTemplate(template.id)}
            >
              <CardContent className="p-4">
                <h4 className="font-medium mb-2">{template.name}</h4>
                <p className="text-sm text-gray-600 mb-3">{template.description}</p>
                
                <div className="space-y-1 text-xs">
                  {Object.entries(template.weights).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="capitalize">{key.replace(/([A-Z])/g, ' $1')}</span>
                      <span>{value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        
        <div className="flex space-x-2">
          <Button 
            onClick={() => applyTemplate(selectedTemplate)}
            disabled={!selectedTemplate}
          >
            Apply Template
          </Button>
          <Button variant="outline" onClick={resetToDefaults}>
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset to Defaults
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function SystemIntegration() {
  const [apiKeys, setApiKeys] = useState({
    sisIntegration: 'sk-sis-****************************',
    emailService: 'smtp-****************************',
    cloudStorage: 'cs-****************************'
  })

  // FIXED: Removed unused 'setConnectionStatus'
  const [connectionStatus] = useState({
    sisIntegration: 'connected',
    emailService: 'connected',
    cloudStorage: 'disconnected'
  })

  const testConnection = (service: string) => {
    toast.info(`Testing ${service} connection...`)
    // Mock test
    setTimeout(() => {
      toast.success(`${service} connection successful!`)
    }, 2000)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center">
          <Database className="h-5 w-5 mr-2" />
          System Integration
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {Object.entries(apiKeys).map(([service, key]) => (
          <div key={service} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="font-medium capitalize">
                {service.replace(/([A-Z])/g, ' $1')}
              </Label>
              <Badge variant={
                connectionStatus[service as keyof typeof connectionStatus] === 'connected' 
                  ? 'default' : 'destructive'
              }>
                {connectionStatus[service as keyof typeof connectionStatus]}
              </Badge>
            </div>
            
            <div className="flex space-x-2">
              <Input
                type="password"
                value={key}
                onChange={(e) => setApiKeys(prev => ({ ...prev, [service]: e.target.value }))}
                className="flex-1"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => testConnection(service)}
              >
                Test
              </Button>
            </div>
          </div>
        ))}
        
        <Separator />
        
        <div className="space-y-2">
          <Label className="font-medium">Data Backup & Sync</Label>
          <div className="flex space-x-2">
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Export Settings
            </Button>
            <Button variant="outline">
              <Upload className="h-4 w-4 mr-2" />
              Import Settings
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function DangerZone() {
  const [confirmDelete, setConfirmDelete] = useState('')

  const handleClearData = () => {
    if (confirmDelete === 'DELETE') {
      toast.success('All data cleared successfully!')
      setConfirmDelete('')
    } else {
      toast.error('Please type DELETE to confirm')
    }
  }

  return (
    <Card className="border-red-200">
      <CardHeader>
        <CardTitle className="flex items-center text-red-600">
          <Shield className="h-5 w-5 mr-2" />
          Danger Zone
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <h4 className="font-medium text-red-800 mb-2">Clear All Data</h4>
          <p className="text-sm text-red-700 mb-4">
            This will permanently delete all exams, schedules, and configurations. This action cannot be undone.
          </p>
          
          <div className="space-y-2">
            <Label>Type "DELETE" to confirm:</Label>
            <Input
              value={confirmDelete}
              onChange={(e) => setConfirmDelete(e.target.value)}
              placeholder="DELETE"
            />
          </div>
          
          <Button
            variant="destructive"
            onClick={handleClearData}
            disabled={confirmDelete !== 'DELETE'}
            className="mt-3"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Clear All Data
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export function Settings() {
  const { settings, updateSettings } = useAppStore()

  const handleThemeChange = (theme: 'light' | 'dark') => {
    updateSettings({ theme })
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="constraints">Constraints</TabsTrigger>
          <TabsTrigger value="integration">Integration</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>
        
        <TabsContent value="profile">
          <UserProfileSection />
        </TabsContent>
        
        <TabsContent value="notifications">
          <NotificationSettings />
        </TabsContent>
        
        <TabsContent value="constraints">
          <ConstraintTemplates />
        </TabsContent>
        
        <TabsContent value="integration">
          <SystemIntegration />
        </TabsContent>
        
        <TabsContent value="system" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Palette className="h-5 w-5 mr-2" />
                Appearance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <Label className="font-medium">Theme</Label>
                  <p className="text-sm text-gray-500">Choose between light and dark themes</p>
                </div>
                <Select value={settings.theme} onValueChange={(value: 'light' | 'dark') => handleThemeChange(value)}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="dark">Dark</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
          
          <DangerZone />
        </TabsContent>
      </Tabs>
    </div>
  )
}