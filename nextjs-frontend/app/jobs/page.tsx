"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { JobService, JobDescription } from "@/lib/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { PlusCircle, Loader2, Briefcase } from "lucide-react"
import { format } from "date-fns"

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadJobs() {
      try {
        const jobsData = await JobService.getJobs()
        setJobs(jobsData)
      } catch (err) {
        console.error("Error loading jobs:", err)
        setError("Failed to load job descriptions. Please try again later.")
      } finally {
        setIsLoading(false)
      }
    }

    loadJobs()
  }, [])

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this job description?")) {
      try {
        await JobService.deleteJob(id)
        setJobs(jobs.filter(job => job.id !== id))
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

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Job Descriptions</h1>
        <Link href="/jobs/new">
          <Button>
            <PlusCircle className="mr-2 h-4 w-4" /> Add New Job
          </Button>
        </Link>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive p-4 rounded-md mb-6">
          {error}
        </div>
      )}

      {jobs.length === 0 ? (
        <div className="text-center py-16 bg-muted/20 rounded-lg">
          <Briefcase className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-xl font-medium mb-2">No job descriptions yet</h3>
          <p className="text-muted-foreground mb-6">Add your first job description to get started</p>
          <Link href="/jobs/new">
            <Button>
              <PlusCircle className="mr-2 h-4 w-4" /> Add New Job
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {jobs.map((job) => (
            <Card key={job.id} className="h-full flex flex-col">
              <CardHeader>
                <CardTitle className="line-clamp-2">{job.title}</CardTitle>
              </CardHeader>
              <CardContent className="flex-grow">
                {job.company && (
                  <p className="text-sm text-muted-foreground mb-2">{job.company}</p>
                )}
                <p className="text-sm text-muted-foreground">
                  Added on {format(new Date(job.created_at), 'MMM d, yyyy')}
                </p>
              </CardContent>
              <CardFooter className="flex justify-between gap-2">
                <Button variant="outline" size="sm" asChild className="flex-1">
                  <Link href={`/jobs/${job.id}`}>View</Link>
                </Button>
                <Button variant="outline" size="sm" asChild className="flex-1">
                  <Link href={`/jobs/${job.id}/edit`}>Edit</Link>
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="flex-1"
                  onClick={() => handleDelete(job.id)}
                >
                  Delete
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}