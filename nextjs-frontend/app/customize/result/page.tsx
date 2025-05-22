"use client"

import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChevronLeft, FileCheck } from "lucide-react"

export default function CustomizationResultPage() {
  const searchParams = useSearchParams()
  const resumeId = searchParams.get('resumeId')
  const jobId = searchParams.get('jobId')
  const versionId = searchParams.get('versionId')
  
  // Enhanced debug logging for navigation parameters
  useEffect(() => {
    console.log("Result page loaded with params:", { 
      resumeId, 
      jobId, 
      versionId,
      hasAllParams: Boolean(resumeId && versionId),
      fullUrl: typeof window !== 'undefined' ? window.location.href : 'N/A'
    });
    
    // Track parameter changes
    if (!resumeId) {
      console.warn("Missing resumeId parameter in result page");
    }
    
    if (!versionId) {
      console.warn("Missing versionId parameter in result page");
    }
    
    if (!jobId) {
      console.warn("Missing jobId parameter in result page (not critical)");
    }
  }, [resumeId, jobId, versionId]);
  
  // Check if all required params are present
  const hasRequiredParams = Boolean(resumeId && versionId)
  
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">Customized Resume</h1>
          <p className="text-muted-foreground">Review and download your customized resume</p>
        </div>
        
        <div className="flex gap-2">
          <Link href={`/customize?resumeId=${resumeId}&jobId=${jobId}`} passHref>
            <Button variant="outline">
              <ChevronLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
          
          <Link href="/analyze" passHref>
            <Button>
              <FileCheck className="mr-2 h-4 w-4" />
              Analyze ATS Match
            </Button>
          </Link>
        </div>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Customization Results</CardTitle>
          <CardDescription>
            Resume customization results will be displayed here.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-muted-foreground mb-4">
              Customization results functionality is being updated for the new Claude Code integration.
            </p>
            {resumeId && (
              <p className="text-sm text-muted-foreground mb-4">
                Resume ID: {resumeId}
                {versionId && <><br />Version: {versionId}</>}
              </p>
            )}
            <div className="flex gap-2 justify-center">
              <Link href="/resumes" passHref>
                <Button variant="outline">
                  View Resumes
                </Button>
              </Link>
              <Link href="/customize" passHref>
                <Button>
                  Start New Customization
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}