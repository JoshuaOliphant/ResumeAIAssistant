"use client"

import * as React from "react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { AlertCircle, Loader2 } from "lucide-react"
import { JobService } from "@/lib/client"

// Define form schema with zod
const jobUrlFormSchema = z.object({
  url: z.string()
    .url({ message: "Please enter a valid URL" })
    .min(5, { message: "URL is too short" })
    .max(500, { message: "URL is too long" }),
})

export type JobUrlFormValues = z.infer<typeof jobUrlFormSchema>

export interface JobURLFormProps {
  onImportSuccess: (data: { title: string; company?: string; description: string }) => void
  onImportError?: (error: string) => void
}

export function JobURLForm({ onImportSuccess, onImportError }: JobURLFormProps) {
  const [isImporting, setIsImporting] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null)
  
  // Form setup with react-hook-form and zod validation
  const form = useForm<JobUrlFormValues>({
    resolver: zodResolver(jobUrlFormSchema),
    defaultValues: {
      url: "",
    },
  })
  
  // Handle form submission
  async function onSubmit(values: JobUrlFormValues) {
    setIsImporting(true)
    setImportError(null)
    
    // Set timeout handler - giving plenty of time for the API to process
    const timeout = setTimeout(() => {
      setImportError("The request is taking longer than expected. The website might be slow to respond or blocked.");
      setIsImporting(false);
    }, 120000); // 120 seconds (2 minutes) timeout
    
    setTimeoutId(timeout);
    
    try {
      const importedData = await JobService.importFromUrl(values.url);
      
      // Clear timeout as we received a response
      if (timeoutId) clearTimeout(timeoutId);
      
      onImportSuccess(importedData);
      
      // Reset form after successful import
      form.reset({
        url: "",
      });
    } catch (error) {
      console.error("Error importing job description:", error);
      
      // Clear timeout as we received an error
      if (timeoutId) clearTimeout(timeoutId);
      
      // Extract error message if available
      let errorMessage = "Failed to import job description. Please try again or copy and paste the description manually.";
      
      if (error instanceof Error) {
        // If it's a specific error from the JINA API, use that message
        errorMessage = error.message || errorMessage;
      }
      
      setImportError(errorMessage);
      
      if (onImportError) {
        onImportError(errorMessage);
      }
    } finally {
      setIsImporting(false);
    }
  }
  
  // Clean up timeout on unmount
  React.useEffect(() => {
    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [timeoutId]);
  
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Import from URL</CardTitle>
        <CardDescription>
          Import a job description from a website URL
        </CardDescription>
      </CardHeader>
      
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <CardContent className="space-y-6">
            {/* URL field */}
            <FormField
              control={form.control}
              name="url"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Job Posting URL</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="https://example.com/jobs/software-engineer" 
                      {...field}
                      disabled={isImporting}
                    />
                  </FormControl>
                  <FormDescription>
                    Paste the URL of the job listing you want to import
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            {/* Error message */}
            {importError && (
              <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm flex items-start">
                <AlertCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                <div>{importError}</div>
              </div>
            )}
          </CardContent>
          
          <CardFooter>
            <Button 
              type="submit" 
              className="w-full"
              disabled={isImporting}
            >
              {isImporting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Importing...
                </>
              ) : (
                "Import Job Description"
              )}
            </Button>
          </CardFooter>
          
          {/* Debug information */}
          <div className="p-3 text-xs text-muted-foreground">
            <p>After importing a job, the content will be used to pre-fill the job description form.</p>
            <p>Enter a URL like: https://www.linkedin.com/jobs/view/4133298276</p>
          </div>
        </form>
      </Form>
    </Card>
  )
}