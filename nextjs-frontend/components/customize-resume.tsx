"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { ATSService, CustomizationService, JobService, ResumeService, ResumeVersion } from "@/lib/client"
import { API_BASE_URL } from "@/lib/api-config"
import { Loader2, FileCheck, RefreshCw, AlertCircle, Check, ChevronRight, Sparkles, Brain } from "lucide-react"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { getCustomizationLevelPrompt } from "@/lib/prompts"

export interface CustomizeResumeProps {
  resumeId: string
  jobId: string
  onSuccess?: (customizedVersion: ResumeVersion) => void
  onError?: (error: Error) => void
}

// Define customization stages
type CustomizationStage = 'analysis' | 'plan' | 'implementation' | 'complete';

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
  const [progress, setProgress] = useState(0)
  const [stage, setStage] = useState<CustomizationStage>('analysis')
  const [customizationLevel, setCustomizationLevel] = useState<CustomizationLevel>('balanced')
  const [estimatedTime, setEstimatedTime] = useState(60) // In seconds
  const [timeRemaining, setTimeRemaining] = useState(60) // In seconds
  const [customizedVersion, setCustomizedVersion] = useState<ResumeVersion | null>(null)
  const [customizationPlan, setCustomizationPlan] = useState<CustomizationPlan | null>(null)
  const [resume, setResume] = useState<string | null>(null)
  const [jobDescription, setJobDescription] = useState<string | null>(null)
  const [progressTimer, setProgressTimer] = useState<NodeJS.Timeout | null>(null)

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

  // Function to update progress bar
  useEffect(() => {
    if (loading && progressTimer === null) {
      // Set estimated time based on current stage
      let stageTime = 60; // default
      
      switch (stage) {
        case 'analysis':
          stageTime = 20;
          break;
        case 'plan':
          stageTime = 30;
          break;
        case 'implementation':
          stageTime = 45;
          break;
      }
      
      setEstimatedTime(stageTime);
      setTimeRemaining(stageTime);
      setProgress(0);
      
      // Set up progress timer - increments every second
      const timer = setInterval(() => {
        setProgress((prevProgress) => {
          // Cap progress at 95% until we get real results
          const newProgress = prevProgress + (100 / stageTime);
          return Math.min(newProgress, 95);
        });
        
        setTimeRemaining((prevTime) => {
          const newTime = prevTime - 1;
          return Math.max(newTime, 0);
        });
      }, 1000);
      
      setProgressTimer(timer);
    }
    
    return () => {
      if (progressTimer) {
        clearInterval(progressTimer);
        setProgressTimer(null);
      }
    };
  }, [loading, stage, progressTimer]);

  // Function to analyze resume and create a customization plan
  const analyzeResume = async () => {
    if (!resume || !jobDescription) {
      setError("Resume and job description data is missing");
      return;
    }
    
    try {
      setLoading(true);
      setStage('analysis');
      setError(null);
      
      // Use the proper ATS analysis endpoint
      console.log("Analyzing resume and job description...");
      
      try {
        // Step 1: Basic keyword analysis using ATSService
        console.log("Step 1: Performing basic keyword analysis...");
        console.log(`Analyzing resume ID: ${resumeId}, job ID: ${jobId}`);
        const analysisResult = await ATSService.analyzeResume(resumeId, jobId);
        console.log("Basic analysis result:", analysisResult);
        
        // Step 2: Move to the plan stage with AI-enhanced analysis
        setStage('plan');
        
        // Reset progress for the next stage
        if (progressTimer) {
          clearInterval(progressTimer);
          setProgressTimer(null);
        }
        
        // Step 3: Use enhanced AI analysis to create a better customization plan
        console.log("Step 2: Generating AI-enhanced customization plan...");
        try {
          // Try to use the AI-enhanced customization plan generator
          const enhancedPlan = await CustomizationService.generateCustomizationPlan(
            resumeId,
            jobId,
            customizationLevel,
            analysisResult
          );
          
          console.log("Enhanced plan generated:", enhancedPlan);
          
          // Set the enhanced customization plan
          setCustomizationPlan(enhancedPlan);
          setLoading(false);
        } catch (enhancedPlanError) {
          console.error("Error generating enhanced plan:", enhancedPlanError);
          console.log("Falling back to basic plan generation...");
          
          // Extract keywords and format them properly for display as fallback
          const keywordsToAdd = Array.isArray(analysisResult.missing_keywords_rich) 
            ? analysisResult.missing_keywords_rich.map(item => {
                if (typeof item === 'object' && item !== null) {
                  // Type assertion to KeywordMatch
                  const keywordItem = item as unknown as KeywordMatch;
                  return typeof keywordItem.keyword === 'string' ? keywordItem.keyword : String(keywordItem.keyword || '');
                }
                return String(item || '');
              })
            : (Array.isArray(analysisResult.missing_keywords) 
                ? analysisResult.missing_keywords.map(item => {
                    if (typeof item === 'object' && item !== null) {
                      // Type assertion to KeywordMatch
                      const keywordItem = item as unknown as KeywordMatch;
                      if (typeof keywordItem.keyword === 'string') {
                        return keywordItem.keyword;
                      }
                      // Otherwise stringify but remove curly braces
                      const str = JSON.stringify(item);
                      return str.replace(/[{}]/g, '').replace(/"/g, '');
                    }
                    return String(item || '');
                  })
                : []);
          
          // Create a basic customization plan from the analysis result as fallback
          const fallbackPlan = {
            summary: `Your resume has a ${analysisResult.match_score || 0}% match with the job description. We've identified opportunities to improve this match.`,
            job_analysis: `The job requires skills related to: ${Array.isArray(keywordsToAdd) && keywordsToAdd.length > 0 ? keywordsToAdd.slice(0, 5).map(kw => typeof kw === 'string' ? kw : String(kw || '')).join(', ') : 'relevant skills'}`,
            keywords_to_add: keywordsToAdd,
            formatting_suggestions: Array.isArray(analysisResult.improvements) 
              ? analysisResult.improvements
                  .filter(imp => 
                    typeof imp === 'object' && imp !== null &&
                    typeof imp.category === 'string' && typeof imp.suggestion === 'string' &&
                    (imp.category.includes("Format") || 
                    imp.category.includes("Structure") || 
                    imp.suggestion.includes("format"))
                  )
                  .map(imp => imp.suggestion)
              : [
                  "Add more specific technical skills mentioned in the job description",
                  "Quantify your achievements with metrics",
                  "Use more powerful action verbs to describe your accomplishments"
                ],
            recommendations: Array.isArray(analysisResult.improvements)
              ? analysisResult.improvements
                  .filter(imp => typeof imp === 'object' && imp !== null)
                  .map(imp => ({
                    section: typeof imp.category === 'string' ? imp.category : 'General',
                    what: typeof imp.priority === 'number' 
                      ? (imp.priority === 1 ? "Critical" : imp.priority === 2 ? "Important" : "Helpful")
                      : "Helpful",
                    why: typeof imp.suggestion === 'string' ? imp.suggestion : 'Improvement suggestion',
                    before_text: "Original content will be improved",
                    after_text: "Customized with job-specific details",
                    description: typeof imp.suggestion === 'string' ? imp.suggestion : 'Improvement suggestion'
                  }))
              : []
          };
          
          // Set fallback customization plan
          setCustomizationPlan(fallbackPlan);
          setLoading(false);
        }
      } catch (analysisError) {
        // If initial analysis fails, log the error and proceed directly to implementation
        console.error("Error during analysis stage:", analysisError);
        console.log("Proceeding directly to implementation stage...");
        
        // Skip the plan stage
        setStage('implementation');
        implementCustomization();
      }
    } catch (err) {
      console.error("Error analyzing resume:", err);
      setError(err instanceof Error ? err.message : "Failed to analyze resume");
      setLoading(false);
    }
  };

  // Function to implement customization plan
  const implementCustomization = async () => {
    if (!resumeId || !jobId) {
      setError("Resume ID and Job ID are required");
      return;
    }
    
    try {
      setLoading(true);
      setStage('implementation');
      setError(null);
      
      // Add the level-specific prompt additions
      const levelPrompt = getCustomizationLevelPrompt(customizationLevel);
      console.log("Using customization level:", customizationLevel, levelPrompt);
      
      // Call the API to customize resume
      console.log("Starting resume customization:", resumeId, jobId, "with level:", customizationLevel);
      console.log("Using customization plan:", customizationPlan);
      
      // Pass the customization level and plan to the API
      const result = await CustomizationService.customizeResume(
        resumeId,
        jobId,
        customizationLevel,
        customizationPlan
      );
      console.log("Customization result:", result);
      
      // Clear the timer
      if (progressTimer) {
        clearInterval(progressTimer);
        setProgressTimer(null);
      }
      
      // Set progress to 100%
      setProgress(100);
      setTimeRemaining(0);
      
      // Store the result
      setCustomizedVersion(result);
      setStage('complete');
      
      // Call onSuccess callback if provided
      if (onSuccess) {
        onSuccess(result);
      }
    } catch (err) {
      console.error("Error customizing resume:", err);
      setError(err instanceof Error ? err.message : "Failed to customize resume");
      
      // Call onError callback if provided
      if (onError && err instanceof Error) {
        onError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  // Start customization process when component mounts and data is loaded
  useEffect(() => {
    if (resumeId && jobId && resume && jobDescription && !customizationPlan && !customizedVersion && !loading && !error) {
      analyzeResume();
    }
  }, [resumeId, jobId, resume, jobDescription, customizationPlan, customizedVersion, loading, error]);

  // Format time in MM:SS format
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Handle retry
  const handleRetry = () => {
    setCustomizationPlan(null);
    setCustomizedVersion(null);
    setStage('analysis');
    analyzeResume();
  };

  // Handle view results (direct to customization result page)
  const handleViewResults = () => {
    if (customizedVersion) {
      router.push(`/customize/result?resumeId=${resumeId}&jobId=${jobId}&versionId=${customizedVersion.id}`);
    }
  };
  
  // Render stage-specific content
  const renderStageContent = () => {
    if (loading) {
      return (
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-lg font-medium">
              {stage === 'analysis' && "Analyzing your resume and job match..."}
              {stage === 'plan' && "Creating customization plan..."}
              {stage === 'implementation' && "Implementing customizations..."}
            </span>
          </div>
          
          <div className="space-y-2">
            <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
              <div 
                className="h-full bg-primary transition-all duration-300 ease-in-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Progress: {Math.round(progress)}%</span>
              <span>Estimated time: {formatTime(timeRemaining)}</span>
            </div>
          </div>
          
          <div className="space-y-2 rounded-lg bg-muted p-4 text-sm">
            <p className="font-medium">What&apos;s happening:</p>
            <ul className="space-y-1 list-disc list-inside text-muted-foreground">
              {stage === 'analysis' && (
                <>
                  <li>Analyzing your resume content</li>
                  <li>Identifying key skills and experiences</li>
                  <li>Extracting job requirements</li>
                  <li>Determining keyword matches</li>
                </>
              )}
              {stage === 'plan' && (
                <>
                  <li>Creating customization strategy</li>
                  <li>Identifying optimal improvements</li>
                  <li>Preparing section-by-section plan</li>
                  <li>Determining key keywords to add</li>
                </>
              )}
              {stage === 'implementation' && (
                <>
                  <li>Applying customization to resume</li>
                  <li>Optimizing content for ATS compatibility</li>
                  <li>Enhancing relevant sections</li>
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
    
    if (customizationPlan && stage === 'plan') {
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
                onClick={implementCustomization}
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
    
    if (customizedVersion && stage === 'complete') {
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
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${stage === 'analysis' || stage === 'plan' || stage === 'implementation' || stage === 'complete' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
            <Brain className="h-4 w-4" />
          </div>
          <div className={`h-1 flex-1 ${stage === 'plan' || stage === 'implementation' || stage === 'complete' ? 'bg-primary' : 'bg-muted'}`}></div>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${stage === 'plan' || stage === 'implementation' || stage === 'complete' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
            <Sparkles className="h-4 w-4" />
          </div>
          <div className={`h-1 flex-1 ${stage === 'implementation' || stage === 'complete' ? 'bg-primary' : 'bg-muted'}`}></div>
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