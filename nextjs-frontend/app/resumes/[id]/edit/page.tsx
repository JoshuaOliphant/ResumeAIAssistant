"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { ResumeForm } from "@/components/resume-form"
import { ResumeService } from "@/lib/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function EditResumePage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter()
  const [resume, setResume] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [resumeId, setResumeId] = useState<string | null>(null)
  
  useEffect(() => {
    async function loadResume() {
      try {
        const resolvedParams = await params
        setResumeId(resolvedParams.id)
        const data = await ResumeService.getResume(resolvedParams.id)
        setResume({
          id: data.id,
          title: data.title,
          content: data.current_version.content
        })
      } catch (err) {
        console.error("Error loading resume:", err)
        setError("Failed to load resume. It may have been deleted or you don't have permission to view it.")
      } finally {
        setIsLoading(false)
      }
    }
    
    loadResume()
  }, [params])
  
  const handleSuccess = () => {
    // Navigate back to the resume detail page
    if (resumeId) {
      router.push(`/resumes/${resumeId}`)
    }
  }
  
  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 flex flex-col items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-primary mb-4" />
        <p className="text-lg text-muted-foreground">Loading resume...</p>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        
        <Button onClick={() => router.push('/resumes')}>
          Back to Resumes
        </Button>
      </div>
    )
  }
  
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">Edit Resume</h1>
      <p className="text-muted-foreground mb-8">
        Make changes to your resume content or title.
      </p>
      
      {resume && <ResumeForm initialData={resume} onSuccess={handleSuccess} />}
    </div>
  )
}