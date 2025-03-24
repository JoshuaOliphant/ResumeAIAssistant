"use client"

interface KeywordMatchProps {
  keywords: { keyword: string; count: number }[]
}

export function KeywordMatch({ keywords }: KeywordMatchProps) {
  if (!keywords || keywords.length === 0) {
    return (
      <div className="border rounded-lg p-4">
        <h3 className="font-medium text-lg mb-2">Matching Keywords</h3>
        <p className="text-muted-foreground text-sm">
          No matching keywords found. Consider adding industry-specific terms from the job description.
        </p>
      </div>
    )
  }

  return (
    <div className="border rounded-lg p-4">
      <h3 className="font-medium text-lg mb-3">Matching Keywords</h3>
      <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto">
        {keywords.map((item, index) => (
          <div 
            key={index} 
            className="bg-primary/10 text-primary px-3 py-1 rounded-full text-sm flex items-center"
          >
            <span className="mr-1">{item.keyword}</span>
            <span className="bg-primary text-primary-foreground text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium">
              {item.count}
            </span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">
        These keywords were found in your resume and are likely to be picked up by ATS systems.
      </p>
    </div>
  )
}