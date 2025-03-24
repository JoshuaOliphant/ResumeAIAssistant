"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import Link from "next/link"
import { useEffect } from "react"
import { 
  FileCheck, FileText, PenTool, FileType, 
  Upload, ClipboardList, BarChart2, FileOutput, Download
} from "lucide-react"

export default function Home() {
  // Add smooth scrolling for navigation links
  useEffect(() => {
    const handleSmoothScroll = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      const href = target.getAttribute('href')
      
      if (href && href.startsWith('#')) {
        e.preventDefault()
        const element = document.getElementById(href.substring(1))
        if (element) {
          window.scrollTo({
            top: element.offsetTop - 80, // Offset for header
            behavior: 'smooth'
          })
        }
      }
    }

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', handleSmoothScroll as EventListener)
    })

    return () => {
      document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.removeEventListener('click', handleSmoothScroll as EventListener)
      })
    }
  }, [])

  return (
    <div className="space-y-16">
      {/* Hero Section with Gradient Background */}
      <section className="py-16 md:py-24 relative overflow-hidden">
        {/* Gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-accent/5 to-background -z-10"></div>
        
        {/* Animated background elements */}
        <div className="absolute top-20 right-10 w-64 h-64 bg-primary/5 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-10 left-10 w-72 h-72 bg-accent/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        
        <div className="max-w-4xl mx-auto space-y-8 px-4 animate-fade-in">
          <h1 className="text-4xl md:text-6xl font-bold text-center leading-tight">
            AI-Powered Resume <span className="text-primary">Customization</span>
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground text-center max-w-3xl mx-auto">
            Tailor your resume to any job description using Claude AI, optimize for ATS systems, 
            and create matching cover letters.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4 pt-4 animate-slide-up">
            <Button asChild size="lg" className="text-lg shadow-lg hover:shadow-xl transition-all">
              <Link href="/resumes/new">Get Started</Link>
            </Button>
            <Button variant="outline" size="lg" asChild className="text-lg border-2 hover:bg-secondary/50 transition-all">
              <Link href="#how-it-works">Learn More</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-16 px-4">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold">Powerful Features</h2>
          <p className="text-xl text-muted-foreground mt-4 max-w-2xl mx-auto">
            Everything you need to optimize your resume and stand out from the competition
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-7xl mx-auto">
          <Card className="transition-all duration-300 hover:shadow-lg hover:border-primary/50 group">
            <CardHeader className="space-y-2">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-all">
                <FileCheck className="w-6 h-6 text-primary" />
              </div>
              <CardTitle className="text-xl">ATS Compatibility</CardTitle>
            </CardHeader>
            <CardContent>
              <p>
                <Link href="/ats" className="text-primary hover:underline">
                  Analyze and optimize
                </Link>{" "}
                your resume for Applicant Tracking Systems with detailed keyword matching and formatting checks.
              </p>
            </CardContent>
          </Card>

          <Card className="transition-all duration-300 hover:shadow-lg hover:border-primary/50 group">
            <CardHeader className="space-y-2">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-all">
                <PenTool className="w-6 h-6 text-primary" />
              </div>
              <CardTitle className="text-xl">AI Customization</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Tailor your resume for specific job descriptions using Claude AI for intelligent customization and keyword optimization.</p>
            </CardContent>
          </Card>

          <Card className="transition-all duration-300 hover:shadow-lg hover:border-primary/50 group">
            <CardHeader className="space-y-2">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-all">
                <FileText className="w-6 h-6 text-primary" />
              </div>
              <CardTitle className="text-xl">Cover Letters</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Generate personalized cover letters that match your resume and the target job description with perfect tone and formatting.</p>
            </CardContent>
          </Card>

          <Card className="transition-all duration-300 hover:shadow-lg hover:border-primary/50 group">
            <CardHeader className="space-y-2">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-all">
                <FileType className="w-6 h-6 text-primary" />
              </div>
              <CardTitle className="text-xl">Multiple Formats</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Export your optimized resume in multiple formats including PDF, DOCX, and Markdown for maximum compatibility with job portals.</p>
            </CardContent>
          </Card>
        </div>
      </section>
      
      {/* How It Works Section with visual process */}
      <section id="how-it-works" className="py-16 px-4 bg-muted/50">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold">How It Works</h2>
          <p className="text-xl text-muted-foreground mt-4 max-w-2xl mx-auto">
            A simple 5-step process to transform your resume and boost your job search
          </p>
        </div>
        
        {/* Process visualization */}
        <div className="max-w-6xl mx-auto relative">
          {/* Connection line (hidden on mobile) */}
          <div className="hidden lg:block absolute top-24 left-[10%] right-[10%] h-1 bg-primary/20 z-0"></div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-4">
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold mb-6 shadow-lg">
                <Upload className="w-7 h-7" />
              </div>
              <h3 className="text-xl font-semibold mb-3">1. Upload Resume</h3>
              <p className="text-muted-foreground">Upload your existing resume in PDF or Markdown format to get started.</p>
            </div>
            
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold mb-6 shadow-lg">
                <ClipboardList className="w-7 h-7" />
              </div>
              <h3 className="text-xl font-semibold mb-3">2. Add Job Description</h3>
              <p className="text-muted-foreground">Paste the job description or provide a URL to automatically import requirements.</p>
            </div>
            
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold mb-6 shadow-lg">
                <BarChart2 className="w-7 h-7" />
              </div>
              <h3 className="text-xl font-semibold mb-3">3. Get ATS Analysis</h3>
              <p className="text-muted-foreground">
                <Link href="/ats" className="text-primary hover:underline">
                  Analyze your resume
                </Link> 
                {" "}to see how well it matches the job requirements with detailed scoring.
              </p>
            </div>
            
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold mb-6 shadow-lg">
                <FileOutput className="w-7 h-7" />
              </div>
              <h3 className="text-xl font-semibold mb-3">4. Customize & Generate</h3>
              <p className="text-muted-foreground">Let Claude AI optimize your resume and create a matching cover letter.</p>
            </div>
            
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="w-16 h-16 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold mb-6 shadow-lg">
                <Download className="w-7 h-7" />
              </div>
              <h3 className="text-xl font-semibold mb-3">5. Download & Apply</h3>
              <p className="text-muted-foreground">Export your tailored documents in your preferred format and apply with confidence.</p>
            </div>
          </div>
          
          {/* Process illustration */}
          <div className="mt-16 bg-card rounded-lg border shadow-md p-8 flex justify-center">
            <div className="w-full max-w-3xl h-64 bg-muted rounded-md flex items-center justify-center">
              <p className="text-muted-foreground text-center">Interactive process visualization will appear here</p>
            </div>
          </div>
        </div>
      </section>
      
      {/* CTA Section with gradient background */}
      <section className="py-16 px-4 rounded-lg relative overflow-hidden">
        {/* Gradient background */}
        <div className="absolute inset-0 bg-gradient-to-r from-primary/10 to-accent/10 -z-10 rounded-2xl"></div>
        
        <div className="max-w-4xl mx-auto text-center space-y-6 p-8">
          <h2 className="text-3xl md:text-4xl font-bold">Ready to optimize your resume?</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Start customizing your resume with AI today to increase your interview callbacks by up to 60%.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" asChild className="text-lg px-8 py-6 h-auto shadow-lg hover:shadow-xl transition-all">
              <Link href="/resumes/new">Get Started Now</Link>
            </Button>
            <Button size="lg" asChild variant="outline" className="text-lg px-8 py-6 h-auto hover:bg-secondary/50 transition-all">
              <Link href="/ats">Analyze Your Resume</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  )
}