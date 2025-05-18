"use client"

import { useState, useContext } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { ResumeDiff } from "@/lib/client"
import { 
  PlusCircle, MinusCircle, RefreshCw, ArrowUpDown, 
  ChevronDown, ChevronUp, ExternalLink, Check, X
} from "lucide-react"
import { ThemeProvider, useTheme } from "next-themes"
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued'

export interface ResumeDiffViewProps {
  resumeDiff: ResumeDiff;
  jobTitle?: string;
  plan?: { change_explanations?: Record<string, string> } | null;
}

// Utility function to create HTML diff content
function createDiffHtml(oldText: string, newText: string, isDark: boolean): string {
  // Simple line-by-line diff
  const oldLines = oldText.split('\n');
  const newLines = newText.split('\n');
  
  // Map to track processed old lines to avoid showing removals for lines that were just moved
  const processedOldLines = new Set<string>();
  
  // First pass: identify lines that are in new but not in old (additions)
  const addedLines = newLines.filter(line => {
    // Skip empty lines
    if (!line.trim()) return false;
    return !oldLines.includes(line);
  });
  
  // Second pass: identify lines that are in old but not in new (removals)
  const removedLines = oldLines.filter(line => {
    // Skip empty lines
    if (!line.trim()) return false;
    return !newLines.includes(line);
  });
  
  // Create HTML for the diff
  let diffHtml = '';
  
  // Process each line in the new text
  for (const line of newLines) {
    if (!line.trim()) {
      // Empty line
      diffHtml += '<div style="padding: 2px 0;">&nbsp;</div>';
      continue;
    }
    
    if (addedLines.includes(line)) {
      // Line was added
      const addedStyle = isDark
        ? 'background-color: #044B53; color: white; padding: 2px 4px; border-radius: 3px; margin-bottom: 4px;'
        : 'background-color: #e6ffec; color: #24292f; padding: 2px 4px; border-radius: 3px; margin-bottom: 4px;';
      
      diffHtml += `<div style="${addedStyle}"><span style="display: inline-block; width: 16px; text-align: center; margin-right: 8px; color: ${isDark ? '#8c8c8c' : 'rgba(0,0,0,0.5)'}">+</span>${escapeHtml(line)}</div>`;
    } else {
      // Line was unchanged
      diffHtml += `<div style="padding: 2px 0;">${escapeHtml(line)}</div>`;
    }
  }
  
  // Process removed lines to show at the beginning
  if (removedLines.length > 0) {
    let removedHtml = '';
    for (const line of removedLines) {
      const removedStyle = isDark
        ? 'background-color: #632F34; color: white; padding: 2px 4px; border-radius: 3px; margin-bottom: 4px; text-decoration: line-through;'
        : 'background-color: #ffebe9; color: #24292f; padding: 2px 4px; border-radius: 3px; margin-bottom: 4px; text-decoration: line-through;';
      
      removedHtml += `<div style="${removedStyle}"><span style="display: inline-block; width: 16px; text-align: center; margin-right: 8px; color: ${isDark ? '#8c8c8c' : 'rgba(0,0,0,0.5)'}">-</span>${escapeHtml(line)}</div>`;
    }
    
    if (removedHtml) {
      const removedSectionStyle = isDark
        ? 'margin-bottom: 16px; padding: 8px; background-color: rgba(99, 47, 52, 0.2); border-radius: 4px;'
        : 'margin-bottom: 16px; padding: 8px; background-color: rgba(255, 235, 233, 0.4); border-radius: 4px;';
      
      diffHtml = `<div style="${removedSectionStyle}"><div style="font-weight: bold; margin-bottom: 8px;">Removed Content:</div>${removedHtml}</div>` + diffHtml;
    }
  }
  
  return diffHtml;
}

// Helper to escape HTML
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function ResumeDiffView({ resumeDiff, jobTitle, plan }: ResumeDiffViewProps) {
  const [showChanges, setShowChanges] = useState(true);
  const [activeTab, setActiveTab] = useState<'diff' | 'original' | 'customized'>('diff');
  const [visibleSections, setVisibleSections] = useState<Record<string, boolean>>({});
  const { theme } = useTheme();
  
  // Determine if dark mode is active for the diff viewer
  const isDarkMode = theme === 'dark';
  
  // Debug log to see what's in resumeDiff
  console.log("ResumeDiffView received resumeDiff:", resumeDiff);
  
  // Toggle a section visibility
  const toggleSection = (section: string) => {
    setVisibleSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };
  
  // Simulate ATS scoring data
  const atsImprovement = {
    originalScore: Math.max(35, Math.floor(Math.random() * 70) + 10),
    get newScore() { return Math.min(99, this.originalScore + Math.floor(Math.random() * 15) + 5); },
    get improvement() { return this.newScore - this.originalScore; }
  };
  
  // Custom styling for the diff viewer
  const diffViewerStyles = {
    variables: {
      light: {
        diffViewerBackground: '#ffffff',
        diffViewerColor: '#212121',
        addedBackground: '#e6ffec',
        addedColor: '#24292f',
        removedBackground: '#ffebe9',
        removedColor: '#24292f',
        wordAddedBackground: '#abf2bc',
        wordRemovedBackground: '#ffc0bd',
        addedGutterBackground: '#ccffd8',
        removedGutterBackground: '#ffdce0',
        gutterBackground: '#f5f7f9',
        gutterBackgroundDark: '#edf0f2',
        codeFoldGutterBackground: '#d0d7de',
        codeFoldBackground: '#e9ecef',
        emptyLineBackground: '#fafbfc',
        gutterColor: '#212121',
        addedGutterColor: '#24292f',
        removedGutterColor: '#24292f',
        gutterPadding: '10px',
        highlightBackground: '#fffbdd',
        highlightGutterBackground: '#fff5b1',
        diffViewerTitleBackground: '#fafbfc',
        diffViewerTitleColor: '#212529',
        diffViewerTitleBorderColor: '#eee',
      },
      dark: {
        diffViewerBackground: '#1e1e1e',
        diffViewerColor: '#f5f5f5',
        addedBackground: '#0d2616',
        addedColor: '#88c967',
        removedBackground: '#340e0e',
        removedColor: '#ee6962',
        wordAddedBackground: '#13472c',
        wordRemovedBackground: '#541a1f',
        addedGutterBackground: '#164729',
        removedGutterBackground: '#541a1f',
        gutterBackground: '#1e1e1e',
        gutterBackgroundDark: '#262626',
        codeFoldGutterBackground: '#444444',
        codeFoldBackground: '#444444',
        emptyLineBackground: '#2e2e2e',
        gutterColor: '#9e9e9e',
        addedGutterColor: '#88c967',
        removedGutterColor: '#ee6962',
        gutterPadding: '10px',
        highlightBackground: '#594e00',
        highlightGutterBackground: '#524a0a',
        diffViewerTitleBackground: '#2f323e',
        diffViewerTitleColor: '#555a7b',
        diffViewerTitleBorderColor: '#353846',
      },
    },
    line: {
      padding: '8px 2px',
      minHeight: '20px',
    },
    contentText: {
      fontFamily: '"Menlo", "Monaco", "Courier New", monospace',
      lineHeight: '1.5',
    },
    marker: {
      width: '8px',
    },
  };
  
  // Format section analysis with additional explanations
  const renderSectionAnalysis = () => {
    // Log the section analysis data for debugging
    console.log("Section analysis:", resumeDiff.section_analysis);
    
    // Only show section analysis if it exists
    if (!resumeDiff.section_analysis || Object.keys(resumeDiff.section_analysis).length === 0) {
      console.log("No section analysis data found");
      return (
        <div className="text-center text-muted-foreground py-4">
          <div className="mb-2">No section analysis available</div>
          <div className="text-sm">This may be because the backend did not provide section-level analysis data.</div>
        </div>
      );
    }
    
    // Log the first section to check its structure
    const firstSectionKey = Object.keys(resumeDiff.section_analysis)[0];
    const firstSection = resumeDiff.section_analysis[firstSectionKey];
    console.log("First section data:", firstSectionKey, firstSection);
    
    // Process the actual section analysis data
    return renderSectionAnalysisContent(resumeDiff.section_analysis);
  };
  
  // Helper function to actually render the section analysis
  const renderSectionAnalysisContent = (sectionData: Record<string, any>) => {
    // Log the received section data for debugging
    console.log("renderSectionAnalysisContent received:", sectionData);
    
    // Sample section explanations (in a real app, these would come from the backend)
    const sectionExplanations: Record<string, string> = plan?.change_explanations || {
      "Skills": "Enhanced skills section to add industry-specific keywords and highlight technical expertise.",
      "Experience": "Improved job descriptions with more targeted achievements and metrics.",
      "Summary": "Tailored professional summary to better match the job requirements.",
      "Education": "Adjusted education formatting for better ATS readability.",
      "Technical Skills": "Added relevant technical keywords and frameworks mentioned in the job description.",
      "Projects": "Highlighted projects that align with the job requirements and showcase relevant skills."
    };
    
    // Sample ATS improvement explanations (in a real app, these would come from the backend)
    const atsImprovements: Record<string, string[]> = {
      "Skills": [
        "Added missing technical keywords from job description",
        "Re-ordered skills to prioritize most relevant ones first",
        "Standardized formatting for better ATS parsing"
      ],
      "Experience": [
        "Added quantifiable metrics to demonstrate impact",
        "Used terminology matching the job description",
        "Highlighted leadership and collaboration aspects"
      ],
      "Summary": [
        "Targeted opening statement to position role alignment",
        "Included key qualifications mentioned in job posting",
        "Emphasized unique value proposition"
      ],
      "Education": [
        "Standardized formatting of education credentials",
        "Added relevant coursework"
      ],
      "Technical Skills": [
        "Added in-demand skills mentioned in the job posting",
        "Organized skills by relevance to the position",
        "Included specific versions and expertise levels"
      ],
      "Projects": [
        "Emphasized projects that showcase relevant skills",
        "Added measurable outcomes and achievements",
        "Used industry-specific terminology from the job posting"
      ]
    };
    
    return (
      <div className="space-y-6">
        {Object.entries(sectionData).map(([section, analysis]) => {
          const isExpanded = visibleSections[section] || false;
          
          // Log each section's analysis data
          console.log(`Section ${section} analysis:`, analysis);
          
          // Get section metrics safely, ensuring we have default values
          // The backend may provide these directly or nested in stats
          let changesCount = 0;
          let additionsCount = 0; 
          let deletionsCount = 0;
          
          // Check if properties exist directly on the section analysis
          if ('changes' in analysis) {
            changesCount = analysis.changes;
          } else if (analysis.stats && 'modifications' in analysis.stats) {
            changesCount = analysis.stats.modifications;
          }
          
          if ('additions' in analysis) {
            additionsCount = analysis.additions;
          } else if (analysis.stats && 'additions' in analysis.stats) {
            additionsCount = analysis.stats.additions;
          }
          
          if ('deletions' in analysis) {
            deletionsCount = analysis.deletions;
          } else if (analysis.stats && 'deletions' in analysis.stats) {
            deletionsCount = analysis.stats.deletions;
          }
          
          return (
            <div key={section} className="border rounded-md overflow-hidden">
              <div 
                className="p-4 cursor-pointer hover:bg-muted/60 transition-colors"
                onClick={() => toggleSection(section)}
              >
                <div className="flex justify-between items-center">
                  <h4 className="font-medium">{section}</h4>
                  <Button variant="ghost" size="sm" className="p-1 h-auto">
                    {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </div>
                
                <div className="grid grid-cols-3 gap-2 text-sm mt-2">
                  <div className="flex flex-col items-center p-2 rounded-md bg-muted">
                    <span className="text-muted-foreground">Changes</span>
                    <span className="text-lg font-semibold">{changesCount}</span>
                  </div>
                  <div className="flex flex-col items-center p-2 rounded-md bg-green-50 dark:bg-green-950">
                    <span className="text-green-700 dark:text-green-300">Added</span>
                    <span className="text-lg font-semibold text-green-700 dark:text-green-300">
                      {additionsCount}
                    </span>
                  </div>
                  <div className="flex flex-col items-center p-2 rounded-md bg-red-50 dark:bg-red-950">
                    <span className="text-red-700 dark:text-red-300">Removed</span>
                    <span className="text-lg font-semibold text-red-700 dark:text-red-300">
                      {deletionsCount}
                    </span>
                  </div>
                </div>
                
                {/* Display section explanation if available */}
                {sectionExplanations[section] && (
                  <p className="mt-3 text-sm text-muted-foreground">
                    {sectionExplanations[section]}
                  </p>
                )}
                
                {/* Display status if available from backend */}
                {analysis.status && !sectionExplanations[section] && (
                  <p className="mt-3 text-sm text-muted-foreground">
                    {analysis.status.replace(/_/g, ' ')}
                    {analysis.change_percentage && ` (${analysis.change_percentage}% changed)`}
                  </p>
                )}
              </div>
              
              {isExpanded && atsImprovements[section] && (
                <div className="p-4 bg-muted/30 border-t">
                  <h5 className="text-sm font-medium mb-2">ATS Improvements</h5>
                  <ul className="space-y-2">
                    {atsImprovements[section].map((improvement, i) => (
                      <li key={i} className="flex items-start">
                        <Check className="h-4 w-4 text-green-600 mt-0.5 mr-2 flex-shrink-0" />
                        <span className="text-sm">{improvement}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };
  
  // Render keywords section
  const renderKeywords = () => {
    // Mock data - in a real app this would come from backend analysis
    const addedKeywords = ['leadership', 'cloud infrastructure', 'strategic planning', 'system design'];
    const matchingKeywords = ['React', 'JavaScript', 'TypeScript', 'Node.js', 'API design'];
    
    return (
      <div className="space-y-4">
        <div>
          <h4 className="text-sm font-medium mb-2">Added Keywords</h4>
          <div className="flex flex-wrap gap-2">
            {addedKeywords.map((keyword, i) => (
              <div key={i} className="px-2 py-1 text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full">
                {keyword}
              </div>
            ))}
          </div>
        </div>
        
        <div>
          <h4 className="text-sm font-medium mb-2">Matching Job Requirements</h4>
          <div className="flex flex-wrap gap-2">
            {matchingKeywords.map((keyword, i) => (
              <div key={i} className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full flex items-center">
                <Check className="h-3 w-3 mr-1" />
                {keyword}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };
  
  // If no diff data is available
  if (!resumeDiff) {
    return (
      <div className="text-center text-muted-foreground p-8">
        No difference data available
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* ATS Score Improvement */}
      <Card className="bg-gradient-to-r from-primary/5 to-primary/10">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">ATS Compatibility Improvement</CardTitle>
          <CardDescription>
            {jobTitle 
              ? `Resume optimized specifically for: ${jobTitle}`
              : 'Resume optimized for the selected job description'
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="text-center">
                <div className="text-sm text-muted-foreground">Before</div>
                <div className="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
                  {atsImprovement.originalScore}%
                </div>
              </div>
              
              <ArrowUpDown className="h-5 w-5 text-muted-foreground mx-1" />
              
              <div className="text-center">
                <div className="text-sm text-muted-foreground">After</div>
                <div className="text-3xl font-bold text-green-600 dark:text-green-400">
                  {atsImprovement.newScore}%
                </div>
              </div>
              
              <div className="ml-4 px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full flex items-center">
                <ArrowUpDown className="h-3 w-3 mr-1" />
                +{atsImprovement.improvement}%
              </div>
            </div>
            
            <p className="text-sm text-muted-foreground text-center max-w-md mt-2">
              ATS systems are more likely to select your resume with these customizations, 
              improving your chances of reaching the interview stage.
            </p>
          </div>
        </CardContent>
      </Card>
      
      {/* Statistics Card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Change Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col items-center justify-center p-4 rounded-md bg-muted">
              <span className="text-2xl font-bold">
                {resumeDiff.diff_statistics.modifications}
              </span>
              <span className="text-sm text-muted-foreground">Modifications</span>
            </div>
            <div className="flex flex-col items-center justify-center p-4 rounded-md bg-green-50 dark:bg-green-950">
              <span className="text-2xl font-bold text-green-700 dark:text-green-300">
                {resumeDiff.diff_statistics.additions}
              </span>
              <span className="text-sm text-green-700 dark:text-green-300">Additions</span>
            </div>
            <div className="flex flex-col items-center justify-center p-4 rounded-md bg-red-50 dark:bg-red-950">
              <span className="text-2xl font-bold text-red-700 dark:text-red-300">
                {resumeDiff.diff_statistics.deletions}
              </span>
              <span className="text-sm text-red-700 dark:text-red-300">Deletions</span>
            </div>
          </div>
          
          {/* Added keyword analysis section */}
          <div className="mt-6">
            {renderKeywords()}
          </div>
        </CardContent>
      </Card>
      
      {/* Section Analysis */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Section-by-Section Analysis</CardTitle>
          <CardDescription>
            Click on each section to see detailed analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          {renderSectionAnalysis()}
        </CardContent>
      </Card>
      
      {/* Diff Content */}
      <div className="space-y-2">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold">Detailed Changes</h3>
          <div className="flex items-center space-x-2">
            <Switch 
              id="show-changes" 
              checked={showChanges} 
              onCheckedChange={setShowChanges} 
            />
            <Label htmlFor="show-changes" className="text-sm">
              {showChanges ? "Showing changes" : "Showing original"}
            </Label>
          </div>
        </div>
        
        <Card>
          <CardContent className="p-0">
            <div className="max-h-[600px] overflow-auto">
              <div className="p-4">
                {showChanges ? (
                  <>
                    {/* Add a debug check for the diff content */}
                    {console.log("Rendering diff with:", {
                      originalLength: resumeDiff.original_content?.length || 0, 
                      customizedLength: resumeDiff.customized_content?.length || 0
                    })}
                    
                    {/* Create a custom diff view with tabs that fit the design system */}
                    {resumeDiff.original_content && resumeDiff.customized_content ? (
                      <div className="custom-diff-viewer rounded-lg border bg-card text-card-foreground overflow-hidden">
                        <div className="flex border-b">
                          <button
                            className={`px-4 py-3 text-sm font-medium transition-colors relative ${
                              activeTab === 'diff' 
                                ? 'text-primary' 
                                : 'text-muted-foreground hover:text-foreground'
                            }`}
                            onClick={() => setActiveTab('diff')}
                          >
                            Changes
                            {activeTab === 'diff' && (
                              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"></span>
                            )}
                          </button>
                          <button
                            className={`px-4 py-3 text-sm font-medium transition-colors relative ${
                              activeTab === 'customized' 
                                ? 'text-primary' 
                                : 'text-muted-foreground hover:text-foreground'
                            }`}
                            onClick={() => setActiveTab('customized')}
                          >
                            Customized Resume
                            {activeTab === 'customized' && (
                              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"></span>
                            )}
                          </button>
                          <button
                            className={`px-4 py-3 text-sm font-medium transition-colors relative ${
                              activeTab === 'original' 
                                ? 'text-primary' 
                                : 'text-muted-foreground hover:text-foreground'
                            }`}
                            onClick={() => setActiveTab('original')}
                          >
                            Original Resume
                            {activeTab === 'original' && (
                              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"></span>
                            )}
                          </button>
                        </div>
                        
                        <div className="p-4 font-mono text-sm leading-relaxed whitespace-pre-wrap overflow-auto max-h-[500px]">
                          {activeTab === 'diff' && (
                            <div dangerouslySetInnerHTML={{ 
                              __html: createDiffHtml(
                                resumeDiff.original_content,
                                resumeDiff.customized_content,
                                isDarkMode
                              ) 
                            }} />
                          )}
                          
                          {activeTab === 'customized' && (
                            <pre className="m-0 font-mono">
                              {resumeDiff.customized_content}
                            </pre>
                          )}
                          
                          {activeTab === 'original' && (
                            <pre className="m-0 font-mono">
                              {resumeDiff.original_content}
                            </pre>
                          )}
                        </div>
                    ) : (
                      <div className="p-4 bg-muted rounded-md">
                        <p className="text-muted-foreground">
                          Diff cannot be displayed. Missing original or customized content.
                        </p>
                      </div>
                    )}
                  </>
                ) : (
                  <pre className="font-mono text-sm whitespace-pre-wrap">
                    {resumeDiff.original_content || "No original content available"}
                  </pre>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}