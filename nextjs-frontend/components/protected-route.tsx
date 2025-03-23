"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { Loader2 } from "lucide-react"

export interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    // If authentication is still loading, wait
    if (isLoading) return
    
    // If not authenticated and not already on auth pages, redirect to login
    if (!isAuthenticated && 
        !pathname.startsWith("/login") && 
        !pathname.startsWith("/register") && 
        !pathname.startsWith("/forgot-password") && 
        !pathname.startsWith("/reset-password")) {
      router.push(`/login?redirect=${encodeURIComponent(pathname)}`)
    }
  }, [isAuthenticated, isLoading, router, pathname])

  // Show loading indicator while checking auth status
  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  // If at an auth page or authenticated, render children
  if (isAuthenticated || 
      pathname.startsWith("/login") || 
      pathname.startsWith("/register") || 
      pathname.startsWith("/forgot-password") || 
      pathname.startsWith("/reset-password") ||
      pathname === "/" ||
      pathname.startsWith("/#")) {
    return <>{children}</>
  }

  // Otherwise render nothing while redirecting
  return null
}