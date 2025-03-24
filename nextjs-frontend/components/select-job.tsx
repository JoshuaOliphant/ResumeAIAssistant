"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle,
  DialogTrigger 
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { JobDescription, JobService } from "@/lib/client"
import { Loader2, FilePlus, FileEdit, Building } from "lucide-react"
import { JobsTable } from "@/components/jobs-table"
import Link from "next/link"

interface SelectJobProps {
  value?: string
  onValueChange: (value: string) => void
  onJobChange?: (job: JobDescription | null) => void
  disabled?: boolean
}

export function SelectJob({ 
  value, 
  onValueChange, 
  onJobChange,
  disabled = false 
}: SelectJobProps) {
  const [jobs, setJobs] = useState<JobDescription[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [selectedJob, setSelectedJob] = useState<JobDescription | null>(null)

  const loadJobs = async () => {
    try {
      setIsLoading(true)
      const data = await JobService.getJobs()
      setJobs(data)
      
      // If a job was selected but no longer exists in the list,
      // reset the selection
      if (value && !data.some(job => job.id === value)) {
        onValueChange("")
        if (onJobChange) onJobChange(null)
        setSelectedJob(null)
      }

      // If a value exists, find the corresponding job
      if (value) {
        const job = data.find(job => job.id === value) || null
        setSelectedJob(job)
        if (onJobChange) onJobChange(job)
      }
    } catch (error) {
      console.error("Error loading jobs:", error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
  }, [])

  const handleSelectionChange = (newValue: string) => {
    onValueChange(newValue)
    
    // Find the selected job and pass it up if requested
    const job = jobs.find(job => job.id === newValue) || null
    setSelectedJob(job)
    if (onJobChange) {
      onJobChange(job)
    }
  }

  const handleTableChange = () => {
    loadJobs()
  }

  return (
    <div className="space-y-2 w-full">
      <div className="flex justify-between items-center">
        <label className="text-sm font-medium" htmlFor="job-select">Select Job Description</label>
        <div className="flex gap-2">
          {selectedJob && (
            <Button 
              variant="outline" 
              size="sm" 
              asChild
              title="Edit selected job"
            >
              <Link href={`/jobs/${selectedJob.id}`}>
                <FileEdit className="h-4 w-4 mr-1" />
                Edit
              </Link>
            </Button>
          )}
          <Button variant="outline" size="sm" asChild title="Create a new job">
            <Link href="/jobs/new">
              <FilePlus className="h-4 w-4 mr-1" />
              New
            </Link>
          </Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" disabled={disabled} title="View all jobs">
                Manage
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl">
              <DialogHeader>
                <DialogTitle>Manage Job Descriptions</DialogTitle>
                <DialogDescription>
                  View, edit or delete your saved job descriptions
                </DialogDescription>
              </DialogHeader>
              <div className="py-4">
                <JobsTable 
                  jobs={jobs} 
                  onChange={handleTableChange} 
                  onSelect={(jobId) => {
                    handleSelectionChange(jobId)
                    setOpen(false)
                  }}
                />
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center h-10 w-full rounded-md border border-input">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center p-4 border rounded-md bg-muted/20 space-y-4">
          <p className="text-muted-foreground text-sm">
            No saved job descriptions found. Create a new job description to get started.
          </p>
          <Button asChild variant="secondary" size="sm">
            <Link href="/jobs/new">
              <FilePlus className="h-4 w-4 mr-2" />
              Create Job
            </Link>
          </Button>
        </div>
      ) : (
        <Select value={value} onValueChange={handleSelectionChange} disabled={disabled}>
          <SelectTrigger id="job-select" className="w-full">
            <SelectValue placeholder="Choose a job description..." />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectLabel>Your Job Descriptions</SelectLabel>
              {jobs.map((job) => (
                <SelectItem key={job.id} value={job.id}>
                  {job.title} {job.company ? `- ${job.company}` : ''}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      )}
      
      {selectedJob && (
        <div className="flex flex-col text-xs text-muted-foreground mt-1">
          <div className="flex items-center">
            {selectedJob.company && (
              <span className="flex items-center mr-2">
                <Building className="h-3 w-3 mr-1" />
                {selectedJob.company}
              </span>
            )}
            <span>Last updated: {new Date(selectedJob.updated_at).toLocaleDateString()}</span>
          </div>
          <div className="line-clamp-1 mt-1">
            {selectedJob.description.substring(0, 100)}...
          </div>
        </div>
      )}
    </div>
  )
}