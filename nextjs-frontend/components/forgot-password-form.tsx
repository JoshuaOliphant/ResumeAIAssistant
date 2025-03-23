"use client"

import * as React from "react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { AlertCircle, ArrowLeft, Loader2, CheckCircle2 } from "lucide-react"

// Define form schema with zod
const forgotPasswordFormSchema = z.object({
  email: z.string()
    .email({ message: "Please enter a valid email address" }),
})

export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordFormSchema>

export function ForgotPasswordForm() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  
  // Form setup with react-hook-form and zod validation
  const form = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordFormSchema),
    defaultValues: {
      email: "",
    },
  })
  
  // Handle form submission
  async function onSubmit(values: ForgotPasswordFormValues) {
    setIsSubmitting(true)
    setError(null)
    
    try {
      // Normally we would call an API here
      // For now, we'll simulate a successful request
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      setSuccess(true)
      form.reset()
    } catch (err) {
      console.error("Password reset request failed:", err)
      setError("Failed to send password reset link. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }
  
  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle>Reset Your Password</CardTitle>
        <CardDescription>
          Enter your email address and we'll send you a link to reset your password
        </CardDescription>
      </CardHeader>
      
      {success ? (
        <CardContent className="space-y-4">
          <div className="bg-success/10 text-success p-4 rounded-md flex items-start">
            <CheckCircle2 className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Check your email</p>
              <p className="text-sm mt-1">
                We've sent a password reset link to your email address. Please check your inbox and follow the instructions.
              </p>
            </div>
          </div>
          
          <div className="text-center mt-4">
            <Link href="/login">
              <Button variant="outline" className="mt-2">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Sign In
              </Button>
            </Link>
          </div>
        </CardContent>
      ) : (
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              {/* Email field */}
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input 
                        type="email"
                        placeholder="Enter your email address" 
                        {...field}
                        disabled={isSubmitting}
                        autoComplete="email"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              {/* Error message */}
              {error && (
                <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm flex items-start">
                  <AlertCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                  <div>{error}</div>
                </div>
              )}
            </CardContent>
            
            <CardFooter className="flex flex-col space-y-4">
              <Button 
                type="submit" 
                className="w-full"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Sending...
                  </>
                ) : (
                  "Send Reset Link"
                )}
              </Button>
              
              <div className="text-center text-sm">
                <Link href="/login" className="text-primary hover:underline flex items-center justify-center">
                  <ArrowLeft className="w-4 h-4 mr-1" />
                  Back to Sign In
                </Link>
              </div>
            </CardFooter>
          </form>
        </Form>
      )}
    </Card>
  )
}