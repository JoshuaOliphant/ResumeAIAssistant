import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { useAuth } from '../lib/auth';
import { Loader2, Clock, Zap } from 'lucide-react';

type TokenUsage = {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
};

type StatusUpdate = {
  task_id: string;
  status: 'initializing' | 'in_progress' | 'completed' | 'error';
  message: string;
  error?: string;
  progress?: number;
  usage?: TokenUsage;
  logs?: string[];  // Add logs to the status update type
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
  const [progress, setProgress] = useState<number | null>(null);
  const [usage, setUsage] = useState<TokenUsage | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
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
        const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:5001/api/v1'}/websockets/ws/customize/${taskId}?token=${token}`;
        
        const ws = new WebSocket(wsUrl);
        let reconnectTimeout: NodeJS.Timeout;

        ws.onopen = () => {
          setSocket(ws);
          setConnectionAttempts(0);
        };

        ws.onmessage = (event) => {
          try {
            console.log('WebSocket message received:', event.data);
            const data: StatusUpdate = JSON.parse(event.data);
            
            if (data.task_id === taskId) {
              console.log('Task status update:', data.status, data.message);
              setStatus(data.status);
              setMessage(data.message);
              
              // Update progress if available
              if (typeof data.progress === 'number') {
                setProgress(data.progress);
              }
              
              // Update usage if available
              if (data.usage) {
                setUsage(data.usage);
              }
              
              // Update logs if available
              if (data.logs && Array.isArray(data.logs)) {
                setLogs(data.logs);
              }
              
              // Handle completion and errors
              if (data.status === 'completed' && onComplete) {
                console.log('Task completed, calling onComplete handler');
                onComplete(data);
                sendNotification('Resume Customization Complete', 'Your resume has been customized successfully.');
              } else if (data.status === 'error' && onError) {
                console.log('Task error, calling onError handler');
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
              <div className="text-center space-y-4">
                <Badge variant="success" className="px-3 py-1 text-base">Completed</Badge>
                <p className="text-green-600 dark:text-green-400 mt-2">Your customized resume is ready!</p>
                {usage && (
                  <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
                    <div className="flex items-center justify-center space-x-2 text-sm text-green-700 dark:text-green-300">
                      <Zap className="h-4 w-4" />
                      <span>Total tokens used: {usage.total_tokens?.toLocaleString() || 'N/A'}</span>
                    </div>
                  </div>
                )}
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
                
                {/* Progress bar */}
                {progress !== null && (
                  <div className="w-full max-w-md mx-auto space-y-2">
                    <Progress value={progress} className="w-full" />
                    <p className="text-sm text-muted-foreground">{Math.round(progress)}% complete</p>
                  </div>
                )}
                
                {/* Usage statistics */}
                {usage && (
                  <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg max-w-md mx-auto">
                    <div className="flex items-center justify-center space-x-2 text-sm text-blue-700 dark:text-blue-300 mb-2">
                      <Zap className="h-4 w-4" />
                      <span>Token Usage</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {usage.prompt_tokens && (
                        <div className="text-center">
                          <div className="font-medium">{usage.prompt_tokens.toLocaleString()}</div>
                          <div className="text-muted-foreground">Prompt</div>
                        </div>
                      )}
                      {usage.completion_tokens && (
                        <div className="text-center">
                          <div className="font-medium">{usage.completion_tokens.toLocaleString()}</div>
                          <div className="text-muted-foreground">Response</div>
                        </div>
                      )}
                    </div>
                    {usage.total_tokens && (
                      <div className="text-center mt-2 pt-2 border-t border-blue-200 dark:border-blue-700">
                        <div className="font-medium text-sm">{usage.total_tokens.toLocaleString()}</div>
                        <div className="text-muted-foreground text-xs">Total</div>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Time estimate */}
                <div className="flex items-center justify-center space-x-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>This may take up to 20 minutes</span>
                </div>
                
                {/* Live logs display */}
                {logs.length > 0 && (
                  <div className="mt-6 space-y-2">
                    <h4 className="text-sm font-medium text-muted-foreground">Live Progress</h4>
                    <div className="bg-black/5 dark:bg-white/5 rounded-lg p-3 max-h-48 overflow-y-auto">
                      <div className="space-y-1 text-xs font-mono">
                        {logs.slice(-10).map((log, index) => (
                          <div key={index} className="text-muted-foreground">
                            {log}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}