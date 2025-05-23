"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { JobDescription, Resume, ResumeVersion } from "@/lib/client"
import { SelectResume } from "@/components/select-resume"
import { SelectJob } from "@/components/select-job"
import { CustomizeResume } from "@/components/customize-resume"
import { ChevronLeft } from "lucide-react"

export default function CustomizePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const resumeIdFromUrl = searchParams.get('resumeId')
  const jobIdFromUrl = searchParams.get('jobId')
  
  const [selectedResumeId, setSelectedResumeId] = useState<string>(resumeIdFromUrl || "")
  const [selectedJobId, setSelectedJobId] = useState<string>(jobIdFromUrl || "")
  const [isReady, setIsReady] = useState<boolean>(false)
  const [customizedVersion, setCustomizedVersion] = useState<ResumeVersion | null>(null)
  
  // Check URL parameters on component mount
  useEffect(() => {
    const resumeId = searchParams.get('resumeId')
    const jobId = searchParams.get('jobId')
    
    if (resumeId) {
      setSelectedResumeId(resumeId)
    }
    
    if (jobId) {
      setSelectedJobId(jobId)
    }
    
    // If both IDs are provided, set isReady to true
    if (resumeId && jobId) {
      setIsReady(true)
    }
  }, [searchParams])
  
  // Handle resume selection
  const handleResumeChange = (resume: Resume | null) => {
    // Resume selection logic if needed
  }
  
  // Handle job selection
  const handleJobChange = (job: JobDescription | null) => {
    // Job selection logic if needed
  }
  
  // Handle start customization
  const handleStartCustomization = () => {
    setIsReady(true)
  }
  
  // Handle customization success
  const handleCustomizationSuccess = (taskId: string) => {
    console.log("Customization success, received taskId:", taskId);
    
    // Redirect to result page with task ID
    const redirectUrl = `/customize/result?taskId=${taskId}&resumeId=${selectedResumeId}&jobId=${selectedJobId}`;
    console.log("Redirecting to:", redirectUrl);
    router.push(redirectUrl)
  }
  
  // Go back to selection
  const handleBackToSelection = () => {
    setIsReady(false)
  }
  
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold">Customize Resume</h1>
      
      {!isReady ? (
        <Card>
          <CardHeader>
            <CardTitle>Select Resume and Job</CardTitle>
            <CardDescription>
              Choose the resume you want to customize and the job description to target
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <SelectResume 
              value={selectedResumeId} 
              onValueChange={setSelectedResumeId}
              onResumeChange={handleResumeChange}
            />
            
            <SelectJob 
              value={selectedJobId}
              onValueChange={setSelectedJobId}
              onJobChange={handleJobChange}
            />
            
            <div className="flex justify-end">
              <Button
                onClick={handleStartCustomization}
                disabled={!selectedResumeId || !selectedJobId}
              >
                Customize Resume
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <Button 
            variant="ghost" 
            onClick={handleBackToSelection}
            className="mb-4"
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back to Selection
          </Button>
          
          <CustomizeResume 
            resumeId={selectedResumeId}
            jobId={selectedJobId}
            onSuccess={handleCustomizationSuccess}
          />
        </>
      )}
    </div>
  )
}