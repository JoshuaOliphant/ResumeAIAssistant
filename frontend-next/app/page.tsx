import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import Link from "next/link"

export default function Home() {
  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="py-12 md:py-20 text-center">
        <div className="max-w-3xl mx-auto space-y-6">
          <h1 className="text-4xl md:text-5xl font-bold">AI-Powered Resume Customization</h1>
          <p className="text-xl text-muted-foreground">
            Tailor your resume to any job description using Claude AI, optimize for ATS systems, 
            and create matching cover letters.
          </p>
          <div className="flex justify-center gap-4 pt-4">
            <Button asChild size="lg">
              <Link href="/analyze">Get Started</Link>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="#how-it-works">Learn More</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-12">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold">Features</h2>
          <p className="text-muted-foreground mt-2">Everything you need to optimize your resume</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>ATS Compatibility</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Analyze and optimize your resume for Applicant Tracking Systems with detailed keyword matching.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI Customization</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Tailor your resume for specific job descriptions using Claude AI for intelligent customization.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Cover Letters</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Generate personalized cover letters that match your resume and the target job description.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Multiple Formats</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Export your optimized resume in multiple formats including PDF, DOCX, and Markdown.</p>
            </CardContent>
          </Card>
        </div>
      </section>
      
      {/* How It Works Section */}
      <section id="how-it-works" className="py-12">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold">How It Works</h2>
          <p className="text-muted-foreground mt-2">A simple process to optimize your resume</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
          <div className="flex flex-col items-center text-center">
            <div className="bg-primary text-primary-foreground w-10 h-10 rounded-full flex items-center justify-center font-bold mb-4">1</div>
            <h3 className="font-semibold mb-2">Upload Resume</h3>
            <p className="text-muted-foreground">Upload your existing resume in Markdown format.</p>
          </div>
          
          <div className="flex flex-col items-center text-center">
            <div className="bg-primary text-primary-foreground w-10 h-10 rounded-full flex items-center justify-center font-bold mb-4">2</div>
            <h3 className="font-semibold mb-2">Add Job Description</h3>
            <p className="text-muted-foreground">Paste a job description or provide a URL to import it.</p>
          </div>
          
          <div className="flex flex-col items-center text-center">
            <div className="bg-primary text-primary-foreground w-10 h-10 rounded-full flex items-center justify-center font-bold mb-4">3</div>
            <h3 className="font-semibold mb-2">Get ATS Analysis</h3>
            <p className="text-muted-foreground">See how well your resume matches the job requirements.</p>
          </div>
          
          <div className="flex flex-col items-center text-center">
            <div className="bg-primary text-primary-foreground w-10 h-10 rounded-full flex items-center justify-center font-bold mb-4">4</div>
            <h3 className="font-semibold mb-2">Customize & Generate</h3>
            <p className="text-muted-foreground">Let AI optimize your resume and create a cover letter.</p>
          </div>
          
          <div className="flex flex-col items-center text-center">
            <div className="bg-primary text-primary-foreground w-10 h-10 rounded-full flex items-center justify-center font-bold mb-4">5</div>
            <h3 className="font-semibold mb-2">Download & Apply</h3>
            <p className="text-muted-foreground">Export your customized documents and apply with confidence.</p>
          </div>
        </div>
      </section>
      
      {/* CTA Section */}
      <section className="py-12 bg-muted rounded-lg p-8 text-center">
        <h2 className="text-2xl font-bold mb-4">Ready to optimize your resume?</h2>
        <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
          Start customizing your resume with AI to increase your chances of landing interviews.
        </p>
        <Button size="lg" asChild>
          <Link href="/analyze">Get Started Now</Link>
        </Button>
      </section>
    </div>
  )
}