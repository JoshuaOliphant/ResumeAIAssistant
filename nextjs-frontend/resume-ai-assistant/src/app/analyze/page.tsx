"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { analyzeResume } from "@/lib/client";

// Define form schema with zod
const formSchema = z.object({
  resumeText: z.string().min(50, "Resume must be at least 50 characters"),
  jobDescription: z.string().min(20, "Job description must be at least 20 characters"),
});

export default function AnalyzePage() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  // Initialize form
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      resumeText: "",
      jobDescription: "",
    },
  });

  // Handle form submission
  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsAnalyzing(true);
    setProgress(0);
    setError("");
    setResult(null);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 10;
      });
    }, 500);

    try {
      const response = await analyzeResume(values.resumeText, values.jobDescription);
      
      clearInterval(progressInterval);
      setProgress(100);
      
      if (response.error) {
        setError(response.error);
      } else {
        setResult(response.data);
      }
    } catch (err) {
      clearInterval(progressInterval);
      setError("An unexpected error occurred. Please try again.");
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Analyze Your Resume</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Upload Information</CardTitle>
            <CardDescription>
              Paste your resume and the job description you're applying for
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <FormField
                  control={form.control}
                  name="resumeText"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Resume</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Paste your resume text here..."
                          className="min-h-[200px]"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="jobDescription"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Job Description</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Paste the job description here..."
                          className="min-h-[200px]"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <Button type="submit" disabled={isAnalyzing} className="w-full">
                  {isAnalyzing ? "Analyzing..." : "Analyze Resume"}
                </Button>
                
                {isAnalyzing && (
                  <div className="space-y-2">
                    <Progress value={progress} className="h-2" />
                    <p className="text-sm text-center text-gray-500">
                      Analyzing your resume against the job description...
                    </p>
                  </div>
                )}
                
                {error && (
                  <div className="p-4 bg-red-50 text-red-600 rounded-md">
                    {error}
                  </div>
                )}
              </form>
            </Form>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription>
              Your resume analysis will appear here
            </CardDescription>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-4">
                {/* Display analysis results here */}
                <p>Analysis results will be displayed here</p>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[400px] text-gray-400">
                Submit your resume and job description to see analysis results
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
