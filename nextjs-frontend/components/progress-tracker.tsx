import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { useAuth } from '../lib/auth';
import { Loader2 } from 'lucide-react';

type StatusUpdate = {
  task_id: string;
  status: 'initializing' | 'in_progress' | 'completed' | 'error';
  message: string;
  error?: string;
};

type ProgressTrackerProps = {
  taskId: string;
  title?: string;
  description?: string;
  onComplete?: (result: any) => void;
  onError?: (error: Error) => void;
  showNotifications?: boolean;
  className?: string;
};

export function ProgressTracker({
  taskId,
  title = "Customizing Resume",
  description = "This may take up to 20 minutes to complete",
  onComplete,
  onError,
  showNotifications = true,
  className
}: ProgressTrackerProps) {
  const { isAuthenticated } = useAuth();
  const [status, setStatus] = useState<string>('in_progress');
  const [message, setMessage] = useState<string>('This task may take up to 20 minutes to complete. Please wait.');
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connectionAttempts, setConnectionAttempts] = useState<number>(0);

  // Request browser notification permission
  useEffect(() => {
    if (showNotifications && typeof window !== 'undefined' && "Notification" in window) {
      if (Notification.permission !== "denied") {
        Notification.requestPermission().catch(() => {});
      }
    }
  }, [showNotifications]);

  // Send browser notification
  const sendNotification = useCallback((title: string, body: string) => {
    if (!showNotifications || typeof window === 'undefined' || !("Notification" in window)) {
      return;
    }
    
    try {
      if (Notification.permission === "granted") {
        const notification = new Notification(title, {
          body,
          icon: '/favicon.ico',
          tag: 'resume-customization-progress'
        });
        
        notification.onclick = () => {
          window.focus();
          notification.close();
        };
      }
    } catch (error) {
      console.error("Error sending notification:", error);
    }
  }, [showNotifications]);

  // Connect to WebSocket
  useEffect(() => {
    const connectWebSocket = async () => {
      if (!isAuthenticated || connectionAttempts >= 3) {
        return;
      }

      try {
        const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
        const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:5001/api/v1'}/progress/ws/${taskId}?token=${token}`;
        
        const ws = new WebSocket(wsUrl);
        let reconnectTimeout: NodeJS.Timeout;

        ws.onopen = () => {
          setSocket(ws);
          setConnectionAttempts(0);
        };

        ws.onmessage = (event) => {
          try {
            const data: StatusUpdate = JSON.parse(event.data);
            
            if (data.task_id === taskId) {
              setStatus(data.status);
              setMessage(data.message);
              
              // Handle completion and errors
              if (data.status === 'completed' && onComplete) {
                onComplete(data);
                sendNotification('Resume Customization Complete', 'Your resume has been customized successfully.');
              } else if (data.status === 'error' && onError) {
                onError(new Error(data.error || 'Unknown error'));
                sendNotification('Customization Failed', data.error || 'An error occurred during processing.');
              }
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onerror = () => {
          if (ws.readyState !== WebSocket.CLOSED) {
            setConnectionAttempts(prev => prev + 1);
          }
        };

        ws.onclose = () => {
          setSocket(null);
          
          const backoffTime = Math.min(1000 * Math.pow(2, connectionAttempts), 8000);
          reconnectTimeout = setTimeout(connectWebSocket, backoffTime);
        };

        return () => {
          if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
          }
          if (ws && ws.readyState !== WebSocket.CLOSED) {
            ws.close();
          }
        };
      } catch (error) {
        setConnectionAttempts(prev => prev + 1);
        
        const backoffTime = Math.min(1000 * Math.pow(2, connectionAttempts), 8000);
        setTimeout(connectWebSocket, backoffTime);
      }
    };

    connectWebSocket();
  }, [taskId, isAuthenticated, connectionAttempts, onComplete, onError, sendNotification]);

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex flex-col items-center justify-center py-8">
            {status === 'completed' ? (
              <div className="text-center space-y-2">
                <Badge variant="success" className="px-3 py-1 text-base">Completed</Badge>
                <p className="text-green-600 dark:text-green-400 mt-2">Your customized resume is ready!</p>
              </div>
            ) : status === 'error' ? (
              <div className="text-center space-y-2">
                <Badge variant="destructive" className="px-3 py-1 text-base">Error</Badge>
                <p className="text-red-600 dark:text-red-400 mt-2">{message}</p>
              </div>
            ) : (
              <div className="text-center space-y-4">
                <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
                <p className="text-lg text-center">{message}</p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}