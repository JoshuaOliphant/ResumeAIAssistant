"use client"

import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ATSService, JobService, ResumeService, JobDescription, Resume } from "@/lib/client"
import { Loader2, RefreshCw, PlusCircle } from "lucide-react"

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
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [isLoadingSaved, setIsLoadingSaved] = useState(false)
  const [savedResumes, setSavedResumes] = useState<Resume[]>([])
  const [savedJobs, setSavedJobs] = useState<JobDescription[]>([])
  const [selectedResumeId, setSelectedResumeId] = useState<string>("")
  const [selectedJobId, setSelectedJobId] = useState<string>("")
  const [selectedResumeContent, setSelectedResumeContent] = useState<string>("")
  const [selectedJobContent, setSelectedJobContent] = useState<string>("")
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      resumeText: "",
      jobDescription: "",
    },
  })
  
  // Load saved resumes and job descriptions
  useEffect(() => {
    async function loadSavedData() {
      setIsLoadingSaved(true)
      try {
        const [resumesResponse, jobsResponse] = await Promise.all([
          ResumeService.getResumes(),
          JobService.getJobs()
        ])
        
        setSavedResumes(resumesResponse)
        setSavedJobs(jobsResponse)
      } catch (error) {
        console.error("Error loading saved data:", error)
      } finally {
        setIsLoadingSaved(false)
      }
    }
    
    loadSavedData()
  }, [])

  // Fetch resume and job description content when selected
  useEffect(() => {
    async function fetchSelectedResumeContent() {
      if (selectedResumeId) {
        try {
          const resume = await ResumeService.getResume(selectedResumeId)
          setSelectedResumeContent(resume.current_version.content)
        } catch (error) {
          console.error("Error fetching resume content:", error)
        }
      }
    }
    
    fetchSelectedResumeContent()
  }, [selectedResumeId])
  
  useEffect(() => {
    async function fetchSelectedJobContent() {
      if (selectedJobId) {
        try {
          const job = await JobService.getJob(selectedJobId)
          setSelectedJobContent(job.description)
        } catch (error) {
          console.error("Error fetching job description content:", error)
        }
      }
    }
    
    fetchSelectedJobContent()
  }, [selectedJobId])
  
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

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Analyze Resume</h1>
      
      <Tabs defaultValue="manual" className="w-full">
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
              {isLoadingSaved ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <label className="text-sm font-medium">Select Resume</label>
                      <Link href="/resumes/new">
                        <Button variant="outline" size="sm">
                          <PlusCircle className="h-4 w-4 mr-2" />
                          New Resume
                        </Button>
                      </Link>
                    </div>
                    {savedResumes.length === 0 ? (
                      <div className="text-center p-4 border rounded-md bg-muted/20">
                        <p className="text-muted-foreground text-sm">
                          No saved resumes found. Create a new resume to get started.
                        </p>
                      </div>
                    ) : (
                      <Select value={selectedResumeId} onValueChange={setSelectedResumeId}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a resume" />
                        </SelectTrigger>
                        <SelectContent>
                          {savedResumes.map((resume) => (
                            <SelectItem key={resume.id} value={resume.id}>
                              {resume.title}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <label className="text-sm font-medium">Select Job Description</label>
                      <Link href="/jobs/new">
                        <Button variant="outline" size="sm">
                          <PlusCircle className="h-4 w-4 mr-2" />
                          New Job
                        </Button>
                      </Link>
                    </div>
                    {savedJobs.length === 0 ? (
                      <div className="text-center p-4 border rounded-md bg-muted/20">
                        <p className="text-muted-foreground text-sm">
                          No saved job descriptions found. Create a new job description to get started.
                        </p>
                      </div>
                    ) : (
                      <Select value={selectedJobId} onValueChange={setSelectedJobId}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select a job description" />
                        </SelectTrigger>
                        <SelectContent>
                          {savedJobs.map((job) => (
                            <SelectItem key={job.id} value={job.id}>
                              {job.title} {job.company ? `- ${job.company}` : ''}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>

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
                </>
              )}
            </CardContent>
            <CardFooter className="flex justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setIsLoadingSaved(true)
                  Promise.all([
                    ResumeService.getResumes(),
                    JobService.getJobs()
                  ]).then(([resumes, jobs]) => {
                    setSavedResumes(resumes)
                    setSavedJobs(jobs)
                  }).catch(error => {
                    console.error("Error refreshing data:", error)
                  }).finally(() => {
                    setIsLoadingSaved(false)
                  })
                }}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>
      
      {analysisResult && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription>
              Here&apos;s how your resume matches the job description
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <h3 className="font-medium mb-2">Match Score</h3>
                <div className="w-full bg-secondary rounded-full h-4">
                  <div 
                    className="bg-primary h-4 rounded-full" 
                    style={{ width: `${analysisResult.match_score}%` }}
                  ></div>
                </div>
                <p className="text-right text-sm text-muted-foreground mt-1">
                  {analysisResult.match_score}%
                </p>
              </div>
              
              <div>
                <h3 className="font-medium mb-2">Matching Keywords</h3>
                <div className="flex flex-wrap gap-2">
                  {analysisResult.matching_keywords.map((item: any, index: number) => (
                    <div key={index} className="bg-primary/10 text-primary px-2 py-1 rounded-full text-sm">
                      {item.keyword} ({item.count})
                    </div>
                  ))}
                </div>
              </div>
              
              <div>
                <h3 className="font-medium mb-2">Missing Keywords</h3>
                <div className="flex flex-wrap gap-2">
                  {analysisResult.missing_keywords.map((keyword: string, index: number) => (
                    <div key={index} className="bg-destructive/10 text-destructive px-2 py-1 rounded-full text-sm">
                      {keyword}
                    </div>
                  ))}
                </div>
              </div>
              
              <div>
                <h3 className="font-medium mb-2">Improvement Suggestions</h3>
                <div className="space-y-4">
                  {Object.entries(analysisResult.improvement_suggestions).map(([category, suggestions]: [string, any]) => (
                    <div key={category} className="border rounded-lg p-4">
                      <h4 className="font-medium mb-2">{category}</h4>
                      <ul className="list-disc pl-5 space-y-1">
                        {suggestions.map((suggestion: string, index: number) => (
                          <li key={index} className="text-sm">{suggestion}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button className="w-full">Customize Resume</Button>
          </CardFooter>
        </Card>
      )}
    </div>
  )
}