"use client"

import * as React from "react"
import { useCallback, useState } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Upload, X, FileText } from "lucide-react"

export interface FileUploadProps extends React.HTMLAttributes<HTMLDivElement> {
  accept?: string
  maxSize?: number
  onFileSelect: (file: File) => void
  onFileContent?: (content: string) => void
  error?: string
}

const FileUpload = React.forwardRef<HTMLDivElement, FileUploadProps>(
  ({ className, accept = ".md", maxSize = 10485760, onFileSelect, onFileContent, error, ...props }, ref) => {
    const [dragActive, setDragActive] = useState(false)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const [fileError, setFileError] = useState<string | null>(null)
    
    const inputRef = React.useRef<HTMLInputElement>(null)
    
    const validateFile = (file: File): boolean => {
      // Check file type
      if (accept) {
        const fileType = file.name.split('.').pop()?.toLowerCase() || ""
        const acceptedTypes = accept.split(',').map(type => 
          type.trim().replace('.', '').toLowerCase()
        )
        
        if (!acceptedTypes.includes(fileType)) {
          setFileError(`Invalid file type. Accepted: ${accept}`)
          return false
        }
      }
      
      // Check file size
      if (maxSize && file.size > maxSize) {
        const sizeMB = Math.round(maxSize / 1024 / 1024)
        setFileError(`File too large. Maximum size: ${sizeMB}MB`)
        return false
      }
      
      setFileError(null)
      return true
    }
    
    const handleFile = (file: File) => {
      if (validateFile(file)) {
        setSelectedFile(file)
        onFileSelect(file)
        
        // If we need to read the file content
        if (onFileContent) {
          const reader = new FileReader()
          reader.onload = (e) => {
            const content = e.target?.result as string
            onFileContent(content)
          }
          reader.readAsText(file)
        }
      }
    }
    
    const handleDrag = useCallback((e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      e.stopPropagation()
      
      if (e.type === "dragenter" || e.type === "dragover") {
        setDragActive(true)
      } else if (e.type === "dragleave") {
        setDragActive(false)
      }
    }, [])
    
    const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)
      
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFile(e.dataTransfer.files[0])
      }
    }, [])
    
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      e.preventDefault()
      
      if (e.target.files && e.target.files[0]) {
        handleFile(e.target.files[0])
      }
    }
    
    const handleButtonClick = () => {
      inputRef.current?.click()
    }
    
    const handleRemoveFile = () => {
      setSelectedFile(null)
      if (inputRef.current) {
        inputRef.current.value = ""
      }
    }
    
    const displayError = error || fileError
    
    return (
      <div
        ref={ref}
        className={cn(
          "relative flex flex-col items-center justify-center w-full",
          className
        )}
        {...props}
      >
        {!selectedFile ? (
          <div
            className={cn(
              "flex flex-col items-center justify-center w-full p-6 border-2 border-dashed rounded-lg cursor-pointer transition-colors",
              dragActive 
                ? "border-primary bg-primary/5" 
                : "border-input hover:border-primary/50 hover:bg-muted",
              displayError && "border-destructive"
            )}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={handleButtonClick}
          >
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              accept={accept}
              onChange={handleChange}
            />
            
            <div className="flex flex-col items-center justify-center text-center">
              <Upload className="w-10 h-10 mb-3 text-muted-foreground" />
              <p className="mb-2 text-sm font-medium">
                <span className="font-semibold text-primary">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-muted-foreground">
                {accept ? `${accept.replace(/\./g, "")} files only` : "Any file type"}
                {maxSize && ` (Max. ${Math.round(maxSize / 1024 / 1024)}MB)`}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between w-full p-4 border rounded-lg">
            <div className="flex items-center">
              <FileText className="w-8 h-8 mr-4 text-primary" />
              <div>
                <p className="text-sm font-medium truncate max-w-[200px]">{selectedFile.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
            
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation()
                handleRemoveFile()
              }}
              className="text-muted-foreground hover:text-destructive"
            >
              <X className="w-4 h-4" />
              <span className="sr-only">Remove file</span>
            </Button>
          </div>
        )}
        
        {displayError && (
          <p className="mt-2 text-sm text-destructive">{displayError}</p>
        )}
      </div>
    )
  }
)
FileUpload.displayName = "FileUpload"

export { FileUpload }