"use client"

import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { CustomizationResult } from "@/components/customization-result"
import { ChevronLeft, FileCheck } from "lucide-react"

export default function CustomizationResultPage() {
  const searchParams = useSearchParams()
  const resumeId = searchParams.get('resumeId')
  const jobId = searchParams.get('jobId')
  const versionId = searchParams.get('versionId')
  
  // Log params for debugging
  useEffect(() => {
    console.log("Result page params:", { resumeId, jobId, versionId });
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
      
      {hasRequiredParams ? (
        <CustomizationResult
          resumeId={resumeId as string}
          versionId={versionId as string}
        />
      ) : (
        <div className="bg-muted p-8 rounded-md text-center">
          <h2 className="text-xl font-semibold mb-2">Missing Information</h2>
          <p className="text-muted-foreground mb-4">
            Resume ID and Version ID are required to view customization results.
          </p>
          <Link href="/customize" passHref>
            <Button>Go to Customize Resume</Button>
          </Link>
        </div>
      )}
    </div>
  )
}