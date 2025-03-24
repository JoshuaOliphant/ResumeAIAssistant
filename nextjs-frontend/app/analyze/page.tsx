"use client"

import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { ATSService, JobService, ResumeService, JobDescription, Resume } from "@/lib/client"
import { Loader2, RefreshCw, PlusCircle } from "lucide-react"
import { SelectResume } from "@/components/select-resume"
import { SelectJob } from "@/components/select-job"
import { ATSAnalysis } from "@/components/ats-analysis"

// Define form schema with zod
const formSchema = z.object({
  resumeText: z.string().min(10, {
    message: "Resume must be at least 10 characters",
  }),
  jobDescription: z.string().min(10, {
    message: "Job description must be at least 10 characters",
  }),
})

export default function AnalyzePage() {
  const searchParams = useSearchParams()
  const resumeIdFromUrl = searchParams.get('resumeId')
  const jobIdFromUrl = searchParams.get('jobId')
  
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [selectedResumeId, setSelectedResumeId] = useState<string>(resumeIdFromUrl || "")
  const [selectedJobId, setSelectedJobId] = useState<string>(jobIdFromUrl || "")
  const [selectedResumeContent, setSelectedResumeContent] = useState<string>("")
  const [selectedJobContent, setSelectedJobContent] = useState<string>("")
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      resumeText: "",
      jobDescription: "",
    },
  })
  
  // Check URL parameters on component mount
  useEffect(() => {
    const resumeId = searchParams.get('resumeId');
    const jobId = searchParams.get('jobId');
    
    if (resumeId) {
      setSelectedResumeId(resumeId);
    }
    
    if (jobId) {
      setSelectedJobId(jobId);
    }
  }, [searchParams]);

  // Fetch resume content when selected
  useEffect(() => {
    async function fetchSelectedResumeContent() {
      if (selectedResumeId) {
        try {
          const resume = await ResumeService.getResume(selectedResumeId)
          setSelectedResumeContent(resume.current_version.content)
        } catch (error) {
          console.error("Error fetching resume content:", error)
        }
      } else {
        setSelectedResumeContent("")
      }
    }
    
    fetchSelectedResumeContent()
  }, [selectedResumeId])
  
  // Fetch job description content when selected
  useEffect(() => {
    async function fetchSelectedJobContent() {
      if (selectedJobId) {
        try {
          const job = await JobService.getJob(selectedJobId)
          setSelectedJobContent(job.description)
        } catch (error) {
          console.error("Error fetching job description content:", error)
        }
      } else {
        setSelectedJobContent("")
      }
    }
    
    fetchSelectedJobContent()
  }, [selectedJobId])
  
  // Auto-analyze when both resume and job are loaded from URL parameters
  useEffect(() => {
    const resumeId = searchParams.get('resumeId');
    const jobId = searchParams.get('jobId');
    
    // Only auto-analyze if both parameters are provided and content is loaded
    if (resumeId && jobId && selectedResumeContent && selectedJobContent && !isAnalyzing && !analysisResult) {
      console.log('Auto-analyzing with loaded content');
      analyzeSavedItems();
    }
  }, [selectedResumeContent, selectedJobContent, searchParams, isAnalyzing, analysisResult]);
  
  async function onSubmit(values: z.infer<typeof formSchema>) {
    try {
      setIsAnalyzing(true)
      
      // Call the API to analyze the resume against the job description
      const result = await ATSService.analyzeContent(
        values.resumeText,
        values.jobDescription
      )
      
      setAnalysisResult(result)
    } catch (error) {
      console.error("Error analyzing resume:", error)
    } finally {
      setIsAnalyzing(false)
    }
  }
  
  async function analyzeSavedItems() {
    if (!selectedResumeContent || !selectedJobContent) {
      return
    }
    
    try {
      setIsAnalyzing(true)
      
      // Call the API to analyze the selected resume against the selected job description
      const result = await ATSService.analyzeContent(
        selectedResumeContent,
        selectedJobContent
      )
      
      setAnalysisResult(result)
    } catch (error) {
      console.error("Error analyzing saved items:", error)
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Handle resume change from SelectResume component
  const handleResumeChange = (resume: Resume | null) => {
    if (resume) {
      setSelectedResumeContent(resume.current_version.content)
    } else {
      setSelectedResumeContent("")
    }
  }
  
  // Handle job change from SelectJob component
  const handleJobChange = (job: JobDescription | null) => {
    if (job) {
      setSelectedJobContent(job.description)
    } else {
      setSelectedJobContent("")
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Analyze Resume</h1>
      
      <Tabs defaultValue={resumeIdFromUrl ? "saved" : "manual"} className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="manual">Enter Resume & Job</TabsTrigger>
          <TabsTrigger value="saved">Use Saved Data</TabsTrigger>
        </TabsList>
        
        <TabsContent value="manual">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
              <Card>
                <CardHeader>
                  <CardTitle>Resume Information</CardTitle>
                  <CardDescription>
                    Enter your resume text or paste Markdown content
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <FormField
                    control={form.control}
                    name="resumeText"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Resume Text</FormLabel>
                        <FormControl>
                          <textarea
                            className="w-full min-h-[200px] p-3 rounded-md border border-input bg-background"
                            placeholder="# John Doe
                            
## Education
- BS in Computer Science, Example University (2018-2022)

## Experience
- Software Engineer, Example Corp (2022-Present)
  - Developed feature X that increased efficiency by 30%
  - Led a team of 5 engineers on Project Y
                            "
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Enter your resume in Markdown format
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Job Description</CardTitle>
                  <CardDescription>
                    Enter the job description you want to target
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <FormField
                    control={form.control}
                    name="jobDescription"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Job Description</FormLabel>
                        <FormControl>
                          <textarea
                            className="w-full min-h-[200px] p-3 rounded-md border border-input bg-background"
                            placeholder="We are seeking a Software Engineer with expertise in React, Node.js, and cloud technologies. The ideal candidate will have 3+ years of experience building web applications..."
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Paste the full job description
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
                <CardFooter>
                  <Button type="submit" disabled={isAnalyzing}>
                    {isAnalyzing ? "Analyzing..." : "Analyze Resume"}
                  </Button>
                </CardFooter>
              </Card>
            </form>
          </Form>
        </TabsContent>
        
        <TabsContent value="saved">
          <Card>
            <CardHeader>
              <CardTitle>Use Saved Data</CardTitle>
              <CardDescription>
                Select from your saved resumes and job descriptions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <SelectResume 
                value={selectedResumeId} 
                onValueChange={setSelectedResumeId}
                onResumeChange={handleResumeChange}
                disabled={isAnalyzing}
              />
              
              <SelectJob 
                value={selectedJobId}
                onValueChange={setSelectedJobId}
                onJobChange={handleJobChange}
                disabled={isAnalyzing}
              />

              <div className="flex justify-end">
                <Button
                  onClick={analyzeSavedItems}
                  disabled={!selectedResumeId || !selectedJobId || isAnalyzing}
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    "Analyze Match"
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      
      {analysisResult && (
        <div className="mt-8">
          <ATSAnalysis 
            resumeId={selectedResumeId} 
            jobId={selectedJobId} 
            onAnalysisComplete={setAnalysisResult}
          />
        </div>
      )}
    </div>
  )
}