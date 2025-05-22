import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Progress } from './ui/progress';
import { Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface ProgressTrackerProps {
  taskId: string;
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
}

export function ProgressTracker({ taskId, onComplete, onError }: ProgressTrackerProps) {
  const [status, setStatus] = useState<string>('initializing');
  const [progress, setProgress] = useState<number>(0);
  const [message, setMessage] = useState<string>('Starting customization...');

  useEffect(() => {
    if (!taskId) return;

    // Simple progress simulation
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 95) return prev; // Don't go to 100% until we know it's done
        return prev + Math.random() * 2; // Gradual progress increase
      });
    }, 2000);

    // Check for completion every 10 seconds
    const checkCompletion = async () => {
      try {
        const response = await fetch(`/api/v1/progress/${taskId}/status`);
        if (response.ok) {
          const data = await response.json();
          setStatus(data.status);
          
          if (data.status === 'completed') {
            setProgress(100);
            setMessage('Customization completed successfully!');
            if (onComplete) onComplete(data);
          } else if (data.status === 'error') {
            setMessage('An error occurred during customization');
            if (onError) onError(data.error || 'Unknown error');
          }
        }
      } catch (error) {
        console.error('Error checking completion:', error);
      }
    };

    const completionInterval = setInterval(checkCompletion, 10000);
    
    // Initial check
    checkCompletion();

    return () => {
      clearInterval(progressInterval);
      clearInterval(completionInterval);
    };
  }, [taskId, onComplete, onError]);

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'error':
        return 'Error';
      default:
        return 'Processing';
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {getStatusIcon()}
          Resume Customization Progress
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{getStatusText()}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="w-full" />
          </div>
          
          <div className="text-sm text-muted-foreground">
            {message}
          </div>

          {status !== 'completed' && status !== 'error' && (
            <div className="text-center">
              <div className="inline-flex items-center gap-2 text-sm text-muted-foreground bg-muted/50 rounded-full px-4 py-2">
                <Clock className="h-4 w-4" />
                <span>This typically takes about 5 minutes to complete</span>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}