"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { CustomizationService, TemplateService, JobService, ResumeService, Template, CustomizationResponse, CustomizationResult } from "@/lib/client"
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
  onSuccess?: () => void
  onError?: (error: Error) => void
}

// Define customization stages
type CustomizationStage = 'evaluation' | 'planning' | 'implementation' | 'verification' | 'complete';

// Define customization level type
type CustomizationLevel = 'conservative' | 'balanced' | 'extensive';

// Define KeywordMatch interface to match the backend schema
interface KeywordMatch {
  keyword: string;
  count_in_resume?: number;
  count_in_job?: number;
  is_match?: boolean;
}

// Define customization plan interface
interface CustomizationPlan {
  summary: string;
  job_analysis: string;
  keywords_to_add: string[];
  formatting_suggestions: string[];
  recommendations: {
    section: string;
    what: string;
    why: string;
    before_text: string;
    after_text: string;
    description: string;
  }[];
}

export function CustomizeResume({ resumeId, jobId, onSuccess, onError }: CustomizeResumeProps) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [stage, setStage] = useState<CustomizationStage>('evaluation')
  const [customizationLevel, setCustomizationLevel] = useState<CustomizationLevel>('balanced')
  const [customizationPlan, setCustomizationPlan] = useState<CustomizationPlan | null>(null)
  const [customizationResult, setCustomizationResult] = useState<CustomizationResult | null>(null)
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [customizationId, setCustomizationId] = useState<string | null>(null)
  const [overallProgress, setOverallProgress] = useState<number>(0)
  const [statusMessage, setStatusMessage] = useState<string>('')
  const [currentStage, setCurrentStage] = useState<CustomizationStage>('evaluation')
  const [resume, setResume] = useState<string | null>(null)
  const [jobDescription, setJobDescription] = useState<string | null>(null)
  
  // Debug trace customization_id
  useEffect(() => {
    if (customizationId) {
      console.log('Customization ID set:', customizationId);
    }
  }, [customizationId]);

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

  // Fetch available templates
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const data = await TemplateService.getTemplates();
        setTemplates(data);
        if (data.length > 0) {
          setSelectedTemplate(data[0].id);
        }
      } catch (err) {
        console.error('Error loading templates:', err);
      }
    };
    fetchTemplates();
  }, []);

  const startCustomizationProcess = async () => {
    if (!resumeId || !jobId) return;
    try {
      setLoading(true);
      setStage('evaluation');
      console.log('Starting customization process with:', { resumeId, jobId, selectedTemplate: selectedTemplate || 'default' });
      
      let customizationResponse: CustomizationResponse;
      try {
        console.log('Before calling CustomizationService.startCustomization');
        customizationResponse = await CustomizationService.startCustomization(
          resumeId,
          jobId,
          selectedTemplate || 'default-template'
        );
        console.log('Customization response:', customizationResponse);
        setCustomizationId(customizationResponse.customization_id);
      } catch (error) {
        console.error('Failed to start customization:', error);
        setError(error instanceof Error ? error.message : 'Failed to start customization');
        setLoading(false);
        return;
      }

      // Get the latest token in case it was refreshed
      // Get the latest token and keep refreshing it
      const token = localStorage.getItem('auth_token') || '';
      // Refresh token now before establishing websocket to ensure it's fresh
      try {
        // Try to refresh the token through the auth context for long-running processes
        const authContext = (window as any).__auth_context;
        if (authContext && typeof authContext.refreshToken === 'function') {
          await authContext.refreshToken();
          console.log('Token refreshed before establishing WebSocket connection');
        }
      } catch (e) {
        console.warn('Failed to refresh token before WebSocket connection:', e);
      }
      
      // Now create the WebSocket with the latest token
      const freshToken = localStorage.getItem('auth_token') || token;
      const ws = CustomizationService.createProgressWebSocket(customizationResponse.customization_id, freshToken);

      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        setCurrentStage(data.stage);
        setStatusMessage(data.message);
        setOverallProgress(data.overall_progress);
        if (data.stage === 'verification' && data.percentage === 100) {
          ws.close();
          try {
            const result: CustomizationResult = await CustomizationService.getCustomizationResult(customizationResponse.customization_id);
            setCustomizationResult(result);
            if (result.plan) {
              setCustomizationPlan(result.plan as CustomizationPlan);
            }
          } catch (e) {
            console.error('Error fetching result:', e);
          }
          setStage('complete');
          setLoading(false);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        // Don't set error or loading state here - let the process continue
        // The backend should still be processing even if the websocket fails
        console.log('WebSocket error occurred, but customization is still running in the background');
        
        // After a few seconds, try to get the result directly instead of using websocket
        setTimeout(async () => {
          try {
            if (customizationResponse.customization_id) {
              console.log('Attempting to fetch customization result directly');
              // Attempt to get the result by direct API call
              const result = await CustomizationService.getCustomizationResult(customizationResponse.customization_id);
              if (result) {
                setCustomizationResult(result);
                if (result.plan) {
                  setCustomizationPlan(result.plan as CustomizationPlan);
                }
                setStage('complete');
                setLoading(false);
              }
            }
          } catch (e) {
            console.error('Error fetching result after websocket error:', e);
          }
        }, 10000); // Wait 10 seconds
      };
      
      ws.onclose = (event) => {
        console.log('WebSocket closed:', event);
        // Only handle unexpected closes as potential issues
        if (!event.wasClean) {
          console.log('WebSocket connection closed unexpectedly, but customization may still be running');
          
          // Similar to onerror, try to fetch the result directly
          setTimeout(async () => {
            try {
              if (customizationResponse.customization_id) {
                console.log('Attempting to fetch customization result after websocket close');
                const result = await CustomizationService.getCustomizationResult(customizationResponse.customization_id);
                if (result) {
                  setCustomizationResult(result);
                  if (result.plan) {
                    setCustomizationPlan(result.plan as CustomizationPlan);
                  }
                  setStage('complete');
                  setLoading(false);
                }
              }
            } catch (e) {
              console.error('Error fetching result after websocket close:', e);
              // Now we can set an error if direct fetching also fails
              setError('Unable to get customization status. Please check the Results page to see if customization completed.');
              setLoading(false);
            }
          }, 15000); // Wait 15 seconds
        }
      };
    } catch (err) {
      console.error('Error starting customization:', err);
      setError(err instanceof Error ? err.message : 'Failed to start customization');
      setLoading(false);
    }
  };


  // Start customization process when component mounts and data is loaded
  useEffect(() => {
    if (resumeId && jobId && resume && jobDescription && !customizationId && !loading && !error) {
      // Add a small delay to ensure we have all data loaded before starting
      const timer = setTimeout(() => {
        console.log('Starting customization with data:', {
          resumeId,
          jobId,
          resumeLength: resume?.length,
          jobDescriptionLength: jobDescription?.length
        });
        startCustomizationProcess();
      }, 500);
      
      return () => clearTimeout(timer);
    }
  }, [resumeId, jobId, resume, jobDescription, customizationId, loading, error]);

  // Format time in MM:SS format
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Handle retry
  const handleRetry = () => {
    setCustomizationPlan(null);
    setCustomizationId(null);
    setOverallProgress(0);
    setStatusMessage('');
    setStage('evaluation');
    console.log('Called handleRetry, starting customization process...');
    startCustomizationProcess();
  };

  // Handle view results (direct to customization result page)
  const handleViewResults = () => {
    if (customizationId) {
      router.push(`/customize/result?customizationId=${customizationId}`);
    }
  };
  
  // Render stage-specific content
  const renderStageContent = () => {
    if (loading) {
      return (
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-lg font-medium">{statusMessage}</span>
          </div>
          <div className="w-full h-2 bg-muted rounded">
            <div className="h-2 bg-primary rounded" style={{ width: `${overallProgress}%` }}></div>
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
    
    if (customizationPlan && stage === 'planning') {
      return (
        <div className="space-y-6">
          <div className="space-y-4 rounded-lg border p-4">
            <div className="space-y-2">
              <h3 className="text-lg font-medium">Customization Plan</h3>
              <p className="text-sm text-muted-foreground">{customizationPlan.summary}</p>
            </div>
            
            <div className="space-y-2">
              <h4 className="text-md font-medium">Job Analysis</h4>
              <p className="text-sm text-muted-foreground">
                {typeof customizationPlan.job_analysis === 'string' 
                  ? customizationPlan.job_analysis 
                  : 'The job requires skills related to relevant technologies and experience.'}
              </p>
            </div>
            
            <div className="space-y-2">
              <h4 className="text-md font-medium">Keywords to Add</h4>
              <div className="flex flex-wrap gap-2">
                {Array.isArray(customizationPlan.keywords_to_add) && customizationPlan.keywords_to_add.map((keyword, index) => (
                  <span 
                    key={index} 
                    className="px-2 py-1 text-xs bg-primary/10 rounded-full text-primary-foreground"
                  >
                    {typeof keyword === 'string' ? keyword : String(keyword)}
                  </span>
                ))}
              </div>
            </div>
            
            <div className="space-y-2">
              <h4 className="text-md font-medium">Formatting Suggestions</h4>
              <ul className="space-y-1 list-disc list-inside text-sm text-muted-foreground">
                {Array.isArray(customizationPlan.formatting_suggestions) && customizationPlan.formatting_suggestions.map((suggestion, index) => (
                  <li key={index}>{typeof suggestion === 'string' ? suggestion : String(suggestion)}</li>
                ))}
              </ul>
            </div>
            
            <div className="space-y-2">
              <h4 className="text-md font-medium">Recommended Changes</h4>
              <div className="space-y-4">
                {Array.isArray(customizationPlan.recommendations) && customizationPlan.recommendations.map((rec, index) => (
                  <div key={index} className="border rounded-md p-3 space-y-2">
                    <div className="flex justify-between items-start">
                      <span className="font-medium text-sm">{typeof rec.section === 'string' ? rec.section : 'General'}</span>
                      <span className="text-xs bg-primary/20 px-2 py-0.5 rounded-full">
                        {typeof rec.what === 'string' ? rec.what : 'Improvement'}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">{typeof rec.why === 'string' ? rec.why : 'Suggested improvement'}</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                      <div className="bg-muted/50 p-2 rounded text-xs">
                        <div className="text-muted-foreground mb-1">Before:</div>
                        <div>{typeof rec.before_text === 'string' ? rec.before_text : 'Original content'}</div>
                      </div>
                      <div className="bg-primary/5 p-2 rounded text-xs">
                        <div className="text-primary mb-1">After:</div>
                        <div>{typeof rec.after_text === 'string' ? rec.after_text : 'Improved content'}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
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
                    Moderate customization with targeted improvements for good ATS optimization
                  </p>
                </div>
                
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="extensive" id="extensive" />
                  <Label htmlFor="extensive" className="font-medium">Extensive</Label>
                  <p className="text-sm text-muted-foreground ml-2">
                    Maximum optimization with comprehensive improvements for ideal ATS performance
                  </p>
                </div>
              </RadioGroup>
            </div>
            
            <div className="flex justify-end space-x-3">
              <Button 
                variant="outline" 
                onClick={handleRetry}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Start Over
              </Button>
              
              <Button
                onClick={startCustomizationProcess}
                disabled={loading}
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Apply Customizations
              </Button>
            </div>
          </div>
        </div>
      );
    }
    
    if (stage === 'complete') {
      return (
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <FileCheck className="h-12 w-12 text-primary" />
          <div className="text-center space-y-2">
            <h3 className="text-lg font-medium">Resume Customized!</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Your resume has been successfully customized for the selected job description using the {customizationLevel} optimization level.
            </p>
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
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${['evaluation','planning','implementation','verification','complete'].indexOf(stage) >= 0 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}> 
            <Brain className="h-4 w-4" />
          </div>
          <div className={`h-1 flex-1 ${['planning','implementation','verification','complete'].indexOf(stage) >= 0 ? 'bg-primary' : 'bg-muted'}`}></div>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${['planning','implementation','verification','complete'].indexOf(stage) >= 0 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}> 
            <Sparkles className="h-4 w-4" />
          </div>
          <div className={`h-1 flex-1 ${['implementation','verification','complete'].indexOf(stage) >= 0 ? 'bg-primary' : 'bg-muted'}`}></div>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${['implementation','verification','complete'].indexOf(stage) >= 0 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
            <FileCheck className="h-4 w-4" />
          </div>
          <div className={`h-1 flex-1 ${['verification','complete'].indexOf(stage) >= 0 ? 'bg-primary' : 'bg-muted'}`}></div>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${['verification','complete'].indexOf(stage) >= 0 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}> 
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
      {stage === 'complete' && customizationId && (
        <CardFooter className="flex justify-center">
          <Button onClick={handleViewResults} className="w-full sm:w-auto">
            View Customized Resume
          </Button>
        </CardFooter>
      )}
    </Card>
  )
}