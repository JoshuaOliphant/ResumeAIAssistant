'use client'

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4 text-center px-6">
      <div className="space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Something went wrong</h2>
        <p className="text-muted-foreground">
          We apologize for the inconvenience. An error occurred while trying to render this page.
        </p>
      </div>
      <div className="flex gap-2">
        <Button onClick={() => reset()} variant="default">
          Try again
        </Button>
        <Button onClick={() => window.location.href = '/'} variant="outline">
          Go home
        </Button>
      </div>
    </div>
  )
}