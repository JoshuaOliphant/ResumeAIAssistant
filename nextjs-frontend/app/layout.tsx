import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/components/theme-provider'
import ClientLayout from '@/components/client-layout'

const inter = Inter({ 
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const jetBrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: {
    default: 'Resume Customizer | AI-Powered Resume Optimization',
    template: '%s | Resume Customizer'
  },
  description: 'AI-powered resume customization and optimization tool to tailor your resume for specific job descriptions using Claude AI.',
  keywords: ['resume', 'AI', 'job application', 'resume customization', 'Claude AI', 'career', 'job search'],
  authors: [
    { name: 'Resume Customizer Team' }
  ],
  creator: 'Resume Customizer',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://resume-customizer.app',
    title: 'Resume Customizer | AI-Powered Resume Optimization',
    description: 'AI-powered resume customization and optimization tool to tailor your resume for specific job descriptions using Claude AI.',
    siteName: 'Resume Customizer',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Resume Customizer | AI-Powered Resume Optimization',
    description: 'AI-powered resume customization and optimization tool to tailor your resume for specific job descriptions using Claude AI.',
  },
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: '#111827' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetBrainsMono.variable} font-sans antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <ClientLayout>
            {children}
          </ClientLayout>
        </ThemeProvider>
      </body>
    </html>
  )
}