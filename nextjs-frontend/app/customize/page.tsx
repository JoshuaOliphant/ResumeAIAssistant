"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ChevronLeft } from "lucide-react"

export default function CustomizePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold">Customize Resume</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Resume Customization</CardTitle>
          <CardDescription>
            Resume customization functionality is being updated. Please check back soon.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-center py-8">
            <p className="text-muted-foreground mb-4">
              We're working on improving the resume customization experience.
            </p>
            <Button
              onClick={() => router.push('/resumes')}
            >
              <ChevronLeft className="mr-2 h-4 w-4" />
              Back to Resumes
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}