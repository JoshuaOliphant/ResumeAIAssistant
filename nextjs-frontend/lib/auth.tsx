"use client"

import { createContext, useState, useContext, useEffect, ReactNode, useCallback } from "react"
import { useRouter } from "next/navigation"
import { AuthService, User, ApiError } from "@/lib/client"
import { AUTH_DEV_MODE, MOCK_USER, MOCK_TOKEN } from "@/lib/auth-dev"

type AuthContextType = {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<boolean>
  error: string | null
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<number>(0)
  const router = useRouter()

  // Refresh token handler
  const refreshToken = useCallback(async (): Promise<boolean> => {
    try {
      // For development mode
      if (AUTH_DEV_MODE) {
        console.log("Using development mode authentication")
        
        // Set development token if not present
        if (typeof window !== 'undefined' && !localStorage.getItem("auth_token")) {
          localStorage.setItem("auth_token", MOCK_TOKEN)
        }
        
        // Set mock user
        setUser(MOCK_USER)
        setLastRefresh(Date.now())
        return true
      }
      
      // Production mode - check if we have a token
      const token = localStorage.getItem("auth_token")
      
      if (token) {
        // Fetch current user data
        const userData = await AuthService.getCurrentUser()
        setUser(userData)
        setLastRefresh(Date.now())
        return true
      }
      return false
    } catch (err) {
      console.error("Auth refresh failed:", err)
      // Only clear token if it's an authentication error
      if (err instanceof ApiError && err.status === 401) {
        if (typeof window !== 'undefined') {
          localStorage.removeItem("auth_token")
        }
        setUser(null)
      }
      return false
    }
  }, [])

  // Check if user is logged in on mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        await refreshToken()
      } finally {
        setIsLoading(false)
      }
    }

    checkAuthStatus()
  }, [])
  
  // Refresh authentication periodically
  useEffect(() => {
    // Skip in dev mode or if no user
    if (AUTH_DEV_MODE || !user) return
    
    // Refresh token more frequently (every 5 minutes) to prevent expiration during long operations
    const refreshInterval = setInterval(() => {
      console.log('Periodic token refresh');
      refreshToken().then(success => {
        console.log(`Periodic token refresh ${success ? 'succeeded' : 'failed'}`);
      });
    }, 5 * 60 * 1000) // 5 minutes
    
    return () => clearInterval(refreshInterval)
  }, [user, refreshToken])

  const login = async (username: string, password: string) => {
    setIsLoading(true)
    setError(null)
    
    // For development mode
    if (AUTH_DEV_MODE) {
      console.log("Using development mode login")
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 800))
      
      // Set development token
      if (typeof window !== 'undefined') {
        localStorage.setItem("auth_token", MOCK_TOKEN)
      }
      
      // Set mock user
      setUser(MOCK_USER)
      
      // Redirect to home page after login
      router.push("/")
      setIsLoading(false)
      return
    }
    
    try {
      // Call login API
      await AuthService.login({ username, password })
      
      // Fetch user data after successful login
      const userData = await AuthService.getCurrentUser()
      setUser(userData)
      
      // Redirect to home page after login
      router.push("/")
    } catch (err: any) {
      console.error("Login failed:", err)
      setError(err.message || "Login failed. Please check your credentials.")
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (email: string, username: string, password: string, fullName?: string) => {
    setIsLoading(true)
    setError(null)
    
    // For development mode
    if (AUTH_DEV_MODE) {
      console.log("Using development mode registration")
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 800))
      
      // Set development token
      if (typeof window !== 'undefined') {
        localStorage.setItem("auth_token", MOCK_TOKEN)
      }
      
      // Create mock user with provided details
      const devUser = {
        ...MOCK_USER,
        email,
        username,
        full_name: fullName || MOCK_USER.full_name
      };
      
      // Set mock user
      setUser(devUser)
      
      // Redirect to home page after registration
      router.push("/")
      setIsLoading(false)
      return
    }
    
    try {
      // Call register API
      await AuthService.register({
        email,
        username,
        password,
        full_name: fullName
      })
      
      // Login after successful registration
      await AuthService.login({ username, password })
      
      // Fetch user data
      const userData = await AuthService.getCurrentUser()
      setUser(userData)
      
      // Redirect to home page after registration
      router.push("/")
    } catch (err: any) {
      console.error("Registration failed:", err)
      setError(err.message || "Registration failed. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    // Development mode or not, we'll clear localStorage
    AuthService.logout()
    setUser(null)
    router.push("/login")
  }

  const clearError = () => {
    setError(null)
  }

  // Expose auth context to window for API client to access
  useEffect(() => {
    if (typeof window !== 'undefined') {
      (window as any).__auth_context = {
        refreshToken
      };
    }
    
    return () => {
      if (typeof window !== 'undefined') {
        delete (window as any).__auth_context;
      }
    };
  }, [refreshToken]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshToken,
        error,
        clearError
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  
  return context
}