import { useState, useEffect } from 'react';
import { Bell } from 'lucide-react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from './ui/dropdown-menu';
import { Badge } from './ui/badge';

type Notification = {
  id: string;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
};

type NotificationBadgeProps = {
  className?: string;
};

// Helper function to get notifications from localStorage
const getStoredNotifications = (): Notification[] => {
  if (typeof window === 'undefined') return [];
  
  try {
    const stored = localStorage.getItem('notifications');
    if (stored) {
      const parsed = JSON.parse(stored);
      return Array.isArray(parsed) ? parsed.map(n => ({
        ...n,
        timestamp: new Date(n.timestamp)
      })) : [];
    }
  } catch (error) {
    console.error('Error loading notifications from localStorage:', error);
  }
  
  return [];
};

// Helper function to save notifications to localStorage
const saveNotifications = (notifications: Notification[]) => {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.setItem('notifications', JSON.stringify(notifications));
  } catch (error) {
    console.error('Error saving notifications to localStorage:', error);
  }
};

export function NotificationBadge({ className }: NotificationBadgeProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  
  // Initialize notifications from localStorage
  useEffect(() => {
    setNotifications(getStoredNotifications());
    
    // Also set up to listen for notification events from other components
    const handleNotificationEvent = (event: CustomEvent) => {
      if (event.detail && event.detail.type === 'notification') {
        addNotification(event.detail.notification);
      }
    };
    
    window.addEventListener('customNotification', handleNotificationEvent as EventListener);
    
    return () => {
      window.removeEventListener('customNotification', handleNotificationEvent as EventListener);
    };
  }, []);
  
  // Count unread notifications
  const unreadCount = notifications.filter(n => !n.read).length;
  
  // Function to add a new notification
  const addNotification = (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      id: Date.now().toString(),
      ...notification,
      timestamp: new Date(),
      read: false
    };
    
    setNotifications(prev => {
      const updated = [newNotification, ...prev].slice(0, 20); // Keep only 20 most recent
      saveNotifications(updated);
      return updated;
    });
  };
  
  // Mark a notification as read
  const markAsRead = (id: string) => {
    setNotifications(prev => {
      const updated = prev.map(n => 
        n.id === id ? { ...n, read: true } : n
      );
      saveNotifications(updated);
      return updated;
    });
  };
  
  // Mark all notifications as read
  const markAllAsRead = () => {
    setNotifications(prev => {
      const updated = prev.map(n => ({ ...n, read: true }));
      saveNotifications(updated);
      return updated;
    });
  };
  
  // Remove a notification
  const removeNotification = (id: string) => {
    setNotifications(prev => {
      const updated = prev.filter(n => n.id !== id);
      saveNotifications(updated);
      return updated;
    });
  };
  
  // Clear all notifications
  const clearAllNotifications = () => {
    setNotifications([]);
    saveNotifications([]);
  };
  
  // Format relative time for notifications (e.g., "2 hours ago")
  const formatRelativeTime = (date: Date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffInSeconds < 60) {
      return 'just now';
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    } else {
      const days = Math.floor(diffInSeconds / 86400);
      return `${days} day${days !== 1 ? 's' : ''} ago`;
    }
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className={`relative ${className || ''}`}>
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge 
              variant="destructive" 
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 rounded-full text-xs"
            >
              {unreadCount > 9 ? '9+' : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <div className="flex items-center justify-between p-2">
          <span className="text-sm font-medium">Notifications</span>
          {notifications.length > 0 && (
            <div className="flex gap-2">
              {unreadCount > 0 && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-7 text-xs" 
                  onClick={markAllAsRead}
                >
                  Mark all as read
                </Button>
              )}
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-7 text-xs" 
                onClick={clearAllNotifications}
              >
                Clear all
              </Button>
            </div>
          )}
        </div>
        
        <DropdownMenuSeparator />
        
        {notifications.length === 0 ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No notifications
          </div>
        ) : (
          <div className="max-h-[400px] overflow-y-auto">
            {notifications.map(notification => (
              <DropdownMenuItem 
                key={notification.id} 
                className={`cursor-pointer p-3 flex flex-col items-start gap-1 ${
                  !notification.read ? 'bg-muted/50' : ''
                }`}
                onClick={() => {
                  markAsRead(notification.id);
                  // You can add navigation logic here if needed
                }}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="font-medium">{notification.title}</span>
                  <span className="text-xs text-muted-foreground">
                    {formatRelativeTime(notification.timestamp)}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{notification.message}</p>
              </DropdownMenuItem>
            ))}
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// Helper function to add a notification from anywhere in the app
export function addNotification(notification: { title: string; message: string }) {
  if (typeof window !== 'undefined') {
    const event = new CustomEvent('customNotification', {
      detail: {
        type: 'notification',
        notification
      }
    });
    
    window.dispatchEvent(event);
    
    // Also send browser notification if permission is granted
    if (Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.message,
        icon: '/favicon.ico'
      });
    }
  }
}