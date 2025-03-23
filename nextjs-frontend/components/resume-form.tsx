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
import { FileUpload } from "@/components/ui/file-upload"
import { CheckCircle2, Loader2 } from "lucide-react"
import { ResumeService } from "@/lib/client"

// Define form schema with zod
const resumeFormSchema = z.object({
  title: z.string()
    .min(3, { message: "Title must be at least 3 characters" })
    .max(100, { message: "Title must be less than 100 characters" }),
  content: z.string()
    .min(1, { message: "Resume content is required" })
    .max(100000, { message: "Resume content is too long" }),
})

export type ResumeFormValues = z.infer<typeof resumeFormSchema>

export interface ResumeFormProps {
  initialData?: {
    id?: string
    title: string
    content: string
  }
  onSuccess?: (data: any) => void
}

export function ResumeForm({ initialData, onSuccess }: ResumeFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitSuccess, setSubmitSuccess] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [fileUploadError, setFileUploadError] = useState<string | null>(null)
  
  // Form setup with react-hook-form and zod validation
  const form = useForm<ResumeFormValues>({
    resolver: zodResolver(resumeFormSchema),
    defaultValues: {
      title: initialData?.title || "",
      content: initialData?.content || "",
    },
  })
  
  // Handle file upload
  const handleFileUpload = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.md')) {
      setFileUploadError("Only Markdown (.md) files are accepted")
      return
    }
    
    setFileUploadError(null)
  }
  
  // Handle file content parsing
  const handleFileContent = (content: string) => {
    form.setValue("content", content)
  }
  
  // Handle form submission
  async function onSubmit(values: ResumeFormValues) {
    setIsSubmitting(true)
    setSubmitSuccess(false)
    setSubmitError(null)
    
    try {
      let result
      
      if (initialData?.id) {
        // Update existing resume
        result = await ResumeService.updateResume(initialData.id, {
          title: values.title,
          content: values.content,
        })
      } else {
        // Create new resume
        result = await ResumeService.createResume({
          title: values.title,
          content: values.content,
        })
      }
      
      setSubmitSuccess(true)
      
      if (onSuccess) {
        onSuccess(result)
      }
      
      // Reset form if creating a new resume (not editing)
      if (!initialData?.id) {
        form.reset({
          title: "",
          content: "",
        })
      }
    } catch (error) {
      console.error("Error saving resume:", error)
      setSubmitError("Failed to save resume. Please try again.")
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
          {initialData?.id ? "Edit Resume" : "New Resume"}
        </CardTitle>
        <CardDescription>
          Create or edit your resume in Markdown format
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
                  <FormLabel>Resume Title</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="e.g., Software Engineer Resume" 
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    A descriptive name for your resume
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            
            {/* File upload */}
            <div className="space-y-2">
              <p className="text-sm font-medium">Upload Resume</p>
              <FileUpload
                accept=".md"
                onFileSelect={handleFileUpload}
                onFileContent={handleFileContent}
                error={fileUploadError || ""}
              />
              <p className="text-xs text-muted-foreground">
                Upload a Markdown (.md) file or enter content directly below
              </p>
            </div>
            
            {/* Content field */}
            <FormField
              control={form.control}
              name="content"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Resume Content</FormLabel>
                  <FormControl>
                    <Textarea 
                      placeholder="# John Doe
## Contact
- Email: john.doe@example.com
- Phone: (123) 456-7890

## Education
- BS in Computer Science, Example University (2015-2019)

## Experience
- Software Engineer, Example Corp (2019-Present)
  - Developed feature X that increased efficiency by 30%
  - Led a team of 5 engineers on Project Y
"                      
                      className="font-mono min-h-[350px] resize-y p-4"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Enter your resume content in Markdown format
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
                Resume saved successfully!
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
                initialData?.id ? "Update Resume" : "Save Resume"
              )}
            </Button>
          </CardFooter>
        </form>
      </Form>
    </Card>
  )
}