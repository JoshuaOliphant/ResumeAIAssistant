"use client"

import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ChevronLeft, Download, FileText, Eye, Loader2, GitCompare } from "lucide-react"
import { EnhancedDiffView } from "@/components/enhanced-diff-view"
import { MarkdownRenderer } from "@/components/markdown-renderer"

interface TaskResult {
  customized_resume?: string;
  customization_summary?: string;
  original_resume?: string;
  [key: string]: any;
}

export default function CustomizationResultPage() {
  const searchParams = useSearchParams()
  const taskId = searchParams.get('taskId')
  const resumeId = searchParams.get('resumeId')
  const jobId = searchParams.get('jobId')
  
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TaskResult | null>(null)
  
  useEffect(() => {
    if (!taskId) {
      setError("No task ID provided")
      setLoading(false)
      return
    }
    
    const fetchResult = async () => {
      try {
        const response = await fetch(`/api/v1/progress/${taskId}/status`)
        if (!response.ok) {
          throw new Error("Failed to fetch task status")
        }
        
        const data = await response.json()
        
        if (data.status === 'completed' && data.result) {
          setResult(data.result)
        } else if (data.status === 'error') {
          setError(data.error || "Task failed")
        } else {
          setError("Task is not completed yet")
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load results")
      } finally {
        setLoading(false)
      }
    }
    
    fetchResult()
  }, [taskId])
  
  const handleDownload = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
  
  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading results...</span>
          </CardContent>
        </Card>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <div className="flex gap-2">
          <Link href="/customize" passHref>
            <Button variant="outline">
              <ChevronLeft className="mr-2 h-4 w-4" />
              Back to Customize
            </Button>
          </Link>
        </div>
      </div>
    )
  }
  
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Customization Complete</h1>
          <p className="text-muted-foreground">Your resume has been customized for the job</p>
        </div>
        
        <Link href="/customize" passHref>
          <Button variant="outline">
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
      </div>
      
      <Tabs defaultValue="resume" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="resume">
            <FileText className="mr-2 h-4 w-4" />
            Customized Resume
          </TabsTrigger>
          <TabsTrigger value="diff">
            <GitCompare className="mr-2 h-4 w-4" />
            Compare Changes
          </TabsTrigger>
          <TabsTrigger value="summary">
            <Eye className="mr-2 h-4 w-4" />
            Summary Report
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="resume" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Your Customized Resume</CardTitle>
                <Button 
                  onClick={() => handleDownload(
                    result?.customized_resume || '', 
                    'customized_resume.md'
                  )}
                  size="sm"
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
              </div>
              <CardDescription>
                This resume has been optimized for the job requirements
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MarkdownRenderer 
                content={result?.customized_resume || "No resume content available"} 
                className="p-6"
              />
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="diff" className="space-y-4">
          {result?.original_resume && result?.customized_resume ? (
            <EnhancedDiffView 
              original={result.original_resume}
              customized={result.customized_resume}
              title="Resume Comparison"
              jobTitle={jobId ? `Job ${jobId}` : undefined}
            />
          ) : (
            <Alert>
              <AlertDescription>
                Original resume content not available for comparison.
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>
        
        <TabsContent value="summary" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Customization Summary</CardTitle>
                <Button 
                  onClick={() => handleDownload(
                    result?.customization_summary || '', 
                    'customization_summary.md'
                  )}
                  size="sm"
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </Button>
              </div>
              <CardDescription>
                Detailed report of changes and recommendations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MarkdownRenderer 
                content={result?.customization_summary || "No summary available"} 
                className="p-6"
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      
      <div className="flex gap-2 justify-center">
        <Link href="/resumes" passHref>
          <Button variant="outline">
            View All Resumes
          </Button>
        </Link>
        <Link href="/customize" passHref>
          <Button>
            Customize Another Resume
          </Button>
        </Link>
      </div>
    </div>
  )
}