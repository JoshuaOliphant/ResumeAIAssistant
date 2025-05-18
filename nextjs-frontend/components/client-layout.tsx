"use client"

import React from 'react'
import dynamic from 'next/dynamic'
import { AuthProvider } from '@/lib/auth'
import { ProtectedRoute } from '@/components/protected-route'

// Load header and footer dynamically
const Header = dynamic(() => import('@/components/header'))
const Footer = dynamic(() => import('@/components/footer'))

interface ClientLayoutProps {
  children: React.ReactNode
}

export default function ClientLayout({ children }: ClientLayoutProps) {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <div className="flex min-h-screen flex-col bg-background text-foreground">
          <Header />
          <main className="flex-1 container mx-auto px-4 py-8">
            {children}
          </main>
          <Footer />
        </div>
      </ProtectedRoute>
    </AuthProvider>
  )
}