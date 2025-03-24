"use client"

import { useState } from "react"
import { JobDescriptionForm } from "@/components/job-description-form"
import { JobURLForm } from "@/components/job-url-form"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useRouter } from "next/navigation"
import { JobDescription } from "@/lib/client"

export default function NewJobPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState("import") // Start with import tab active
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
    console.log("Import successful! Switching tabs with data:", data)
    
    // First update the imported data
    setImportedData(data)
    
    // Then switch the active tab
    console.log("Switching to manual tab")
    setActiveTab("manual")
  }
  
  return (
    <div className="container mx-auto py-8 max-w-3xl">
      <h1 className="text-3xl font-bold mb-8">Add Job Description</h1>
      
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-8">
          <TabsTrigger id="manual-tab-trigger" value="manual">Manual Entry</TabsTrigger>
          <TabsTrigger value="import">Import from URL</TabsTrigger>
        </TabsList>
        
        <TabsContent value="manual">
          {importedData && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md text-green-800">
              <p className="font-medium">Job description successfully imported!</p>
              <p className="text-sm">You can now review and save it using the form below.</p>
            </div>
          )}
          
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