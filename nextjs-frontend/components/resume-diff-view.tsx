"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ResumeDiff } from "@/lib/client"
import { 
  Download, Layers, GitBranch, FileText, Hash, Eye, EyeOff
} from "lucide-react"
import { useTheme } from "next-themes"

export interface ResumeDiffViewProps {
  resumeDiff: ResumeDiff;
  jobTitle?: string;
  plan?: { change_explanations?: Record<string, string> } | null;
}

interface DiffLine {
  lineNumber: number;
  type: 'unchanged' | 'added' | 'removed' | 'modified';
  content: string;
  originalContent?: string;
}

// Parse content into lines with diff annotations
function parseContentToDiffLines(original: string, customized: string): {
  originalLines: DiffLine[];
  customizedLines: DiffLine[];
} {
  const originalLines = original.split('\n');
  const customizedLines = customized.split('\n');
  
  const maxLength = Math.max(originalLines.length, customizedLines.length);
  const parsedOriginal: DiffLine[] = [];
  const parsedCustomized: DiffLine[] = [];
  
  for (let i = 0; i < maxLength; i++) {
    const origLine = originalLines[i] || '';
    const custLine = customizedLines[i] || '';
    
    if (origLine === custLine) {
      parsedOriginal.push({ lineNumber: i + 1, type: 'unchanged', content: origLine });
      parsedCustomized.push({ lineNumber: i + 1, type: 'unchanged', content: custLine });
    } else if (origLine && !custLine) {
      parsedOriginal.push({ lineNumber: i + 1, type: 'removed', content: origLine });
      parsedCustomized.push({ lineNumber: i + 1, type: 'removed', content: '' });
    } else if (!origLine && custLine) {
      parsedOriginal.push({ lineNumber: i + 1, type: 'added', content: '' });
      parsedCustomized.push({ lineNumber: i + 1, type: 'added', content: custLine });
    } else {
      parsedOriginal.push({ lineNumber: i + 1, type: 'modified', content: origLine, originalContent: origLine });
      parsedCustomized.push({ lineNumber: i + 1, type: 'modified', content: custLine, originalContent: origLine });
    }
  }
  
  return { originalLines: parsedOriginal, customizedLines: parsedCustomized };
}

export function ResumeDiffView({ resumeDiff, jobTitle, plan }: ResumeDiffViewProps) {
  const [viewMode, setViewMode] = useState<'side-by-side' | 'unified' | 'inline'>('side-by-side');
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [highlightChanges, setHighlightChanges] = useState(true);
  const { theme } = useTheme();
  
  const leftPanelRef = useRef<HTMLDivElement>(null);
  const rightPanelRef = useRef<HTMLDivElement>(null);
  
  // Parse diff lines
  const { originalLines, customizedLines } = useMemo(() => {
    if (!resumeDiff?.original_content || !resumeDiff?.customized_content) {
      return { originalLines: [], customizedLines: [] };
    }
    return parseContentToDiffLines(resumeDiff.original_content, resumeDiff.customized_content);
  }, [resumeDiff]);
  
  // Calculate statistics
  const stats = useMemo(() => {
    const additions = customizedLines.filter(l => l.type === 'added').length;
    const deletions = originalLines.filter(l => l.type === 'removed').length;
    const modifications = customizedLines.filter(l => l.type === 'modified').length;
    const total = additions + deletions + modifications;
    
    return { additions, deletions, modifications, total };
  }, [originalLines, customizedLines]);
  
  // Synchronized scrolling for side-by-side view
  useEffect(() => {
    const leftPanel = leftPanelRef.current;
    const rightPanel = rightPanelRef.current;
    
    if (!leftPanel || !rightPanel || viewMode !== 'side-by-side') return;
    
    const syncScroll = (source: HTMLDivElement, target: HTMLDivElement) => {
      const scrollPercentage = source.scrollTop / (source.scrollHeight - source.clientHeight);
      target.scrollTop = scrollPercentage * (target.scrollHeight - target.clientHeight);
    };
    
    const handleLeftScroll = () => syncScroll(leftPanel, rightPanel);
    const handleRightScroll = () => syncScroll(rightPanel, leftPanel);
    
    leftPanel.addEventListener('scroll', handleLeftScroll);
    rightPanel.addEventListener('scroll', handleRightScroll);
    
    return () => {
      leftPanel.removeEventListener('scroll', handleLeftScroll);
      rightPanel.removeEventListener('scroll', handleRightScroll);
    };
  }, [viewMode]);
  
  // Line rendering function
  const renderLine = (line: DiffLine, isOriginal: boolean = false) => {
    const getLineStyle = () => {
      if (!highlightChanges) return '';
      
      switch (line.type) {
        case 'added':
          return isOriginal ? 'opacity-0' : 'bg-green-50 dark:bg-green-950/30 border-l-4 border-green-500';
        case 'removed':
          return isOriginal ? 'bg-red-50 dark:bg-red-950/30 border-l-4 border-red-500' : 'opacity-0';
        case 'modified':
          return 'bg-yellow-50 dark:bg-yellow-950/30 border-l-4 border-yellow-500';
        default:
          return '';
      }
    };
    
    return (
      <div 
        key={line.lineNumber}
        className={`flex ${getLineStyle()} transition-all duration-200`}
      >
        {showLineNumbers && (
          <span className="w-12 px-2 text-xs text-muted-foreground text-right border-r">
            {line.lineNumber}
          </span>
        )}
        <pre className="flex-1 px-3 py-1 font-mono text-sm whitespace-pre-wrap">
          {line.content || '\u00A0'}
        </pre>
      </div>
    );
  };
  
  // Download customized resume
  const handleDownload = () => {
    const blob = new Blob([resumeDiff.customized_content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `customized_resume_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };
  
  if (!resumeDiff) {
    return (
      <div className="text-center text-muted-foreground p-8">
        No difference data available
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Header with Job Context */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Resume Customization Results</span>
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4 mr-1" />
              Download Resume
            </Button>
          </CardTitle>
          <CardDescription>
            {jobTitle 
              ? `Resume has been customized for: ${jobTitle}`
              : 'Resume has been customized for the selected job description'
            }
          </CardDescription>
        </CardHeader>
      </Card>
      
      {/* Change Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Changes</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Hash className="h-8 w-8 text-muted-foreground/20" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-green-200 dark:border-green-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-600">Additions</p>
                <p className="text-2xl font-bold text-green-600">{stats.additions}</p>
              </div>
              <Badge variant="outline" className="text-green-600">+</Badge>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-red-200 dark:border-red-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-red-600">Deletions</p>
                <p className="text-2xl font-bold text-red-600">{stats.deletions}</p>
              </div>
              <Badge variant="outline" className="text-red-600">−</Badge>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-yellow-200 dark:border-yellow-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-yellow-600 dark:text-yellow-500">Modifications</p>
                <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-500">{stats.modifications}</p>
              </div>
              <Badge variant="outline" className="text-yellow-600 dark:text-yellow-500">~</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Diff Content */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Document Changes</h3>
          <div className="flex items-center gap-4">
            <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as any)} className="w-auto">
              <TabsList className="grid grid-cols-3">
                <TabsTrigger value="side-by-side">
                  <Layers className="h-4 w-4 mr-1" />
                  Side by Side
                </TabsTrigger>
                <TabsTrigger value="unified">
                  <GitBranch className="h-4 w-4 mr-1" />
                  Unified
                </TabsTrigger>
                <TabsTrigger value="inline">
                  <FileText className="h-4 w-4 mr-1" />
                  Inline
                </TabsTrigger>
              </TabsList>
            </Tabs>
            
            <div className="flex items-center gap-3 text-sm">
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={showLineNumbers}
                  onChange={(e) => setShowLineNumbers(e.target.checked)}
                  className="rounded"
                />
                Lines
              </label>
              <label className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={highlightChanges}
                  onChange={(e) => setHighlightChanges(e.target.checked)}
                  className="rounded"
                />
                Highlights
              </label>
            </div>
          </div>
        </div>
        
        {/* Side by Side View */}
        {viewMode === 'side-by-side' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="py-3 px-4 border-b">
                <CardTitle className="text-base">Original Resume</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div 
                  ref={leftPanelRef}
                  className="max-h-[600px] overflow-auto"
                >
                  {originalLines.map(line => renderLine(line, true))}
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader className="py-3 px-4 border-b">
                <CardTitle className="text-base text-green-600">Customized Resume</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div 
                  ref={rightPanelRef}
                  className="max-h-[600px] overflow-auto"
                >
                  {customizedLines.map(line => renderLine(line))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        
        {/* Unified View */}
        {viewMode === 'unified' && (
          <Card>
            <CardContent className="p-0">
              <div className="max-h-[600px] overflow-auto">
                {customizedLines.map((line, idx) => {
                  const origLine = originalLines[idx];
                  
                  if (line.type === 'unchanged') {
                    return renderLine(line);
                  }
                  
                  return (
                    <div key={line.lineNumber}>
                      {origLine && origLine.type !== 'added' && renderLine(origLine, true)}
                      {line.type !== 'removed' && renderLine(line)}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* Inline View */}
        {viewMode === 'inline' && (
          <Card>
            <CardContent className="p-0">
              <div className="max-h-[600px] overflow-auto p-4">
                <pre className="font-mono text-sm whitespace-pre-wrap">
                  {resumeDiff.customized_content}
                </pre>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}