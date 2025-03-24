"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp, AlertCircle } from "lucide-react"

interface ImprovementSuggestionsProps {
  suggestions: Record<string, string[]>
}

export function ImprovementSuggestions({ suggestions }: ImprovementSuggestionsProps) {
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({})

  // Toggle category expansion
  const toggleCategory = (category: string) => {
    setExpandedCategories({
      ...expandedCategories,
      [category]: !expandedCategories[category]
    })
  }

  // Get priority indicator for suggestion categories
  const getCategoryPriority = (category: string, itemCount: number) => {
    // Known high priority categories
    const highPriorityCategories = [
      'Missing Keywords', 
      'Skills Section', 
      'Skills', 
      'Experience Section', 
      'Quantified Results'
    ];
    
    // Known medium priority categories
    const mediumPriorityCategories = [
      'Keyword Density', 
      'Experience', 
      'Action Verbs', 
      'Technical Details'
    ];
    
    // Known low priority categories
    const lowPriorityCategories = [
      'Education', 
      'Resume Length', 
      'Formatting'
    ];
    
    // Determine priority based on category and item count
    let priority;
    
    if (highPriorityCategories.includes(category)) {
      priority = { color: 'bg-red-500', label: 'High Priority' };
    } else if (mediumPriorityCategories.includes(category)) {
      priority = { color: 'bg-amber-500', label: 'Medium Priority' };
    } else if (lowPriorityCategories.includes(category)) {
      priority = { color: 'bg-emerald-500', label: 'Low Priority' };
    } else {
      // Default priority based on item count
      priority = itemCount > 3 
        ? { color: 'bg-red-500', label: 'High Priority' }
        : itemCount > 1 
          ? { color: 'bg-amber-500', label: 'Medium Priority' } 
          : { color: 'bg-emerald-500', label: 'Low Priority' };
    }

    return priority;
  }

  if (!suggestions || Object.keys(suggestions).length === 0) {
    return (
      <div className="border rounded-lg p-4">
        <h3 className="font-medium text-lg mb-2">Improvement Suggestions</h3>
        <div className="flex items-center gap-2 text-muted-foreground">
          <AlertCircle className="h-5 w-5" />
          <p>No improvement suggestions available.</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h3 className="font-medium text-lg mb-3">Improvement Suggestions</h3>
      <div className="space-y-3">
        {Object.entries(suggestions).map(([category, items]) => {
          const isExpanded = expandedCategories[category] ?? false
          const priority = getCategoryPriority(category, items.length)
          
          return (
            <div key={category} className="border rounded-lg overflow-hidden">
              <div 
                className="flex justify-between items-center p-4 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => toggleCategory(category)}
              >
                <div className="flex items-center gap-3">
                  <span className={`${priority.color} w-2 h-6 rounded-sm`} aria-hidden="true" />
                  <h4 className="font-medium">{category}</h4>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                    {priority.label}
                  </span>
                </div>
                <button aria-label={isExpanded ? "Collapse section" : "Expand section"}>
                  {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </button>
              </div>
              
              {isExpanded && (
                <div className="px-4 pb-4 pt-1">
                  <ul className="list-disc pl-6 space-y-2">
                    {items.map((item, index) => (
                      <li key={index} className="text-sm">{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}