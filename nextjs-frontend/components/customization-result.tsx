"use client"

import { useState, useEffect } from "react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { ResumeService, ExportService, ResumeVersion, ResumeDiff } from "@/lib/client"
import { ResumeDiffView } from "@/components/resume-diff-view"
import { FileText, Download, FileDown, FileCode } from "lucide-react"

export interface CustomizationResultProps {
  resumeId: string
  versionId: string
  originalVersionId?: string
}

export function CustomizationResult({ resumeId, versionId, originalVersionId }: CustomizationResultProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [customizedVersion, setCustomizedVersion] = useState<ResumeVersion | null>(null)
  const [resumeDiff, setResumeDiff] = useState<ResumeDiff | null>(null)
  const [downloading, setDownloading] = useState<string | null>(null)

  // Fetch customized version and diff data
  useEffect(() => {
    const fetchData = async () => {
      if (!resumeId) {
        console.error("Missing resumeId parameter");
        setError("Resume ID is required");
        setLoading(false);
        return;
      }
      
      try {
        setLoading(true);
        setError(null);
        console.log("Fetching resume data for:", resumeId, "with version:", versionId || "latest");
        
        // Get the resume data
        const resume = await ResumeService.getResume(resumeId);
        console.log("Got resume:", resume);
        
        // Find the appropriate version to display
        let versionToUse;
        
        if (versionId === 'latest' || !versionId) {
          // Use the current version if no specific version is requested or 'latest' is specified
          console.log("Using current version:", resume.current_version);
          versionToUse = resume.current_version;
        } else {
          // Try to find the specified version
          versionToUse = resume.current_version;
          // In production, we would fetch the specific version
          // For now, we'll use the current version as a fallback
          console.log("Using current version for now (would fetch specific version in production)");
        }
        
        // Set the customized version
        if (!versionToUse) {
          throw new Error("Could not find the requested resume version");
        }
        
        setCustomizedVersion(versionToUse);
        console.log("Set customized version:", versionToUse);
        
        try {
          // Get resume diff - handle this separately so if it fails, we still show the resume
          const diffVersionId = versionToUse.id;
          console.log("Fetching diff using version ID:", diffVersionId);
          
          const diff = await ResumeService.getResumeDiff(resumeId, diffVersionId, originalVersionId);
          console.log("Got resume diff:", diff);
          
          // Make sure the diff has the required properties
          let updatedDiff = { ...diff };
          
          if (!updatedDiff.section_analysis) {
            console.warn("Diff is missing section_analysis, adding an empty object");
            updatedDiff.section_analysis = {};
          }
          
          if (!updatedDiff.diff_statistics) {
            console.warn("Diff is missing diff_statistics, adding default values");
            updatedDiff.diff_statistics = {
              additions: 0,
              deletions: 0,
              modifications: 0
            };
          }

          // Ensure original and customized content are strings
          if (!updatedDiff.original_content || typeof updatedDiff.original_content !== 'string') {
            console.warn("Diff is missing or invalid original_content, using resume content");
            updatedDiff.original_content = resume.current_version?.content || "";
          }
          
          if (!updatedDiff.customized_content || typeof updatedDiff.customized_content !== 'string') {
            console.warn("Diff is missing or invalid customized_content, using current version content");
            updatedDiff.customized_content = versionToUse.content || "";
          }
          
          // Strip any HTML from the content that might interfere with the diff viewer
          if (updatedDiff.original_content.includes('<span') || updatedDiff.original_content.includes('</span>')) {
            console.warn("Stripping HTML from original_content");
            updatedDiff.original_content = updatedDiff.original_content.replace(/<\/?[^>]+(>|$)/g, "");
          }
          
          if (updatedDiff.customized_content.includes('<span') || updatedDiff.customized_content.includes('</span>')) {
            console.warn("Stripping HTML from customized_content");
            updatedDiff.customized_content = updatedDiff.customized_content.replace(/<\/?[^>]+(>|$)/g, "");
          }
          
          setResumeDiff(updatedDiff);
          console.log("Set resume diff:", updatedDiff);
        } catch (diffErr) {
          console.error("Error fetching diff:", diffErr);
          console.log("Creating fallback diff object using resume content");
          
          // Create a minimal valid diff object to avoid rendering errors
          setResumeDiff({
            id: resumeId,
            title: resume.title,
            original_content: resume.current_version?.content?.replace(/<\/?[^>]+(>|$)/g, "") || "",
            customized_content: versionToUse.content?.replace(/<\/?[^>]+(>|$)/g, "") || "",
            diff_content: "",
            diff_statistics: {
              additions: 0,
              deletions: 0,
              modifications: 0
            },
            section_analysis: {},
            is_diff_view: false
          });
        }
      } catch (err) {
        console.error("Error fetching customization result:", err);
        setError(err instanceof Error ? err.message : "Failed to load customization result");
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, [resumeId, versionId, originalVersionId])

  // Handle file download
  const handleDownload = async (format: 'pdf' | 'docx' | 'markdown') => {
    if (!customizedVersion) return
    
    try {
      setDownloading(format)
      
      if (format === 'pdf') {
        // Download PDF
        const blob = await ExportService.exportResumeToPdf(resumeId, versionId)
        downloadBlob(blob, `resume_${resumeId}_customized.pdf`)
      } else if (format === 'docx') {
        // Download DOCX
        const blob = await ExportService.exportResumeToDocx(resumeId, versionId)
        downloadBlob(blob, `resume_${resumeId}_customized.docx`)
      } else if (format === 'markdown') {
        // Download markdown
        if (customizedVersion?.content) {
          const blob = new Blob([customizedVersion.content], { type: 'text/markdown' })
          downloadBlob(blob, `resume_${resumeId}_customized.md`)
        }
      }
    } catch (err) {
      console.error(`Error downloading ${format}:`, err)
      alert(`Failed to download ${format.toUpperCase()}: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setDownloading(null)
    }
  }

  // Helper function to trigger file download
  const downloadBlob = (blob: Blob, fileName: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
  
  // Render loading state
  if (loading) {
    return (
      <Card className="w-full">
        <CardContent className="pt-6">
          <div className="flex justify-center items-center min-h-[300px]">
            <div className="animate-pulse flex flex-col items-center space-y-4">
              <div className="h-12 w-12 rounded-full bg-secondary"></div>
              <div className="h-4 w-32 bg-secondary rounded"></div>
              <div className="h-2 w-48 bg-secondary rounded"></div>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }
  
  // Render error state
  if (error) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Error Loading Results</CardTitle>
          <CardDescription>{error}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex justify-center">
            <Button onClick={() => window.location.reload()} variant="outline">
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }
  
  // Render no data state
  if (!customizedVersion) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>No Results Found</CardTitle>
          <CardDescription>The customized resume version could not be found.</CardDescription>
        </CardHeader>
      </Card>
    )
  }
  
  return (
    <div className="space-y-6">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Customized Resume</CardTitle>
          <CardDescription>View and download your customized resume</CardDescription>
        </CardHeader>
        <CardContent className="pb-0">
          <Tabs defaultValue="customized">
            <TabsList className="mb-4">
              <TabsTrigger value="customized">
                <FileText className="mr-2 h-4 w-4" />
                Customized Resume
              </TabsTrigger>
              <TabsTrigger value="changes">
                <FileCode className="mr-2 h-4 w-4" />
                View Changes
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="customized" className="mt-0">
              <div className="relative">
                <div className="bg-muted p-4 rounded-md overflow-auto max-h-[600px] font-mono text-sm whitespace-pre-wrap">
                  {customizedVersion.content}
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="changes" className="mt-0">
              {resumeDiff ? (
                <>
                  {console.log("About to render ResumeDiffView with:", resumeDiff)}
                  <ResumeDiffView resumeDiff={resumeDiff} />
                </>
              ) : (
                <div className="p-4 bg-muted rounded-md">
                  <p className="text-muted-foreground">No difference data available.</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
        <CardFooter className="flex flex-wrap justify-center sm:justify-end gap-2 pt-6">
          <Button
            variant="outline"
            onClick={() => handleDownload('markdown')}
            disabled={downloading === 'markdown'}
          >
            {downloading === 'markdown' ? (
              <FileDown className="mr-2 h-4 w-4 animate-bounce" />
            ) : (
              <FileCode className="mr-2 h-4 w-4" />
            )}
            Markdown
          </Button>
          <Button
            variant="outline"
            onClick={() => handleDownload('docx')}
            disabled={downloading === 'docx'}
          >
            {downloading === 'docx' ? (
              <FileDown className="mr-2 h-4 w-4 animate-bounce" />
            ) : (
              <FileText className="mr-2 h-4 w-4" />
            )}
            DOCX
          </Button>
          <Button
            onClick={() => handleDownload('pdf')}
            disabled={downloading === 'pdf'}
          >
            {downloading === 'pdf' ? (
              <FileDown className="mr-2 h-4 w-4 animate-bounce" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            Download PDF
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}