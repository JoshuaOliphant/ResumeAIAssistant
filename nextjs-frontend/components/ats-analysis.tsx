"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { ATSService, ATSAnalysisResult } from "@/lib/client"
import { MatchScore } from "@/components/ats-match-score"
import { KeywordMatch } from "@/components/ats-keyword-match"
import { MissingKeywords } from "@/components/ats-missing-keywords"
import { ImprovementSuggestions } from "@/components/ats-improvement-suggestions"

interface ATSAnalysisProps {
  resumeId: string
  jobId: string
  onAnalysisComplete?: (result: ATSAnalysisResult) => void
}

export function ATSAnalysis({ resumeId, jobId, onAnalysisComplete }: ATSAnalysisProps) {
  const router = useRouter()
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] = useState<ATSAnalysisResult | null>(null)

  // Perform analysis when component mounts or when ids change
  useEffect(() => {
    if (resumeId && jobId) {
      performAnalysis()
    }
  }, [resumeId, jobId])
  
  // Function to adapt backend response to frontend format
  function adaptAPIResponse(apiResponse: any): ATSAnalysisResult {
    // Extract matching keywords and format them for frontend
    const matchingKeywords = Array.isArray(apiResponse.matching_keywords)
      ? apiResponse.matching_keywords.map((item: any) => {
          if (typeof item === 'object' && item !== null) {
            return {
              keyword: item.keyword,
              count: item.count_in_resume || 1,
              count_in_resume: item.count_in_resume || 1,
              count_in_job: item.count_in_job || 1,
              is_match: item.is_match !== undefined ? item.is_match : true
            };
          }
          return { keyword: String(item), count: 1, count_in_resume: 1, count_in_job: 1, is_match: true };
        })
      : [];
    
    // Extract missing keywords - keep the rich structure if available, otherwise use simple strings
    const missingKeywords = Array.isArray(apiResponse.missing_keywords)
      ? apiResponse.missing_keywords.map((item: any) => {
          if (typeof item === 'object' && item !== null && item.keyword) {
            return item;
          }
          return { 
            keyword: String(item), 
            count_in_resume: 0, 
            count_in_job: 1, 
            is_match: false 
          };
        })
      : [];
    
    // Format improvements
    let improvementSuggestions: Record<string, string[]> = {};
    const improvements = apiResponse.improvements || [];
    
    if (Array.isArray(improvements)) {
      // Group improvements by category
      improvements.forEach((item: any) => {
        if (typeof item === 'object' && item !== null && item.category && item.suggestion) {
          if (!improvementSuggestions[item.category]) {
            improvementSuggestions[item.category] = [];
          }
          improvementSuggestions[item.category].push(item.suggestion);
        }
      });
    } else if (typeof apiResponse.improvement_suggestions === 'object') {
      // If it's already in the right format
      improvementSuggestions = apiResponse.improvement_suggestions;
    }
    
    // Extract section scores
    const sectionScores = Array.isArray(apiResponse.section_scores)
      ? apiResponse.section_scores
      : [];
    
    // Create the adapted result object
    return {
      id: apiResponse.id || 'temp-id',
      resume_id: apiResponse.resume_id,
      job_description_id: apiResponse.job_description_id,
      match_score: apiResponse.match_score,
      matching_keywords: matchingKeywords,
      missing_keywords: Array.isArray(missingKeywords) 
        ? missingKeywords.map(mk => typeof mk === 'string' ? mk : mk.keyword) 
        : [],
      improvement_suggestions: improvementSuggestions,
      
      // New fields
      improvements: improvements,
      job_type: apiResponse.job_type || 'default',
      section_scores: sectionScores,
      confidence: apiResponse.confidence || 'medium',
      keyword_density: apiResponse.keyword_density || 0,
      
      // Add rich versions of data for the updated components
      matching_keywords_rich: matchingKeywords,
      missing_keywords_rich: missingKeywords,
    };
  }

  async function performAnalysis() {
    if (!resumeId || !jobId) {
      setError("Both resume and job description are required")
      return
    }
    
    try {
      setError(null)
      setIsAnalyzing(true)
      
      // Call the API to analyze the resume against the job description
      const apiResponse = await ATSService.analyzeResume(resumeId, jobId)
      
      // Adapt the API response to the frontend format
      const result = adaptAPIResponse(apiResponse)
      
      setAnalysisResult(result)
      
      // Notify parent component if callback provided
      if (onAnalysisComplete) {
        onAnalysisComplete(result)
      }
    } catch (error) {
      console.error("Error analyzing resume:", error)
      // Check for ApiError specifically (from client.ts)
      if (error && typeof error === 'object' && 'status' in error && 'message' in error) {
        const apiError = error as { status: number; message: string; data?: any };
        setError(`Failed to analyze resume (${apiError.status}): ${apiError.message}`)
        console.error("API Error details:", apiError.data);
      } else if (error instanceof Error) {
        // Regular Error object
        setError(`Failed to analyze resume: ${error.message || "Unknown error occurred"}`)
      } else {
        setError("Failed to analyze resume. Please try again.")
      }
    } finally {
      setIsAnalyzing(false)
    }
  }

  if (isAnalyzing) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Analyzing Resume</CardTitle>
          <CardDescription>
            Please wait while we analyze your resume against the job description
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <p className="text-muted-foreground">
              Analyzing compatibility, keywords, and skills match...
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="w-full border-destructive/50">
        <CardHeader>
          <CardTitle>Analysis Error</CardTitle>
          <CardDescription>
            There was a problem analyzing your resume
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-destructive/10 text-destructive p-4 rounded-md">
            <p>{error}</p>
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={performAnalysis}>Try Again</Button>
        </CardFooter>
      </Card>
    )
  }

  if (!analysisResult) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>ATS Analysis</CardTitle>
          <CardDescription>
            Select a resume and job description to get started
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-muted-foreground mb-4">
              No analysis available. Please select a resume and job description.
            </p>
            <Button onClick={performAnalysis} disabled={!resumeId || !jobId}>
              Analyze Compatibility
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>ATS Analysis Results</CardTitle>
        <CardDescription>
          Here&apos;s how your resume matches the job description
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-8">
          <div className="flex flex-col sm:flex-row justify-between gap-4 items-start">
            <MatchScore 
              score={analysisResult.match_score} 
              confidence={analysisResult.confidence} 
            />
            
            {analysisResult.job_type && (
              <div className="px-4 py-3 bg-muted rounded-lg">
                <p className="text-sm font-medium">Job Type</p>
                <p className="text-lg capitalize">{analysisResult.job_type.replace('_', ' ')}</p>
                {analysisResult.keyword_density !== undefined && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Keyword Density: {analysisResult.keyword_density.toFixed(1)}%
                  </p>
                )}
              </div>
            )}
          </div>
          
          {analysisResult.section_scores && analysisResult.section_scores.length > 0 && (
            <div className="border rounded-lg p-4">
              <h3 className="font-medium text-lg mb-3">Section Analysis</h3>
              <div className="space-y-3">
                {analysisResult.section_scores.map((section, index) => (
                  <div key={index} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{section.section}</span>
                      <span className="font-medium">{section.score}%</span>
                    </div>
                    <Progress 
                      value={section.score} 
                      className="h-2"
                      indicatorClassName={
                        section.score >= 70 ? "bg-emerald-500" : 
                        section.score >= 50 ? "bg-amber-500" : 
                        "bg-red-500"
                      }
                    />
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                Section scores show how well each part of your resume matches job requirements.
              </p>
            </div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <KeywordMatch keywords={
              (analysisResult.matching_keywords_rich || []).map(item => ({
                keyword: item.keyword,
                count: item.count_in_resume || 1
              }))
            } />
            <MissingKeywords keywords={
              Array.isArray(analysisResult.missing_keywords_rich) 
                ? analysisResult.missing_keywords_rich.map(item => 
                    typeof item === 'string' ? item : item.keyword
                  )
                : (analysisResult.missing_keywords || [])
            } />
          </div>
          
          <ImprovementSuggestions suggestions={analysisResult.improvement_suggestions} />
        </div>
      </CardContent>
      <CardFooter className="flex justify-between flex-col sm:flex-row gap-4">
        <Button variant="outline" onClick={performAnalysis} className="w-full sm:w-auto">
          Refresh Analysis
        </Button>
        <Button asChild className="w-full sm:w-auto">
          <Link href={`/customize?resumeId=${resumeId}&jobId=${jobId}`}>
            Customize Resume
          </Link>
        </Button>
      </CardFooter>
    </Card>
  )
}