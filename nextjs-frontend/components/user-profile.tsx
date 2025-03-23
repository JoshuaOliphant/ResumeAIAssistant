"use client"

import * as React from "react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { AlertCircle, Loader2, CheckCircle2 } from "lucide-react"
import { useAuth } from "@/lib/auth"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

// Define profile form schema with zod
const profileFormSchema = z.object({
  email: z.string()
    .email({ message: "Please enter a valid email address" }),
  username: z.string()
    .min(3, { message: "Username must be at least 3 characters" })
    .max(50, { message: "Username must be less than 50 characters" })
    .regex(/^[a-zA-Z0-9._-]+$/, { message: "Username can only contain letters, numbers, and ._-" }),
  fullName: z.string()
    .max(100, { message: "Full name must be less than 100 characters" })
    .optional(),
})

// Define password change form schema with zod
const passwordFormSchema = z.object({
  currentPassword: z.string()
    .min(1, { message: "Current password is required" }),
  newPassword: z.string()
    .min(8, { message: "Password must be at least 8 characters" })
    .regex(/[A-Z]/, { message: "Password must contain at least one uppercase letter" })
    .regex(/[a-z]/, { message: "Password must contain at least one lowercase letter" })
    .regex(/[0-9]/, { message: "Password must contain at least one number" }),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
})

type ProfileFormValues = z.infer<typeof profileFormSchema>
type PasswordFormValues = z.infer<typeof passwordFormSchema>

export function UserProfile() {
  const { user } = useAuth()
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false)
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [profileError, setProfileError] = useState<string | null>(null)
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [profileSuccess, setProfileSuccess] = useState(false)
  const [passwordSuccess, setPasswordSuccess] = useState(false)
  
  // Profile form setup
  const profileForm = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      email: user?.email || "",
      username: user?.username || "",
      fullName: user?.full_name || "",
    },
  })
  
  // Password form setup
  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordFormSchema),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
  })
  
  // Get user initials for avatar
  const getInitials = () => {
    if (!user) return "?"
    
    if (user.full_name) {
      return user.full_name
        .split(" ")
        .map(n => n[0])
        .join("")
        .toUpperCase()
        .substring(0, 2)
    }
    
    return user.username.substring(0, 2).toUpperCase()
  }
  
  // Handle profile form submission
  async function onProfileSubmit(values: ProfileFormValues) {
    setIsUpdatingProfile(true)
    setProfileError(null)
    setProfileSuccess(false)
    
    try {
      // Normally we would call an API here
      // For now, we'll simulate a successful update
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      setProfileSuccess(true)
      
      // Reset success message after a delay
      setTimeout(() => {
        setProfileSuccess(false)
      }, 3000)
    } catch (err) {
      console.error("Profile update failed:", err)
      setProfileError("Failed to update profile. Please try again.")
    } finally {
      setIsUpdatingProfile(false)
    }
  }
  
  // Handle password form submission
  async function onPasswordSubmit(values: PasswordFormValues) {
    setIsChangingPassword(true)
    setPasswordError(null)
    setPasswordSuccess(false)
    
    try {
      // Normally we would call an API here
      // For now, we'll simulate a successful update
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      setPasswordSuccess(true)
      passwordForm.reset()
      
      // Reset success message after a delay
      setTimeout(() => {
        setPasswordSuccess(false)
      }, 3000)
    } catch (err) {
      console.error("Password change failed:", err)
      setPasswordError("Failed to change password. Please make sure your current password is correct.")
    } finally {
      setIsChangingPassword(false)
    }
  }
  
  if (!user) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }
  
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Avatar className="h-20 w-20">
          <AvatarFallback className="text-2xl">{getInitials()}</AvatarFallback>
        </Avatar>
        <div>
          <h1 className="text-2xl font-bold">{user.full_name || user.username}</h1>
          <p className="text-muted-foreground">{user.email}</p>
        </div>
      </div>
      
      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="mb-6">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="password">Password</TabsTrigger>
        </TabsList>
        
        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>
                Update your account profile information
              </CardDescription>
            </CardHeader>
            
            <Form {...profileForm}>
              <form onSubmit={profileForm.handleSubmit(onProfileSubmit)}>
                <CardContent className="space-y-4">
                  {/* Email field */}
                  <FormField
                    control={profileForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Email Address</FormLabel>
                        <FormControl>
                          <Input 
                            type="email"
                            placeholder="your.email@example.com" 
                            {...field}
                            disabled={isUpdatingProfile}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  {/* Username field */}
                  <FormField
                    control={profileForm.control}
                    name="username"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Username</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="username" 
                            {...field}
                            disabled={isUpdatingProfile}
                          />
                        </FormControl>
                        <FormDescription>
                          This is your public display name
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  {/* Full Name field */}
                  <FormField
                    control={profileForm.control}
                    name="fullName"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Full Name</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="John Doe" 
                            {...field}
                            value={field.value || ""}
                            disabled={isUpdatingProfile}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  {/* Error message */}
                  {profileError && (
                    <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm flex items-start">
                      <AlertCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                      <div>{profileError}</div>
                    </div>
                  )}
                  
                  {/* Success message */}
                  {profileSuccess && (
                    <div className="bg-success/10 text-success p-3 rounded-md text-sm flex items-start">
                      <CheckCircle2 className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                      <div>Profile updated successfully!</div>
                    </div>
                  )}
                </CardContent>
                
                <CardFooter>
                  <Button 
                    type="submit" 
                    disabled={isUpdatingProfile}
                  >
                    {isUpdatingProfile ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      "Save Changes"
                    )}
                  </Button>
                </CardFooter>
              </form>
            </Form>
          </Card>
        </TabsContent>
        
        <TabsContent value="password">
          <Card>
            <CardHeader>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>
                Update your account password
              </CardDescription>
            </CardHeader>
            
            <Form {...passwordForm}>
              <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)}>
                <CardContent className="space-y-4">
                  {/* Current Password field */}
                  <FormField
                    control={passwordForm.control}
                    name="currentPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Current Password</FormLabel>
                        <FormControl>
                          <Input 
                            type="password"
                            placeholder="••••••••" 
                            {...field}
                            disabled={isChangingPassword}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  {/* New Password field */}
                  <FormField
                    control={passwordForm.control}
                    name="newPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>New Password</FormLabel>
                        <FormControl>
                          <Input 
                            type="password"
                            placeholder="••••••••" 
                            {...field}
                            disabled={isChangingPassword}
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
                    control={passwordForm.control}
                    name="confirmPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Confirm New Password</FormLabel>
                        <FormControl>
                          <Input 
                            type="password"
                            placeholder="••••••••" 
                            {...field}
                            disabled={isChangingPassword}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  {/* Error message */}
                  {passwordError && (
                    <div className="bg-destructive/10 text-destructive p-3 rounded-md text-sm flex items-start">
                      <AlertCircle className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                      <div>{passwordError}</div>
                    </div>
                  )}
                  
                  {/* Success message */}
                  {passwordSuccess && (
                    <div className="bg-success/10 text-success p-3 rounded-md text-sm flex items-start">
                      <CheckCircle2 className="w-4 h-4 mr-2 mt-0.5 flex-shrink-0" />
                      <div>Password changed successfully!</div>
                    </div>
                  )}
                </CardContent>
                
                <CardFooter>
                  <Button 
                    type="submit" 
                    disabled={isChangingPassword}
                  >
                    {isChangingPassword ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Updating...
                      </>
                    ) : (
                      "Change Password"
                    )}
                  </Button>
                </CardFooter>
              </form>
            </Form>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}