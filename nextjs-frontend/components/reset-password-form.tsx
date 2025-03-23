"use client"

import * as React from "react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { AlertCircle, ArrowLeft, Loader2, CheckCircle2 } from "lucide-react"

// Define form schema with zod
const resetPasswordFormSchema = z.object({
  password: z.string()
    .min(8, { message: "Password must be at least 8 characters" })
    .regex(/[A-Z]/, { message: "Password must contain at least one uppercase letter" })
    .regex(/[a-z]/, { message: "Password must contain at least one lowercase letter" })
    .regex(/[0-9]/, { message: "Password must contain at least one number" }),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
})

export type ResetPasswordFormValues = z.infer<typeof resetPasswordFormSchema>

export function ResetPasswordForm() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  
  // Form setup with react-hook-form and zod validation
  const form = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordFormSchema),
    defaultValues: {
      password: "",
      confirmPassword: "",
    },
  })
  
  // Handle form submission
  async function onSubmit(values: ResetPasswordFormValues) {
    setIsSubmitting(true)
    setError(null)
    
    // Validate token
    if (!token) {
      setError("Invalid or expired password reset token. Please request a new password reset link.")
      setIsSubmitting(false)
      return
    }
    
    try {
      // Normally we would call an API here with the token and new password
      // For now, we'll simulate a successful password reset
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      setSuccess(true)
      
      // Redirect to login after a delay
      setTimeout(() => {
        router.push("/login")
      }, 3000)
    } catch (err) {
      console.error("Password reset failed:", err)
      setError("Failed to reset password. Please try again or request a new reset link.")
    } finally {
      setIsSubmitting(false)
    }
  }
  
  // Check if token is missing
  if (!token && !success) {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardHeader>
          <CardTitle>Invalid Reset Link</CardTitle>
          <CardDescription>
            The password reset link is invalid or has expired
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-destructive/10 text-destructive p-4 rounded-md">
            <p>
              Please request a new password reset link from the 
              <Link href="/forgot-password" className="text-primary hover:underline mx-1">
                forgot password
              </Link> 
              page.
            </p>
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
      </Card>
    )
  }
  
  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle>Create New Password</CardTitle>
        <CardDescription>
          Enter a new password for your account
        </CardDescription>
      </CardHeader>
      
      {success ? (
        <CardContent className="space-y-4">
          <div className="bg-success/10 text-success p-4 rounded-md flex items-start">
            <CheckCircle2 className="w-5 h-5 mr-2 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Password reset successful</p>
              <p className="text-sm mt-1">
                Your password has been updated. You will be redirected to the login page in a few seconds.
              </p>
            </div>
          </div>
          
          <div className="text-center mt-4">
            <Link href="/login">
              <Button className="mt-2">
                Sign In Now
              </Button>
            </Link>
          </div>
        </CardContent>
      ) : (
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              {/* Password field */}
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>New Password</FormLabel>
                    <FormControl>
                      <Input 
                        type="password" 
                        placeholder="Enter new password" 
                        {...field}
                        disabled={isSubmitting}
                        autoComplete="new-password"
                      />
                    </FormControl>
                    <FormDescription>
                      At least 8 characters with uppercase, lowercase, and numbers
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              {/* Confirm Password field */}
              <FormField
                control={form.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm Password</FormLabel>
                    <FormControl>
                      <Input 
                        type="password" 
                        placeholder="Confirm new password" 
                        {...field}
                        disabled={isSubmitting}
                        autoComplete="new-password"
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
                    Resetting Password...
                  </>
                ) : (
                  "Reset Password"
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