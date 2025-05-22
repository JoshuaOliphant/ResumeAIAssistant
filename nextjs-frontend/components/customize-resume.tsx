"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ProgressTracker } from "@/components/progress-tracker"
import { ResumeService, JobService, Resume, JobDescription, ResumeVersion } from "@/lib/client"
import { Play, AlertCircle, CheckCircle } from "lucide-react"

export interface CustomizeResumeProps {
  resumeId: string
  jobId: string
  onSuccess?: (version: ResumeVersion) => void
  onError?: (error: string) => void
}

export function CustomizeResume({ resumeId, jobId, onSuccess, onError }: CustomizeResumeProps) {
  const [isCustomizing, setIsCustomizing] = useState(false)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [resume, setResume] = useState<Resume | null>(null)
  const [job, setJob] = useState<JobDescription | null>(null)

  // Load resume and job data when component mounts
  React.useEffect(() => {
    const loadData = async () => {
      try {
        const [resumeData, jobData] = await Promise.all([
          ResumeService.getResume(resumeId),
          JobService.getJobDescription(jobId)
        ])
        setResume(resumeData)
        setJob(jobData)
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load data"
        setError(errorMessage)
        onError?.(errorMessage)
      }
    }
    
    if (resumeId && jobId) {
      loadData()
    }
  }, [resumeId, jobId, onError])

  const handleStartCustomization = async () => {
    if (!resume || !job) {
      setError("Resume or job data not loaded")
      return
    }

    try {
      setIsCustomizing(true)
      setError(null)

      // Call the Claude Code API to start customization
      const response = await fetch('/api/v1/claude-code/customize-resume', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          resume_id: resumeId,
          job_id: jobId,
        }),
      })

      if (!response.ok) {
        throw new Error(`Customization failed: ${response.statusText}`)
      }

      const result = await response.json()
      setCurrentTaskId(result.task_id)

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to start customization"
      setError(errorMessage)
      setIsCustomizing(false)
      onError?.(errorMessage)
    }
  }

  const handleCustomizationComplete = (result: any) => {
    setIsCustomizing(false)
    setCurrentTaskId(null)
    
    // The result should contain the customized resume version
    if (result && result.version) {
      onSuccess?.(result.version)
    } else {
      // If no version in result, we need to refresh the resume to get the latest version
      ResumeService.getResume(resumeId).then((updatedResume) => {
        onSuccess?.(updatedResume.current_version)
      }).catch((err) => {
        const errorMessage = err instanceof Error ? err.message : "Failed to get updated resume"
        setError(errorMessage)
        onError?.(errorMessage)
      })
    }
  }

  const handleCustomizationError = (error: string) => {
    setIsCustomizing(false)
    setCurrentTaskId(null)
    setError(error)
    onError?.(error)
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  if (!resume || !job) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center">Loading resume and job data...</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Resume and Job Overview */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Resume</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-medium">{resume.filename}</p>
            <p className="text-sm text-muted-foreground">
              Current version: {resume.current_version?.version_number || 1}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Job Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-medium">{job.title}</p>
            {job.company && (
              <p className="text-sm text-muted-foreground">{job.company}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Customization Control */}
      <Card>
        <CardHeader>
          <CardTitle>Claude Code Resume Customization</CardTitle>
          <CardDescription>
            This will analyze your resume against the job description and create a customized version 
            that better matches the requirements. This process typically takes about 5 minutes.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!isCustomizing ? (
            <Button 
              onClick={handleStartCustomization}
              size="lg"
              className="w-full"
            >
              <Play className="mr-2 h-4 w-4" />
              Start Customization
            </Button>
          ) : (
            <div className="space-y-4">
              {currentTaskId && (
                <ProgressTracker
                  taskId={currentTaskId}
                  onComplete={handleCustomizationComplete}
                  onError={handleCustomizationError}
                />
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}