"use client"

import dynamic from 'next/dynamic'

// Import the client-side home page component with no SSR
const HomeClient = dynamic(() => import('@/app/page-client'), { ssr: false })

export default function PageWrapper() {
  return <HomeClient />
}