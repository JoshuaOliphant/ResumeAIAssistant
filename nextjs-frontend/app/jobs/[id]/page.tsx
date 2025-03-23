"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { JobService, JobDescription } from "@/lib/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Pencil, ArrowLeft, Trash } from "lucide-react"
import { format } from "date-fns"

export default function JobViewPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [job, setJob] = useState<JobDescription | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadJob() {
      try {
        const jobData = await JobService.getJob(params.id)
        setJob(jobData)
      } catch (err) {
        console.error("Error loading job:", err)
        setError("Failed to load job description. It may have been deleted or is unavailable.")
      } finally {
        setIsLoading(false)
      }
    }

    loadJob()
  }, [params.id])

  const handleDelete = async () => {
    if (!job) return
    
    if (confirm("Are you sure you want to delete this job description?")) {
      try {
        await JobService.deleteJob(job.id)
        router.push("/jobs")
      } catch (err) {
        console.error("Error deleting job:", err)
        alert("Failed to delete job description. Please try again.")
      }
    }
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
        
        <Card>
          <CardContent className="pt-6">
            <div className="bg-destructive/10 text-destructive p-4 rounded-md">
              {error || "Job description not found"}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <div className="flex items-center justify-between mb-8">
        <Link href="/jobs">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Jobs
          </Button>
        </Link>
        
        <div className="flex gap-2">
          <Link href={`/jobs/${job.id}/edit`}>
            <Button variant="outline">
              <Pencil className="mr-2 h-4 w-4" /> Edit
            </Button>
          </Link>
          <Button variant="destructive" onClick={handleDelete}>
            <Trash className="mr-2 h-4 w-4" /> Delete
          </Button>
        </div>
      </div>
      
      <Card className="mb-6">
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="text-2xl">{job.title}</CardTitle>
              {job.company && <p className="text-lg mt-1">{job.company}</p>}
            </div>
            <div className="text-sm text-muted-foreground">
              Added on {format(new Date(job.created_at), 'MMM d, yyyy')}
            </div>
          </div>
        </CardHeader>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>Job Description</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="whitespace-pre-wrap">{job.description}</div>
        </CardContent>
      </Card>
    </div>
  )
}