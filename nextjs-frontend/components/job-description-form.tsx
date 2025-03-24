"use client"

import * as React from "react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { CheckCircle2, Loader2 } from "lucide-react"
import { JobService, JobDescription } from "@/lib/client"

// Define form schema with zod
const jobDescriptionFormSchema = z.object({
  title: z.string()
    .min(3, { message: "Title must be at least 3 characters" })
    .max(100, { message: "Title must be less than 100 characters" }),
  company: z.string()
    .max(100, { message: "Company name must be less than 100 characters" })
    .optional(),
  description: z.string()
    .min(1, { message: "Job description is required" })
    .max(100000, { message: "Job description is too long" }),
})

export type JobDescriptionFormValues = z.infer<typeof jobDescriptionFormSchema>

export interface JobDescriptionFormProps {
  initialData?: {
    id?: string
    title: string
    company?: string
    description: string
  }
  onSuccess?: (data: JobDescription) => void
}

export function JobDescriptionForm({ initialData, onSuccess }: JobDescriptionFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  
  // Form setup with react-hook-form and zod validation
  const form = useForm<JobDescriptionFormValues>({
    resolver: zodResolver(jobDescriptionFormSchema),
    defaultValues: {
      title: initialData?.title || "",
      company: initialData?.company || "",
      description: initialData?.description || "",
    },
  })
  
  // Update form values when initialData changes
  React.useEffect(() => {
    if (initialData) {
      console.log("Updating form with initialData:", initialData)
      form.reset({
        title: initialData.title || "",
        company: initialData.company || "",
        description: initialData.description || "",
      })
    }
  }, [initialData, form])
  
  // Handle form submission
  async function onSubmit(values: JobDescriptionFormValues) {
    setIsSubmitting(true)
    setSubmitSuccess(false)
    setSubmitError(null)
    
    try {
      let result
      
      if (initialData?.id) {
        // Update existing job description
        result = await JobService.updateJob(initialData.id, {
          title: values.title,
          company: values.company,
          description: values.description,
        })
      } else {
        // Create new job description
        result = await JobService.createJob({
          title: values.title,
          company: values.company,
          description: values.description,
        })
      }
      
      setSubmitSuccess(true)
      
      if (onSuccess) {
        onSuccess(result)
      }
      
      // Reset form if creating a new job description (not editing)
      if (!initialData?.id) {
        form.reset({
          title: "",
          company: "",
          description: "",
        })
      }
    } catch (error) {
      console.error("Error saving job description:", error)
      setSubmitError("Failed to save job description. Please try again.")
    } finally {
      setIsSubmitting(false)
      
      // Remove success message after a delay
      if (submitSuccess) {
        setTimeout(() => {
          setSubmitSuccess(false)
        }, 3000)
      }
    }
  }
  
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>
          {initialData?.id ? "Edit Job Description" : "New Job Description"}
        </CardTitle>
        <CardDescription>
          Add details about the job you're applying for
        </CardDescription>
      </CardHeader>
      
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
          <CardContent className="space-y-6">
            {/* Title field */}
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Job Title</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="e.g., Senior Software Engineer" 
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    The title of the position you're applying for
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            {/* Company field */}
            <FormField
              control={form.control}
              name="company"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Company Name (Optional)</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="e.g., Acme Corporation" 
                      {...field}
                      value={field.value || ""}
                    />
                  </FormControl>
                  <FormDescription>
                    The company offering the position
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            {/* Description field */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Job Description</FormLabel>
                  <FormControl>
                    <Textarea 
                      placeholder="Paste the full job description here..."
                      className="min-h-[300px] resize-y p-4"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Enter the full job description text
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            {/* Error message */}
            {submitError && (
              <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm">
                {submitError}
              </div>
            )}
            
            {/* Success message */}
            {submitSuccess && (
              <div className="bg-success/10 text-success flex items-center p-3 rounded-md text-sm">
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Job description saved successfully!
              </div>
            )}
          </CardContent>
          
          <CardFooter className="flex justify-between">
            <Button 
              type="button" 
              variant="outline"
              onClick={() => window.history.back()}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                initialData?.id ? "Update Job Description" : "Save Job Description"
              )}
            </Button>
          </CardFooter>
        </form>
      </Form>
    </Card>
  )
}