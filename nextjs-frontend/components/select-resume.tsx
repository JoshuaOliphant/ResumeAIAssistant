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
import { Resume, ResumeService } from "@/lib/client"
import { Loader2, FilePlus, FileEdit } from "lucide-react"
import { ResumesTable } from "@/components/resumes-table"
import Link from "next/link"

interface SelectResumeProps {
  value?: string
  onValueChange: (value: string) => void
  onResumeChange?: (resume: Resume | null) => void
  disabled?: boolean
}

export function SelectResume({ 
  value, 
  onValueChange, 
  onResumeChange,
  disabled = false 
}: SelectResumeProps) {
  const [resumes, setResumes] = useState<Resume[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null)

  const loadResumes = async () => {
    try {
      setIsLoading(true)
      const data = await ResumeService.getResumes()
      setResumes(data)
      
      // If a resume was selected but no longer exists in the list,
      // reset the selection
      if (value && !data.some(resume => resume.id === value)) {
        onValueChange("")
        if (onResumeChange) onResumeChange(null)
        setSelectedResume(null)
      }

      // If a value exists, find the corresponding resume
      if (value) {
        const resume = data.find(resume => resume.id === value) || null
        setSelectedResume(resume)
        if (onResumeChange) onResumeChange(resume)
      }
    } catch (error) {
      console.error("Error loading resumes:", error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadResumes()
  }, [])

  const handleSelectionChange = (newValue: string) => {
    onValueChange(newValue)
    
    // Find the selected resume and pass it up if requested
    const resume = resumes.find(resume => resume.id === newValue) || null
    setSelectedResume(resume)
    if (onResumeChange) {
      onResumeChange(resume)
    }
  }

  const handleTableChange = () => {
    loadResumes()
  }

  return (
    <div className="space-y-2 w-full">
      <div className="flex justify-between items-center">
        <label className="text-sm font-medium" htmlFor="resume-select">Select Resume</label>
        <div className="flex gap-2">
          {selectedResume && (
            <Button 
              variant="outline" 
              size="sm" 
              asChild
              title="Edit selected resume"
            >
              <Link href={`/resumes/${selectedResume.id}`}>
                <FileEdit className="h-4 w-4 mr-1" />
                Edit
              </Link>
            </Button>
          )}
          <Button variant="outline" size="sm" asChild title="Create a new resume">
            <Link href="/resumes/new">
              <FilePlus className="h-4 w-4 mr-1" />
              New
            </Link>
          </Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" disabled={disabled} title="View all resumes">
                Manage
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl">
              <DialogHeader>
                <DialogTitle>Manage Resumes</DialogTitle>
                <DialogDescription>
                  View, edit or delete your saved resumes
                </DialogDescription>
              </DialogHeader>
              <div className="py-4">
                <ResumesTable 
                  resumes={resumes} 
                  onChange={handleTableChange} 
                  onSelect={(resumeId) => {
                    handleSelectionChange(resumeId)
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
      ) : resumes.length === 0 ? (
        <div className="text-center p-4 border rounded-md bg-muted/20 space-y-4">
          <p className="text-muted-foreground text-sm">
            No saved resumes found. Create a new resume to get started.
          </p>
          <Button asChild variant="secondary" size="sm">
            <Link href="/resumes/new">
              <FilePlus className="h-4 w-4 mr-2" />
              Create Resume
            </Link>
          </Button>
        </div>
      ) : (
        <Select value={value} onValueChange={handleSelectionChange} disabled={disabled}>
          <SelectTrigger id="resume-select" className="w-full">
            <SelectValue placeholder="Choose your resume..." />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectLabel>Your Resumes</SelectLabel>
              {resumes.map((resume) => (
                <SelectItem key={resume.id} value={resume.id}>
                  {resume.title}
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      )}
      
      {selectedResume && (
        <div className="text-xs text-muted-foreground mt-1">
          Last updated: {new Date(selectedResume.updated_at).toLocaleDateString()}
        </div>
      )}
    </div>
  )
}