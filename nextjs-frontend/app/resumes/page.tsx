"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ResumeService } from "@/lib/client"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Loader2, PlusCircle, Edit, Trash2, FileText, AlertCircle, Calendar } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

export default function ResumesPage() {
  const router = useRouter()
  const [resumes, setResumes] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  useEffect(() => {
    async function loadResumes() {
      try {
        const data = await ResumeService.getResumes()
        setResumes(data)
      } catch (err) {
        console.error("Error loading resumes:", err)
        setError("Failed to load resumes. Please try again later.")
      } finally {
        setIsLoading(false)
      }
    }
    
    loadResumes()
  }, [])
  
  const handleDelete = async (id: string) => {
    if (window.confirm("Are you sure you want to delete this resume?")) {
      try {
        await ResumeService.deleteResume(id)
        setResumes(prevResumes => prevResumes.filter(resume => resume.id !== id))
      } catch (err) {
        console.error("Error deleting resume:", err)
        alert("Failed to delete resume. Please try again.")
      }
    }
  }
  
  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto py-12 px-4 flex flex-col items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-primary mb-4" />
        <p className="text-lg text-muted-foreground">Loading resumes...</p>
      </div>
    )
  }
  
  return (
    <div className="max-w-7xl mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Your Resumes</h1>
        <Button asChild>
          <Link href="/resumes/new">
            <PlusCircle className="w-4 h-4 mr-2" />
            New Resume
          </Link>
        </Button>
      </div>
      
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      {resumes.length === 0 && !error ? (
        <Card className="p-8 text-center">
          <div className="flex flex-col items-center">
            <FileText className="w-16 h-16 text-muted-foreground mb-4" />
            <h2 className="text-xl font-medium mb-2">No Resumes Found</h2>
            <p className="text-muted-foreground mb-6">
              You haven't created any resumes yet. Create your first resume to get started.
            </p>
            <Button asChild>
              <Link href="/resumes/new">
                <PlusCircle className="w-4 h-4 mr-2" />
                Create Your First Resume
              </Link>
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {resumes.map((resume) => (
            <Card key={resume.id} className="flex flex-col">
              <CardHeader className="pb-2">
                <CardTitle className="line-clamp-1">{resume.title}</CardTitle>
                <CardDescription className="flex items-center">
                  <Calendar className="w-3 h-3 mr-1" />
                  Updated {formatDistanceToNow(new Date(resume.updated_at), { addSuffix: true })}
                </CardDescription>
              </CardHeader>
              <CardContent className="pb-2 flex-grow">
                <p className="text-sm text-muted-foreground line-clamp-3">
                  {resume.current_version.content.substring(0, 150)}...
                </p>
              </CardContent>
              <CardFooter className="flex justify-between">
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/resumes/${resume.id}`}>
                    <FileText className="w-4 h-4 mr-2" />
                    View
                  </Link>
                </Button>
                <div className="flex space-x-2">
                  <Button variant="ghost" size="sm" asChild>
                    <Link href={`/resumes/${resume.id}/edit`}>
                      <Edit className="w-4 h-4" />
                      <span className="sr-only">Edit</span>
                    </Link>
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => handleDelete(resume.id)}
                    className="text-destructive hover:text-destructive/90 hover:bg-destructive/10"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span className="sr-only">Delete</span>
                  </Button>
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}