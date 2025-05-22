"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { JobService, ResumeService, ResumeVersion, ClaudeCodeService } from "@/lib/client"
import { API_BASE_URL } from "@/lib/api-config"
import { Loader2, FileCheck, RefreshCw, AlertCircle, Check, ChevronRight, Sparkles, Brain } from "lucide-react"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { getCustomizationLevelPrompt } from "@/lib/prompts"
import { ProgressTracker } from "./progress-tracker"
import { addNotification } from "./notification-badge"

export interface CustomizeResumeProps {
  resumeId: string
  jobId: string
  onSuccess?: (customizedVersion: ResumeVersion) => void
  onError?: (error: Error) => void
}

// Define customization stages
type CustomizationStage = 'preparation' | 'implementation' | 'complete';

// Define customization level type
type CustomizationLevel = 'conservative' | 'balanced' | 'extensive';

export function CustomizeResume({ resumeId, jobId, onSuccess, onError }: CustomizeResumeProps) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stage, setStage] = useState<CustomizationStage>('preparation')
  const [customizationLevel, setCustomizationLevel] = useState<CustomizationLevel>('balanced')
  const [customizedVersion, setCustomizedVersion] = useState<ResumeVersion | null>(null)
  const [resume, setResume] = useState<string | null>(null)
  const [jobDescription, setJobDescription] = useState<string | null>(null)
  const [operationId, setOperationId] = useState<string | null>(null)
  const [useRealTimeProgress, setUseRealTimeProgress] = useState(true)
  const [customizationSummary, setCustomizationSummary] = useState<string | null>(null)

  // Load resume and job description
  useEffect(() => {
    const loadData = async () => {
      try {
        // Fetch resume and job description
        const resumeData = await ResumeService.getResume(resumeId);
        const jobData = await JobService.getJob(jobId);
        
        setResume(resumeData.current_version.content);
        setJobDescription(jobData.description);
      } catch (err) {
        console.error("Error loading resume or job data:", err);
        setError(err instanceof Error ? err.message : "Failed to load resume or job data");
      }
    };
    
    if (resumeId && jobId) {
      loadData();
    }
  }, [resumeId, jobId]);

  // Initialize operation ID for progress tracking
  const initializeOperation = async () => {
    try {
      // Make a POST request to create a new progress tracker
      const response = await fetch(`${API_BASE_URL}/progress/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to initialize progress tracking:', response.status, response.statusText, errorText);
        console.error('API URL attempted:', `${API_BASE_URL}/progress/create`);
        console.error('Auth token present:', !!localStorage.getItem('auth_token'));
        console.error('Falling back to client-side simulation');
        setUseRealTimeProgress(false);
        return null;
      }
      
      const data = await response.json();
      console.log('Progress tracking initialized with ID:', data.task_id);
      
      // Wait a short delay to ensure the task is registered before we start polling
      await new Promise(resolve => setTimeout(resolve, 500));
      
      return data.task_id;
    } catch (error) {
      console.error('Error initializing progress tracking (network/other):', error);
      console.error('This likely means the progress endpoint is unreachable or there is a network issue');
      setUseRealTimeProgress(false);
      return null;
    }
  };

  // Function to prepare for resume customization with Claude Code
  const prepareCustomization = async () => {
    if (!resume || !jobDescription) {
      setError("Resume and job description data is missing");
      return;
    }
    
    try {
      // Initialize progress tracking
      const taskId = await initializeOperation();
      setOperationId(taskId);
      
      setLoading(true);
      setStage('preparation');
      setError(null);
      
      // Skip analysis phase and move directly to implementation
      console.log("Preparing to customize resume with Claude Code...");
      console.log(`Using resume ID: ${resumeId}, job ID: ${jobId}, operation ID: ${taskId}`);
      
      // Proceed to implementation directly
      setStage('implementation');
      implementCustomization();
    } catch (err) {
      console.error("Error preparing customization:", err);
      setError(err instanceof Error ? err.message : "Failed to prepare customization");
      setLoading(false);
    }
  };

  // Function to implement customization with Claude Code
  const implementCustomization = async () => {
    if (!resumeId || !jobId) {
      setError("Resume ID and Job ID are required");
      return;
    }
    
    try {
      // Make sure we have an operation ID for tracking
      if (!operationId) {
        const taskId = await initializeOperation();
        setOperationId(taskId);
      }
      
      setLoading(true);
      setStage('implementation');
      setError(null);
      
      // Add the level-specific prompt additions
      const levelPrompt = getCustomizationLevelPrompt(customizationLevel);
      console.log("Using customization level:", customizationLevel, levelPrompt);
      
      // Call the Claude Code API to customize resume
      console.log("Starting Claude Code resume customization:", resumeId, jobId, "with level:", customizationLevel);
      
      // Pass the customization level to the API with the operation ID header and a longer timeout
      const result = await ClaudeCodeService.customizeResume(
        resumeId,
        jobId,
        customizationLevel,
        operationId ? { 
          headers: { 'X-Operation-ID': operationId },
          timeout: 1800  // Use 30-minute timeout (1800 seconds)
        } : { timeout: 1800 }
      );
      
      // Log the raw result for debugging
      console.log("Claude Code customization raw result:", result);
      console.log("Result type:", typeof result);
      console.log("Result keys:", Object.keys(result));
      console.log("Content field:", result.customized_resume || result.content);
      
      // Process the result immediately (don't rely only on WebSocket completion)
      processCustomizationResult(result);
    } catch (err) {
      console.error("Error customizing resume with Claude Code:", err);
      setError(err instanceof Error ? err.message : "Failed to customize resume");
      
      // Add error notification
      addNotification({
        title: "Customization Error",
        message: err instanceof Error ? err.message : "Failed to customize resume"
      });
      
      // Call onError callback if provided
      if (onError && err instanceof Error) {
        onError(err);
      }
    }
  };
  
  // Process the customization result (called either directly or via WebSocket completion)
  const processCustomizationResult = (result: any) => {
    if (!result) {
      console.error('Cannot process null or undefined result');
      return;
    }
    
    console.log('Processing customization result:', result);
    
    try {
      // Create a valid customizedVersion object even if the structure from API is different
      const versionObj = {
        id: result.id || result.customization_id || 'latest',
        resume_id: resumeId,
        content: result.customized_resume || result.content,
        version_number: 1,
        is_customized: true,
        job_description_id: jobId,
        created_at: new Date().toISOString()
      };
      
      console.log('Created version object:', versionObj);
      setCustomizedVersion(versionObj);
      
      // Store customization summary if available 
      if (result.customization_summary) {
        setCustomizationSummary(result.customization_summary);
      }
      
      setStage('complete');
      setLoading(false);
      
      // Add notification
      addNotification({
        title: "Resume Customization Complete",
        message: "Your resume has been successfully customized for this job using Claude Code."
      });
      
      // Call onSuccess callback if provided
      if (onSuccess) {
        onSuccess(versionObj);
      }
      
      // Automatically navigate to results page after a short delay
      setTimeout(() => {
        console.log('Auto-navigating to results page');
        handleViewResults();
      }, 1500);
    } catch (e) {
      console.error('Error processing customization result:', e);
      setError(e instanceof Error ? e.message : "Failed to process customization result");
    }
  };

  // Start customization process when component mounts and data is loaded
  useEffect(() => {
    if (resumeId && jobId && resume && jobDescription && !customizedVersion && !loading && !error) {
      prepareCustomization();
    }
  }, [resumeId, jobId, resume, jobDescription, customizedVersion, loading, error]);

  // Format time in MM:SS format
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Handle retry
  const handleRetry = () => {
    setCustomizedVersion(null);
    setCustomizationSummary(null);
    setStage('preparation');
    prepareCustomization();
  };

  // Handle view results (direct to customization result page)
  const handleViewResults = () => {
    if (customizedVersion) {
      // Check if we have a valid version ID, if not use a fallback approach
      const versionId = customizedVersion.id || 'latest';
      console.log('Navigating to results page with params:', { resumeId, jobId, versionId });
      router.push(`/customize/result?resumeId=${resumeId}&jobId=${jobId}&versionId=${versionId}`);
    } else {
      console.error('Cannot navigate to results: customizedVersion is null or undefined');
    }
  };
  
  // Render stage-specific content
  const renderStageContent = () => {
    if (loading) {
      // Use real-time progress tracker if available
      if (operationId && useRealTimeProgress) {
        return (
          <ProgressTracker 
            taskId={operationId}
            title="Resume Customization Progress"
            description="Track the progress of your resume customization with Claude Code"
            onComplete={(result) => {
              console.log('ProgressTracker onComplete called with result:', result);
              
              // If we have result data, process it directly
              if (result && (result.result || result.data)) {
                console.log('Processing result from WebSocket completion');
                processCustomizationResult(result.result || result.data);
              } 
              // Otherwise just update the stage if we already have a customized version
              else if (stage === 'implementation' && customizedVersion) {
                console.log('WebSocket completion received, transitioning to complete stage');
                setStage('complete');
              }
              // If we don't have a customized version yet, fetch the resume data
              else if (stage === 'implementation' && !customizedVersion) {
                console.log('WebSocket completion received but no customized version, attempting to fetch resume');
                // This is a fallback - try to get the latest version from the API
                ResumeService.getResume(resumeId)
                  .then(resumeData => {
                    console.log('Fetched resume data:', resumeData);
                    if (resumeData && resumeData.current_version) {
                      setCustomizedVersion(resumeData.current_version);
                      setStage('complete');
                    }
                  })
                  .catch(err => console.error('Error fetching resume after completion:', err));
              }
            }}
            onError={(error) => {
              console.log('ProgressTracker onError called with error:', error);
              if (!customizedVersion) {
                setError(error.message);
              }
            }}
            showNotifications={true}
          />
        );
      }
      
      // Fallback to static progress display if real-time tracking isn't available
      return (
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-lg font-medium">
              {stage === 'preparation' && "Preparing to customize your resume..."}
              {stage === 'implementation' && "Customizing your resume with Claude Code..."}
            </span>
          </div>
          
          <div className="space-y-2 rounded-lg bg-muted p-4 text-sm">
            <p className="font-medium">What&apos;s happening:</p>
            <ul className="space-y-1 list-disc list-inside text-muted-foreground">
              {stage === 'preparation' && (
                <>
                  <li>Loading your resume content</li>
                  <li>Preparing job description</li>
                  <li>Initializing Claude Code</li>
                </>
              )}
              {stage === 'implementation' && (
                <>
                  <li>Using Claude Code to customize your resume</li>
                  <li>Optimizing content for job relevance</li>
                  <li>Enhancing sections to highlight your qualifications</li>
                  <li>Maintaining authentic representation</li>
                  <li>Finalizing improvements</li>
                </>
              )}
            </ul>
          </div>
        </div>
      );
    }
    
    if (error) {
      return (
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <AlertCircle className="h-12 w-12 text-destructive" />
          <div className="text-center space-y-2">
            <h3 className="text-lg font-medium">Customization Error</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              {error}
            </p>
          </div>
          <Button onClick={handleRetry} variant="outline" className="mt-4">
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
        </div>
      );
    }
    
    if (stage === 'preparation') {
      return (
        <div className="space-y-6">
          <div className="space-y-4 rounded-lg border p-4">
            <div className="space-y-2">
              <h3 className="text-lg font-medium">Customize Your Resume with Claude Code</h3>
              <p className="text-sm text-muted-foreground">
                Claude Code will analyze your resume and the job description to create a tailored version of your resume that highlights your relevant skills and experience.
              </p>
            </div>
            
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-medium mb-2">Customization Level</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Choose how extensively you want to customize your resume. All changes will maintain authenticity.
                </p>
                
                <RadioGroup 
                  value={customizationLevel} 
                  onValueChange={(value) => setCustomizationLevel(value as CustomizationLevel)}
                  className="space-y-3"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="conservative" id="conservative" />
                    <Label htmlFor="conservative" className="font-medium">Conservative</Label>
                    <p className="text-sm text-muted-foreground ml-2">
                      Minimal changes focusing only on essential keywords and formatting
                    </p>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="balanced" id="balanced" />
                    <Label htmlFor="balanced" className="font-medium">Balanced</Label>
                    <p className="text-sm text-muted-foreground ml-2">
                      Moderate customization with targeted improvements for good job relevance
                    </p>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="extensive" id="extensive" />
                    <Label htmlFor="extensive" className="font-medium">Extensive</Label>
                    <p className="text-sm text-muted-foreground ml-2">
                      Maximum optimization with comprehensive improvements for ideal job matching
                    </p>
                  </div>
                </RadioGroup>
              </div>
              
              <div className="flex justify-end space-x-3">
                <Button 
                  onClick={implementCustomization}
                  disabled={loading}
                >
                  <Sparkles className="mr-2 h-4 w-4" />
                  Customize with Claude Code
                </Button>
              </div>
            </div>
          </div>
        </div>
      );
    }
    
    if (customizedVersion && stage === 'complete') {
      return (
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <FileCheck className="h-12 w-12 text-primary" />
          <div className="text-center space-y-2">
            <h3 className="text-lg font-medium">Resume Customized!</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Your resume has been successfully customized for the selected job description using Claude Code with {customizationLevel} optimization level.
            </p>
            
            {customizationSummary && (
              <div className="mt-4 p-4 bg-muted rounded-lg text-left">
                <h4 className="font-medium mb-2">Customization Summary</h4>
                <p className="text-sm">{customizationSummary}</p>
              </div>
            )}
          </div>
        </div>
      );
    }
    
    // Default loading state while fetching initial data
    return (
      <div className="flex flex-col items-center justify-center py-8 space-y-4">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <div className="text-center space-y-2">
          <h3 className="text-lg font-medium">Preparing Customization</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Loading resume and job data...
          </p>
        </div>
      </div>
    );
  };
  
  // Render progress steps
  const renderProgressSteps = () => {
    return (
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center w-full">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${stage === 'preparation' || stage === 'implementation' || stage === 'complete' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
            <Brain className="h-4 w-4" />
          </div>
          <div className={`h-1 flex-1 ${stage === 'implementation' || stage === 'complete' ? 'bg-primary' : 'bg-muted'}`}></div>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${stage === 'implementation' || stage === 'complete' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
            <Sparkles className="h-4 w-4" />
          </div>
          <div className={`h-1 flex-1 ${stage === 'complete' ? 'bg-primary' : 'bg-muted'}`}></div>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${stage === 'complete' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
            <Check className="h-4 w-4" />
          </div>
        </div>
      </div>
    );
  };
  
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Customizing Your Resume</CardTitle>
        <CardDescription>Our AI will analyze your resume and customize it for the job description</CardDescription>
      </CardHeader>
      <CardContent>
        {renderProgressSteps()}
        {renderStageContent()}
      </CardContent>
      {customizedVersion && (
        <CardFooter className="flex justify-center">
          <Button onClick={handleViewResults} className="w-full sm:w-auto">
            View Customized Resume
          </Button>
        </CardFooter>
      )}
    </Card>
  )
}