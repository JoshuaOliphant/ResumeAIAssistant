"use client"

import { useState } from "react"
import { useSearchParams } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { SelectResume } from "@/components/select-resume"
import { SelectJob } from "@/components/select-job"
import { ATSAnalysis } from "@/components/ats-analysis"
import { Resume, JobDescription } from "@/lib/client"

export default function ATSPage() {
  const searchParams = useSearchParams()
  const resumeIdFromUrl = searchParams.get('resumeId')
  const jobIdFromUrl = searchParams.get('jobId')
  
  const [selectedResumeId, setSelectedResumeId] = useState<string>(resumeIdFromUrl || "")
  const [selectedJobId, setSelectedJobId] = useState<string>(jobIdFromUrl || "")
  
  // Handle resume change from SelectResume component
  const handleResumeChange = (resume: Resume | null) => {
    // This is handled by the selectedResumeId state already
  }
  
  // Handle job change from SelectJob component
  const handleJobChange = (job: JobDescription | null) => {
    // This is handled by the selectedJobId state already
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-2">ATS Compatibility Analysis</h1>
      <p className="text-muted-foreground mb-8">
        Analyze how well your resume matches the job description and get tailored improvement suggestions.
      </p>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle>Select Resume</CardTitle>
            <CardDescription>
              Choose a resume to analyze
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SelectResume 
              value={selectedResumeId} 
              onValueChange={setSelectedResumeId}
              onResumeChange={handleResumeChange}
            />
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Select Job</CardTitle>
            <CardDescription>
              Choose a job description to analyze against
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SelectJob 
              value={selectedJobId}
              onValueChange={setSelectedJobId}
              onJobChange={handleJobChange}
            />
          </CardContent>
        </Card>
      </div>
      
      <ATSAnalysis resumeId={selectedResumeId} jobId={selectedJobId} />
    </div>
  )
}