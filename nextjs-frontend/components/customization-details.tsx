"use client"

import { CustomizationResult, ExportService } from "@/lib/client"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

interface CustomizationDetailsProps {
  result: CustomizationResult
}

export function CustomizationDetails({ result }: CustomizationDetailsProps) {
  if (!result) return null

  const download = async (url?: string) => {
    if (!url) return
    try {
      const blob = await ExportService.downloadFromUrl(url)
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = url.split('/').pop() || 'file'
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (error) {
      console.error('Download failed:', error)
      // Optionally add user feedback here
    }
  }

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Customization Details</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {result.analysis && (
          <div>
            <h4 className="font-medium mb-1">Initial Match Score</h4>
            <p className="text-sm">{result.analysis.match_score}%</p>
          </div>
        )}
        {result.verification && (
          <div>
            <h4 className="font-medium mb-1">Final Match Score</h4>
            <p className="text-sm">{result.verification.final_score}% ( +{result.verification.improvement} )</p>
          </div>
        )}
        {result.plan && result.plan.format_improvements && (
          <div>
            <h4 className="font-medium mb-1">Summary of Changes</h4>
            <ul className="list-disc list-inside text-sm space-y-1">
              {result.plan.format_improvements.map((imp: string, idx: number) => (
                <li key={idx}>{imp}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => download(result.customized_resume_url)}>
            Download Resume
          </Button>
          {result.diff_url && (
            <Button variant="outline" onClick={() => download(result.diff_url)}>
              Download Diff
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
