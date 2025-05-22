"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { ResumeService } from "@/lib/client"
import { Loader2, AlertCircle, Edit, ArrowLeft, FileText, Download } from "lucide-react"
import { format } from "date-fns"

export default function ResumePage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [resume, setResume] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    async function loadResume() {
      try {
        const data = await ResumeService.getResume(params.id)
        setResume(data)
      } catch (err) {
        console.error("Error loading resume:", err)
        setError("Failed to load resume. It may have been deleted or you don't have permission to view it.")
      } finally {
        setIsLoading(false)
      }
    }
    
    loadResume()
  }, [params.id])
  
  const handleExportPdf = async () => {
    try {
      const blob = await ResumeService.exportResumeToPdf(resume.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${resume.title.replace(/\s+/g, "_")}.pdf`
      document.body.appendChild(a)
      a.click()
      URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error("Error exporting resume:", err)
      alert("Failed to export resume. Please try again.")
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
        
        <Button asChild>
          <Link href="/resumes">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Resumes
          </Link>
        </Button>
      </div>
    )
  }
  
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <Button variant="ghost" className="mb-6" asChild>
        <Link href="/resumes">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Resumes
        </Link>
      </Button>
      
      {resume && (
        <>
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold">{resume.title}</h1>
            <div className="flex space-x-3">
              <Button variant="outline" onClick={handleExportPdf}>
                <Download className="w-4 h-4 mr-2" />
                Export PDF
              </Button>
              <Button asChild>
                <Link href={`/resumes/${resume.id}/edit`}>
                  <Edit className="w-4 h-4 mr-2" />
                  Edit
                </Link>
              </Button>
            </div>
          </div>
          
          <div className="text-sm text-muted-foreground mb-8">
            <div>Created: {format(new Date(resume.created_at), "PPP")}</div>
            <div>Last Updated: {format(new Date(resume.updated_at), "PPP")}</div>
          </div>
          
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center text-lg">
                <FileText className="w-5 h-5 mr-2" />
                Resume Content
              </CardTitle>
              <CardDescription>
                {resume.current_version.is_customized
                  ? "This resume has been customized for a specific job"
                  : "Original resume content"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="border rounded-md p-6 font-mono whitespace-pre-wrap break-words">
                {resume.current_version.content}
              </div>
            </CardContent>
            <CardFooter className="flex justify-between">
              <div className="text-sm text-muted-foreground">
                Version {resume.current_version.version_number}
              </div>
              <Button variant="outline" asChild>
                <Link href={`/customize?resumeId=${resume.id}`}>Customize Resume</Link>
              </Button>
            </CardFooter>
          </Card>
        </>
      )}
    </div>
  )
}