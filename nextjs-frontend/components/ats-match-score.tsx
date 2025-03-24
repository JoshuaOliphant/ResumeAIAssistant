"use client"

import { Progress } from "@/components/ui/progress"

interface MatchScoreProps {
  score: number
  confidence?: string
}

export function MatchScore({ score, confidence }: MatchScoreProps) {
  // Determine color based on score ranges
  const getScoreColor = (score: number) => {
    if (score >= 80) return "bg-emerald-500"
    if (score >= 60) return "bg-amber-500"
    return "bg-red-500"
  }

  // Get a descriptive text based on score
  const getScoreDescription = (score: number) => {
    if (score >= 80) return "Great match! Your resume is well-aligned with this job."
    if (score >= 60) return "Good match. Some improvements could help your application."
    return "Low match. Consider tailoring your resume to improve chances."
  }

  // Get confidence badge color
  const getConfidenceBadgeColor = (confidence?: string) => {
    if (!confidence) return "bg-gray-200 text-gray-700";
    
    switch (confidence.toLowerCase()) {
      case 'high':
        return "bg-emerald-100 text-emerald-800";
      case 'medium':
        return "bg-amber-100 text-amber-800";
      case 'low':
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-200 text-gray-700";
    }
  }

  return (
    <div className="flex-1">
      <div className="flex justify-between mb-2 items-center">
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-lg">Match Score</h3>
          {confidence && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${getConfidenceBadgeColor(confidence)}`}>
              {confidence.charAt(0).toUpperCase() + confidence.slice(1)} Confidence
            </span>
          )}
        </div>
        <span className="font-semibold text-lg">{score}%</span>
      </div>
      
      <Progress 
        value={score} 
        className="h-3"
        indicatorClassName={getScoreColor(score)}
      />
      
      <p className="mt-2 text-sm text-muted-foreground">
        {getScoreDescription(score)}
        {confidence === 'low' && (
          <span className="block text-xs mt-1 text-amber-600">
            Note: Low confidence score. Consider providing more detailed resume and job description.
          </span>
        )}
      </p>
    </div>
  )
}