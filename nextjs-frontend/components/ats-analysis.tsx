"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { InfoIcon } from "lucide-react"

interface ATSAnalysisProps {
  resumeId: string
  jobId: string
  onAnalysisComplete?: (result: any) => void
}

export function ATSAnalysis({ resumeId, jobId, onAnalysisComplete }: ATSAnalysisProps) {
  const router = useRouter()

  // Redirect to customization which now includes ATS analysis
  useEffect(() => {
    if (resumeId && jobId) {
      // Auto-redirect to the Claude Code customization page
      router.push(`/customize?resumeId=${resumeId}&jobId=${jobId}&mode=claude`)
    }
  }, [resumeId, jobId, router])

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>ATS Analysis with Claude</CardTitle>
        <CardDescription>
          ATS analysis is now integrated with the customization process
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Alert className="mb-6">
          <InfoIcon className="h-4 w-4" />
          <AlertTitle>ATS analysis has been upgraded</AlertTitle>
          <AlertDescription>
            The standalone ATS analysis has been integrated with our new Claude-powered resume customization. This provides a more comprehensive analysis and improvement process in one step.
          </AlertDescription>
        </Alert>
        
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <p className="text-muted-foreground mb-6">
            Redirecting to customization page...
          </p>
          <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
        </div>
      </CardContent>
      <CardFooter className="flex justify-center">
        <Button asChild className="w-full sm:w-auto">
          <Link href={`/customize?resumeId=${resumeId}&jobId=${jobId}&mode=claude`}>
            Continue to Resume Customization
          </Link>
        </Button>
      </CardFooter>
    </Card>
  )
}