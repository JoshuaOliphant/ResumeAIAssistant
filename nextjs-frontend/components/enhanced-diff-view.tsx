"use client"

import { useState } from "react"
import ReactDiffViewer from 'react-diff-viewer-continued'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Download, GitCompare, FileText, Eye } from "lucide-react"
import { useTheme } from "next-themes"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface EnhancedDiffViewProps {
  original: string;
  customized: string;
  title?: string;
  jobTitle?: string;
}

export function EnhancedDiffView({ original, customized, title, jobTitle }: EnhancedDiffViewProps) {
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('split');
  const { theme } = useTheme();
  
  // Custom styles for the diff viewer
  const customStyles = {
    variables: {
      light: {
        diffViewerBackground: '#ffffff',
        diffViewerColor: '#212529',
        addedBackground: '#e6ffed',
        addedColor: '#24292e',
        removedBackground: '#ffeef0',
        removedColor: '#24292e',
        wordAddedBackground: '#acf2bd',
        wordRemovedBackground: '#fdb8c0',
        addedGutterBackground: '#cdffd8',
        removedGutterBackground: '#ffdce0',
        gutterBackground: '#f6f8fa',
        gutterBackgroundDark: '#f0f1f3',
        highlightBackground: '#fffbdd',
        highlightGutterBackground: '#fff5b1',
        codeFoldGutterBackground: '#dbedff',
        codeFoldBackground: '#f1f8ff',
        emptyLineBackground: '#fafbfc',
        gutterColor: '#212529',
        addedGutterColor: '#28a745',
        removedGutterColor: '#dc3545',
      },
      dark: {
        diffViewerBackground: '#0d1117',
        diffViewerColor: '#c9d1d9',
        addedBackground: '#0d4429',
        addedColor: '#c9d1d9',
        removedBackground: '#5d1f26',
        removedColor: '#c9d1d9',
        wordAddedBackground: '#1c7c3c',
        wordRemovedBackground: '#8c2929',
        addedGutterBackground: '#034525',
        removedGutterBackground: '#5d0f12',
        gutterBackground: '#161b22',
        gutterBackgroundDark: '#101418',
        highlightBackground: '#2d333b',
        highlightGutterBackground: '#2d333b',
        codeFoldGutterBackground: '#1c2128',
        codeFoldBackground: '#262c36',
        emptyLineBackground: '#161b22',
        gutterColor: '#8b949e',
        addedGutterColor: '#7ee787',
        removedGutterColor: '#ffa198',
      }
    },
    gutter: {
      minWidth: 50,
      padding: '0 10px',
      textAlign: 'center',
    },
    line: {
      padding: '0 10px',
      minWidth: 0,
    },
    codeFold: {
      fontSize: 12,
    }
  };

  const handleDownload = () => {
    const blob = new Blob([customized], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `customized_resume_${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Calculate diff statistics
  const calculateStats = () => {
    const originalLines = original.split('\n');
    const customizedLines = customized.split('\n');
    
    // Simple stats calculation (you could use a more sophisticated diff algorithm)
    const maxLines = Math.max(originalLines.length, customizedLines.length);
    let additions = 0;
    let deletions = 0;
    let modifications = 0;
    
    // Count additions and deletions
    if (customizedLines.length > originalLines.length) {
      additions = customizedLines.length - originalLines.length;
    } else if (originalLines.length > customizedLines.length) {
      deletions = originalLines.length - customizedLines.length;
    }
    
    // Count modifications (simplified - lines that exist in both but are different)
    const minLines = Math.min(originalLines.length, customizedLines.length);
    for (let i = 0; i < minLines; i++) {
      if (originalLines[i] !== customizedLines[i]) {
        modifications++;
      }
    }
    
    return { additions, deletions, modifications };
  };

  const stats = calculateStats();

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{title || "Resume Comparison"}</CardTitle>
              <CardDescription>
                {jobTitle 
                  ? `Comparing original resume with version customized for: ${jobTitle}`
                  : 'Comparing original and customized resume versions'
                }
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Statistics */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-green-600 dark:text-green-400">Additions</p>
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">+{stats.additions}</p>
              </div>
              <Badge variant="outline" className="text-green-600 dark:text-green-400">Added</Badge>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-red-600 dark:text-red-400">Deletions</p>
                <p className="text-2xl font-bold text-red-600 dark:text-red-400">-{stats.deletions}</p>
              </div>
              <Badge variant="outline" className="text-red-600 dark:text-red-400">Removed</Badge>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-yellow-600 dark:text-yellow-400">Changes</p>
                <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">~{stats.modifications}</p>
              </div>
              <Badge variant="outline" className="text-yellow-600 dark:text-yellow-400">Modified</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Diff Viewer */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Document Changes</CardTitle>
            <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'split' | 'unified')}>
              <TabsList>
                <TabsTrigger value="split">
                  <GitCompare className="h-4 w-4 mr-2" />
                  Split View
                </TabsTrigger>
                <TabsTrigger value="unified">
                  <FileText className="h-4 w-4 mr-2" />
                  Unified View
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="max-h-[600px] overflow-auto">
            <ReactDiffViewer
              oldValue={original}
              newValue={customized}
              splitView={viewMode === 'split'}
              useDarkTheme={theme === 'dark'}
              styles={customStyles}
              compareMethod="diffWords"
              leftTitle="Original Resume"
              rightTitle="Customized Resume"
              hideLineNumbers={false}
              showDiffOnly={false}
              extraLinesSurroundingDiff={3}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}