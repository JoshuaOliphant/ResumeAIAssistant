import dynamic from 'next/dynamic'

// Import the client-side home page component with no SSR
const HomeClient = dynamic(() => import('./page-client'), { ssr: false })

export default function Home() {
  return <HomeClient />
}