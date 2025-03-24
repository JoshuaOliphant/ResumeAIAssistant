"use client"

interface MissingKeywordsProps {
  keywords: string[]
}

export function MissingKeywords({ keywords }: MissingKeywordsProps) {
  if (!keywords || keywords.length === 0) {
    return (
      <div className="border rounded-lg p-4">
        <h3 className="font-medium text-lg mb-2">Missing Keywords</h3>
        <p className="text-muted-foreground text-sm">
          Great job! Your resume includes all the major keywords from the job description.
        </p>
      </div>
    )
  }

  return (
    <div className="border rounded-lg p-4">
      <h3 className="font-medium text-lg mb-3">Missing Keywords</h3>
      <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto">
        {keywords.map((keyword, index) => (
          <div 
            key={index} 
            className="bg-destructive/10 text-destructive px-3 py-1 rounded-full text-sm flex items-center"
          >
            {keyword}
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        Consider adding these keywords to your resume to improve your ATS compatibility score.
      </p>
    </div>
  )
}