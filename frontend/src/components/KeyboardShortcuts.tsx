// frontend/src/components/KeyboardShortcuts.tsx
import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { 
  Search, 
  LayoutDashboard, 
  Calendar, 
  PlayCircle, 
  Sliders, 
  BarChart3,
  Command
} from 'lucide-react';

interface KeyboardShortcutsProps {
  isOpen: boolean;
  onClose: () => void;
}

export function KeyboardShortcuts({ isOpen, onClose }: KeyboardShortcutsProps) {
  const shortcuts = [
    {
      category: 'Navigation',
      items: [
        { keys: ['Ctrl', 'Shift', 'D'], description: 'Go to Dashboard', icon: LayoutDashboard },
        { keys: ['Ctrl', 'Shift', 'T'], description: 'Go to Timetable', icon: Calendar },
        { keys: ['Ctrl', 'Shift', 'S'], description: 'Go to Scheduling', icon: PlayCircle },
        { keys: ['Ctrl', 'Shift', 'C'], description: 'Go to Constraints', icon: Sliders },
        { keys: ['Ctrl', 'Shift', 'A'], description: 'Go to Analytics', icon: BarChart3 },
      ]
    },
    {
      category: 'Search & Actions',
      items: [
        { keys: ['Ctrl', 'K'], description: 'Open Global Search', icon: Search },
        { keys: ['F'], description: 'Focus Filters (when available)', icon: null },
        { keys: ['Esc'], description: 'Close modals/dialogs', icon: null },
        { keys: ['?'], description: 'Show keyboard shortcuts', icon: Command },
      ]
    }
  ];

  const formatKey = (key: string) => {
    // Replace Ctrl with Cmd on Mac
    const isMac = navigator.platform.includes('Mac');
    if (key === 'Ctrl' && isMac) {
      return '⌘';
    }
    if (key === 'Shift') {
      return '⇧';
    }
    return key;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Command className="h-5 w-5" />
            Keyboard Shortcuts
          </DialogTitle>
          <DialogDescription>
            Learn keyboard shortcuts to navigate and use the application more efficiently.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6">
          {shortcuts.map((category) => (
            <div key={category.category}>
              <h3 className="font-medium mb-3">{category.category}</h3>
              <div className="space-y-2">
                {category.items.map((item, index) => {
                  const Icon = item.icon;
                  return (
                    <div key={index} className="flex items-center justify-between py-2">
                      <div className="flex items-center gap-3">
                        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
                        <span className="text-sm">{item.description}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        {item.keys.map((key, keyIndex) => (
                          <React.Fragment key={keyIndex}>
                            <Badge variant="outline" className="px-2 py-1 text-xs">
                              {formatKey(key)}
                            </Badge>
                            {keyIndex < item.keys.length - 1 && (
                              <span className="text-muted-foreground text-xs">+</span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
              {category.category !== shortcuts[shortcuts.length - 1].category && (
                <Separator className="mt-4" />
              )}
            </div>
          ))}
        </div>
        
        <div className="text-xs text-muted-foreground">
          <p>
            Press <Badge variant="outline" className="px-1.5 py-0.5 text-xs">?</Badge> anytime to view these shortcuts
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}