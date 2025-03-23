"use client"

import { useState } from "react"
import { JobDescriptionForm } from "@/components/job-description-form"
import { JobURLForm } from "@/components/job-url-form"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useRouter } from "next/navigation"
import { JobDescription } from "@/lib/client"

export default function NewJobPage() {
  const router = useRouter()
  const [importedData, setImportedData] = useState<{ 
    title: string; 
    company?: string; 
    description: string 
  } | null>(null)
  
  // Handle successful job description creation
  const handleSuccess = (job: JobDescription) => {
    // Navigate to the job description page after successful creation
    setTimeout(() => {
      router.push(`/jobs/${job.id}`)
    }, 2000)
  }
  
  // Handle successful import from URL
  const handleImportSuccess = (data: { 
    title: string; 
    company?: string; 
    description: string 
  }) => {
    setImportedData(data)
    // Switch to the manual tab after successful import
    document.getElementById("manual-tab-trigger")?.click()
  }
  
  return (
    <div className="container mx-auto py-8 max-w-3xl">
      <h1 className="text-3xl font-bold mb-8">Add Job Description</h1>
      
      <Tabs defaultValue="manual" className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-8">
          <TabsTrigger id="manual-tab-trigger" value="manual">Manual Entry</TabsTrigger>
          <TabsTrigger value="import">Import from URL</TabsTrigger>
        </TabsList>
        
        <TabsContent value="manual">
          <JobDescriptionForm 
            initialData={importedData || undefined} 
            onSuccess={handleSuccess} 
          />
        </TabsContent>
        
        <TabsContent value="import">
          <JobURLForm onImportSuccess={handleImportSuccess} />
        </TabsContent>
      </Tabs>
    </div>
  )
}