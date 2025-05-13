import { useState, useEffect, useCallback } from 'react';
import { Progress } from './ui/progress';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { ChevronRightIcon, CheckCircleIcon, ClockIcon, XCircleIcon, InfoIcon } from 'lucide-react';
import { useAuth } from '../lib/auth';

type ProgressStage = {
  name: string;
  description: string;
  progress: number;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  message?: string;
  estimated_time_remaining?: number;
};

type ProgressUpdate = {
  task_id: string;
  overall_progress: number;
  status: 'initializing' | 'in_progress' | 'completed' | 'error';
  current_stage?: string;
  stages: Record<string, ProgressStage>;
  message?: string;
  estimated_time_remaining?: number;
  started_at?: string;
  updated_at?: string;
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

const DEFAULT_STAGES = [
  {
    name: 'initialization',
    description: 'Setting up resources and preparing for processing',
    progress: 0.0,
    status: 'pending' as const,
  },
  {
    name: 'analysis',
    description: 'Analyzing resume and job description',
    progress: 0.0,
    status: 'pending' as const,
  },
  {
    name: 'planning',
    description: 'Creating customization plan',
    progress: 0.0,
    status: 'pending' as const,
  },
  {
    name: 'implementation',
    description: 'Implementing customized resume sections',
    progress: 0.0,
    status: 'pending' as const,
  },
  {
    name: 'finalization',
    description: 'Finalizing and assembling customized resume',
    progress: 0.0,
    status: 'pending' as const,
  },
];

export function ProgressTracker({
  taskId,
  title = "Operation Progress",
  description = "Track the progress of your current operation",
  onComplete,
  onError,
  showNotifications = true,
  className
}: ProgressTrackerProps) {
  const { isAuthenticated } = useAuth();
  const [progress, setProgress] = useState<number>(0);
  const [status, setStatus] = useState<string>('initializing');
  const [message, setMessage] = useState<string>('Initializing...');
  const [currentStage, setCurrentStage] = useState<string>('initialization');
  const [stages, setStages] = useState<Record<string, ProgressStage>>({});
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<number | null>(null);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [hasReceivedUpdate, setHasReceivedUpdate] = useState<boolean>(false);
  const [connectionAttempts, setConnectionAttempts] = useState<number>(0);
  const [fallbackMode, setFallbackMode] = useState<boolean>(false);
  const [simulatedProgress, setSimulatedProgress] = useState<number>(0);
  const [activeTab, setActiveTab] = useState<string>('overview');

  // Initialize default stages
  useEffect(() => {
    const initialStages: Record<string, ProgressStage> = {};
    DEFAULT_STAGES.forEach(stage => {
      initialStages[stage.name] = stage;
    });
    setStages(initialStages);
  }, []);

  // Format time remaining in a human-readable way
  const formatTimeRemaining = (seconds: number): string => {
    // Handle invalid or very small values
    if (seconds <= 0) {
      return 'Almost done';
    }
    
    // Round to the nearest integer to avoid decimal places
    const roundedSeconds = Math.round(seconds);
    
    if (roundedSeconds < 15) {
      return 'Just a few seconds';
    } else if (roundedSeconds < 60) {
      return `${roundedSeconds} seconds`;
    } else if (roundedSeconds < 3600) {
      const minutes = Math.ceil(roundedSeconds / 60);
      return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
    } else {
      const hours = Math.floor(roundedSeconds / 3600);
      const minutes = Math.ceil((roundedSeconds % 3600) / 60);
      
      if (minutes === 0) {
        return `${hours} hour${hours !== 1 ? 's' : ''}`;
      } else {
        return `${hours} hour${hours !== 1 ? 's' : ''} ${minutes} min`;
      }
    }
  };

  // Request browser notification permission
  useEffect(() => {
    if (showNotifications && typeof window !== 'undefined' && "Notification" in window) {
      // Check if permission isn't denied (could be "default" or "granted")
      if (Notification.permission !== "denied") {
        // Request permission and handle the promise return (modern browsers)
        Notification.requestPermission().then(permission => {
          if (permission === "granted") {
            console.log("Notification permission granted");
          }
        }).catch(error => {
          console.error("Error requesting notification permission:", error);
        });
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
          tag: 'resume-customization-progress', // Group similar notifications
          requireInteraction: true // Keep notification visible until user interacts with it
        });
        
        // Handle notification clicks
        notification.onclick = () => {
          window.focus(); // Focus the window when notification is clicked
          notification.close();
        };
      } else if (Notification.permission !== "denied") {
        // If permission is "default" (not yet decided), try requesting it one more time
        Notification.requestPermission().then(permission => {
          if (permission === "granted") {
            sendNotification(title, body); // Try again after permission is granted
          }
        });
      }
    } catch (error) {
      console.error("Error sending notification:", error);
    }
  }, [showNotifications]);

  // Connect to WebSocket and handle reconnection
  useEffect(() => {
    const connectWebSocket = async () => {
      if (!isAuthenticated) {
        console.log('Not authenticated, skipping WebSocket connection');
        return;
      }
      
      if (connectionAttempts >= 3) {
        // After 3 failed attempts, fall back to simulated progress
        console.log('Maximum reconnection attempts reached, falling back to simulated progress');
        setFallbackMode(true);
        return;
      }

      try {
        // Get the token from localStorage instead of using getAccessToken
        const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
        const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:5000/api/v1'}/progress/ws/${taskId}?token=${token}`;
        console.log(`Connecting to WebSocket: ${wsUrl.replace(/token=.*/, 'token=***')}`);
        
        const ws = new WebSocket(wsUrl);
        let reconnectTimeout: NodeJS.Timeout;

        ws.onopen = () => {
          console.log('WebSocket connection established');
          setSocket(ws);
          // Reset connection attempts on successful connection
          if (connectionAttempts > 0) {
            setConnectionAttempts(0);
          }
        };

        ws.onmessage = (event) => {
          try {
            const data: ProgressUpdate = JSON.parse(event.data);
            
            if (data.task_id === taskId) {
              setHasReceivedUpdate(true);
              setProgress(data.overall_progress * 100);
              setStatus(data.status);
              
              if (data.message) {
                setMessage(data.message);
              }
              
              if (data.current_stage) {
                setCurrentStage(data.current_stage);
              }
              
              if (data.stages) {
                setStages(data.stages);
              }
              
              if (data.estimated_time_remaining !== undefined) {
                setEstimatedTimeRemaining(data.estimated_time_remaining);
              }
              
              // Handle completion and errors
              if (data.status === 'completed' && onComplete) {
                onComplete(data);
                sendNotification('Operation Complete', 'Your resume customization has been completed successfully.');
              } else if (data.status === 'error' && onError) {
                onError(new Error(data.message || 'Unknown error'));
                sendNotification('Operation Failed', data.message || 'An error occurred during processing.');
              }
            }
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          // Only increment connection attempts if the socket isn't already closed
          if (ws.readyState !== WebSocket.CLOSED) {
            setConnectionAttempts(prev => prev + 1);
          }
        };

        ws.onclose = (event) => {
          console.log(`WebSocket connection closed (code: ${event.code}, reason: ${event.reason || 'No reason provided'})`);
          setSocket(null);
          
          // Use exponential backoff for reconnection (1s, 2s, 4s)
          const backoffTime = Math.min(1000 * Math.pow(2, connectionAttempts), 8000);
          console.log(`Reconnecting in ${backoffTime}ms...`);
          
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
        console.error('Error connecting to WebSocket:', error);
        setConnectionAttempts(prev => prev + 1);
        
        // Schedule reconnection
        const backoffTime = Math.min(1000 * Math.pow(2, connectionAttempts), 8000);
        setTimeout(connectWebSocket, backoffTime);
      }
    };

    connectWebSocket();
  }, [taskId, isAuthenticated, connectionAttempts, onComplete, onError, sendNotification]);

  // Fallback to client-side simulation if WebSocket fails
  useEffect(() => {
    if (!fallbackMode || hasReceivedUpdate) return;

    const simulationInterval = setInterval(() => {
      setSimulatedProgress(prev => {
        const increment = Math.random() * 0.5 + 0.1; // 0.1 to 0.6% increment
        const newProgress = prev + increment;
        
        if (newProgress >= 100) {
          clearInterval(simulationInterval);
          setStatus('completed');
          setMessage('Operation completed successfully');
          
          if (onComplete) {
            onComplete({ task_id: taskId, status: 'completed' });
          }
          
          return 100;
        }
        
        // Simulate stage transitions
        if (newProgress < 10) {
          setCurrentStage('initialization');
          setStages(prev => ({
            ...prev,
            initialization: {
              ...prev.initialization,
              progress: newProgress / 10,
              status: 'in_progress'
            }
          }));
        } else if (newProgress < 30) {
          setCurrentStage('analysis');
          setStages(prev => ({
            ...prev,
            initialization: { ...prev.initialization, progress: 1, status: 'completed' },
            analysis: { ...prev.analysis, progress: (newProgress - 10) / 20, status: 'in_progress' }
          }));
        } else if (newProgress < 55) {
          setCurrentStage('planning');
          setStages(prev => ({
            ...prev,
            initialization: { ...prev.initialization, progress: 1, status: 'completed' },
            analysis: { ...prev.analysis, progress: 1, status: 'completed' },
            planning: { ...prev.planning, progress: (newProgress - 30) / 25, status: 'in_progress' }
          }));
        } else if (newProgress < 85) {
          setCurrentStage('implementation');
          setStages(prev => ({
            ...prev,
            initialization: { ...prev.initialization, progress: 1, status: 'completed' },
            analysis: { ...prev.analysis, progress: 1, status: 'completed' },
            planning: { ...prev.planning, progress: 1, status: 'completed' },
            implementation: { ...prev.implementation, progress: (newProgress - 55) / 30, status: 'in_progress' }
          }));
        } else {
          setCurrentStage('finalization');
          setStages(prev => ({
            ...prev,
            initialization: { ...prev.initialization, progress: 1, status: 'completed' },
            analysis: { ...prev.analysis, progress: 1, status: 'completed' },
            planning: { ...prev.planning, progress: 1, status: 'completed' },
            implementation: { ...prev.implementation, progress: 1, status: 'completed' },
            finalization: { ...prev.finalization, progress: (newProgress - 85) / 15, status: 'in_progress' }
          }));
        }
        
        // Update estimated time
        const remainingPercent = 100 - newProgress;
        const averageTimePerPercent = (Date.now() - simulationStartTime) / newProgress;
        setEstimatedTimeRemaining(remainingPercent * averageTimePerPercent / 1000);
        
        return newProgress;
      });
    }, 500);
    
    const simulationStartTime = Date.now();
    
    return () => clearInterval(simulationInterval);
  }, [fallbackMode, hasReceivedUpdate, taskId, onComplete]);

  // If fallback mode is active, use simulated progress instead of WebSocket progress
  const displayProgress = fallbackMode && !hasReceivedUpdate ? simulatedProgress : progress;

  // Get the status icon for a stage
  const getStageStatusIcon = (stage: ProgressStage) => {
    if (stage.status === 'completed') {
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    } else if (stage.status === 'in_progress') {
      return <ClockIcon className="h-5 w-5 text-blue-500 animate-pulse" />;
    } else if (stage.status === 'error') {
      return <XCircleIcon className="h-5 w-5 text-red-500" />;
    } else {
      return <InfoIcon className="h-5 w-5 text-gray-300" />;
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview" value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="details">Detailed Status</TabsTrigger>
          </TabsList>
          
          <TabsContent value="overview">
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <div className="font-semibold">{message}</div>
                <Badge
                  variant={
                    status === 'completed' ? 'success' :
                    status === 'error' ? 'destructive' :
                    status === 'initializing' ? 'outline' :
                    'default'
                  }
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </Badge>
              </div>
              
              <Progress value={displayProgress} className="h-2" />
              
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <div>{Math.round(displayProgress)}% complete</div>
                {estimatedTimeRemaining !== null && estimatedTimeRemaining > 0 && (
                  <div>Est. {formatTimeRemaining(estimatedTimeRemaining)} remaining</div>
                )}
              </div>
              
              <div className="pt-2">
                <div className="font-medium mb-2">Current stage: {currentStage}</div>
                <div className="text-sm text-muted-foreground">
                  {stages[currentStage]?.description || ''}
                </div>
              </div>
              
              {fallbackMode && !hasReceivedUpdate && (
                <div className="text-amber-500 text-xs mt-2">
                  Using estimated progress. Real-time updates unavailable.
                </div>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="details">
            <div className="space-y-4">
              {Object.entries(stages).map(([stageName, stage]) => (
                <div 
                  key={stageName}
                  className={`rounded-md p-3 ${
                    stage.status === 'completed' ? 'bg-green-50 dark:bg-green-900/20' :
                    stage.status === 'in_progress' ? 'bg-blue-50 dark:bg-blue-900/20' :
                    stage.status === 'error' ? 'bg-red-50 dark:bg-red-900/20' :
                    'bg-gray-50 dark:bg-gray-800/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      {getStageStatusIcon(stage)}
                      <div>
                        <h4 className="font-medium capitalize">{stageName}</h4>
                        <p className="text-sm text-muted-foreground">{stage.description}</p>
                      </div>
                    </div>
                    <div className="text-sm font-medium">
                      {Math.round(stage.progress * 100)}%
                    </div>
                  </div>
                  
                  {stage.message && (
                    <div className="ml-7 mt-1 text-sm">
                      {stage.message}
                    </div>
                  )}
                  
                  {currentStage === stageName && (
                    <Progress 
                      value={stage.progress * 100} 
                      className="h-1 mt-2"
                    />
                  )}
                  
                  {currentStage === stageName && stage.estimated_time_remaining !== undefined && stage.estimated_time_remaining > 0 && (
                    <div className="ml-7 mt-1 text-xs text-muted-foreground">
                      Est. {formatTimeRemaining(stage.estimated_time_remaining)} remaining for this stage
                    </div>
                  )}
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}