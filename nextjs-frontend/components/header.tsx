"use client"

import Link from 'next/link'
import { Menu, LogIn } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/theme-toggle'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { useAuth } from '@/lib/auth'
import { UserMenu } from '@/components/user-menu'
import { NotificationBadge } from '@/components/notification-badge'

const navigation = [
  { name: 'Features', href: '/#features' },
  { name: 'How It Works', href: '/#how-it-works' },
  { name: 'Resumes', href: '/resumes' },
  { name: 'Jobs', href: '/jobs' },
  { name: 'ATS Analysis', href: '/ats' },
  { name: 'Customize Resume', href: '/customize' },
  { name: 'API Docs', href: '/api/docs' },
]

export default function Header() {
  const { isAuthenticated, isLoading } = useAuth()

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto py-4 px-4 flex justify-between items-center">
        <Link href="/" className="font-bold text-xl flex items-center gap-2">
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            className="h-6 w-6 text-primary"
          >
            <path d="M18 8a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8z" />
            <path d="M8 10h8" />
            <path d="M8 14h4" />
          </svg>
          <span>Resume Customizer</span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-6">
          {navigation.map((item) => (
            <Link 
              key={item.name}
              href={item.href} 
              className="text-sm font-medium hover:text-primary transition-colors"
            >
              {item.name}
            </Link>
          ))}
          <ThemeToggle />
          
          {!isLoading && (
            <>
              {isAuthenticated ? (
                <>
                  <NotificationBadge />
                  <UserMenu />
                </>
              ) : (
                <Button asChild size="sm">
                  <Link href="/login">
                    <LogIn className="w-4 h-4 mr-2" />
                    Sign In
                  </Link>
                </Button>
              )}
            </>
          )}
        </nav>

        {/* Mobile Navigation */}
        <div className="md:hidden flex items-center gap-2">
          <ThemeToggle />
          
          {!isLoading && isAuthenticated && (
            <>
              <NotificationBadge />
              <UserMenu />
            </>
          )}
          
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Menu">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right">
              <SheetHeader>
                <SheetTitle>Resume Customizer</SheetTitle>
              </SheetHeader>
              <nav className="flex flex-col gap-4 mt-6">
                {navigation.map((item) => (
                  <Link 
                    key={item.name}
                    href={item.href} 
                    className="text-sm font-medium hover:text-primary transition-colors p-2 -ml-2 rounded-md hover:bg-accent"
                  >
                    {item.name}
                  </Link>
                ))}
                
                {!isLoading && !isAuthenticated && (
                  <Link 
                    href="/login" 
                    className="text-sm font-medium hover:text-primary transition-colors p-2 -ml-2 rounded-md hover:bg-accent flex items-center"
                  >
                    <LogIn className="w-4 h-4 mr-2" />
                    Sign In
                  </Link>
                )}
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  )
}