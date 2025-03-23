"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { ResumeForm } from "@/components/resume-form"

export default function NewResumePage() {
  const router = useRouter()
  
  const handleSuccess = (data: any) => {
    // Navigate to the resume detail or edit page
    router.push(`/resumes/${data.id}`)
  }
  
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">Create New Resume</h1>
      <p className="text-muted-foreground mb-8">
        Create a new resume by entering the content in Markdown format or uploading a Markdown file.
      </p>
      
      <ResumeForm onSuccess={handleSuccess} />
    </div>
  )
}