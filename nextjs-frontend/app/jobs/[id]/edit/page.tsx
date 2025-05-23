"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { JobService, JobDescription } from "@/lib/client"
import { JobDescriptionForm } from "@/components/job-description-form"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Loader2 } from "lucide-react"

export default function JobEditPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter()
  const [job, setJob] = useState<JobDescription | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadJob() {
      try {
        const resolvedParams = await params
        const jobData = await JobService.getJob(resolvedParams.id)
        setJob(jobData)
      } catch (err) {
        console.error("Error loading job:", err)
        setError("Failed to load job description. It may have been deleted or is unavailable.")
      } finally {
        setIsLoading(false)
      }
    }

    loadJob()
  }, [params])

  // Handle successful job update
  const handleSuccess = (updatedJob: JobDescription) => {
    setTimeout(() => {
      router.push(`/jobs/${updatedJob.id}`)
    }, 2000)
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-16 flex justify-center items-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="container mx-auto py-8">
        <Link href="/jobs">
          <Button variant="outline" className="mb-8">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Jobs
          </Button>
        </Link>
        
        <div className="bg-destructive/10 text-destructive p-4 rounded-md">
          {error || "Job description not found"}
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 max-w-3xl">
      <Link href={`/jobs/${job.id}`}>
        <Button variant="outline" className="mb-8">
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Job Details
        </Button>
      </Link>
      
      <h1 className="text-3xl font-bold mb-8">Edit Job Description</h1>
      
      <JobDescriptionForm 
        initialData={{
          id: job.id,
          title: job.title,
          company: job.company,
          description: job.description
        }} 
        onSuccess={handleSuccess} 
      />
    </div>
  )
}