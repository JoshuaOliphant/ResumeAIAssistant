"use client"

import { ReactNode } from 'react'
import { AuthProvider } from '@/lib/auth'
import { ProtectedRoute } from '@/components/protected-route'

export default function ClientAuthProviders({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <ProtectedRoute>
        {children}
      </ProtectedRoute>
    </AuthProvider>
  )
}