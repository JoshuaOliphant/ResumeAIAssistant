import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import Link from "next/link";
import { BadgeCheck, FileText, PenLine, FileDown, Upload, Search, Sparkles, Download } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-16">
      {/* Hero Section with Gradient Background */}
      <section className="py-16 md:py-24 lg:py-32 flex flex-col items-center text-center relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-indigo-100 to-purple-100 dark:from-blue-950 dark:via-indigo-900 dark:to-purple-900 opacity-80"></div>
        <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-10"></div>
        <div className="container px-4 md:px-6 relative z-10">
          <div className="space-y-6 md:space-y-8 max-w-4xl mx-auto">
            <div className="animate-fade-in-up">
              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400">
                AI-Powered Resume Customization
              </h1>
            </div>
            <p className="mx-auto max-w-[700px] text-gray-700 dark:text-gray-300 md:text-xl animate-fade-in-up animation-delay-100">
              Tailor your resume for each job application using Claude AI. Get higher match scores, pass ATS systems, and land more interviews.
            </p>
            <div className="flex flex-wrap justify-center gap-4 animate-fade-in-up animation-delay-200">
              <Button asChild size="lg" className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 transition-all duration-300 shadow-lg hover:shadow-xl">
                <Link href="/resumes/new">Get Started</Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="border-2 hover:bg-gray-100/10 transition-all duration-300">
                <Link href="/how-it-works">Learn More</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid - 4 columns on desktop */}
      <section className="container px-4 md:px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Powerful Features</h2>
          <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">Everything you need to create the perfect resume for each job application</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Feature 1 */}
          <Card className="border-2 hover:border-blue-500 hover:shadow-lg transition-all duration-300">
            <CardHeader className="pb-2">
              <div className="w-12 h-12 rounded-lg bg-blue-100 dark:bg-blue-900 flex items-center justify-center mb-2">
                <BadgeCheck className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <CardTitle>ATS Compatibility</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 dark:text-gray-400">Ensure your resume passes through Applicant Tracking Systems with our ATS-focused analysis.</p>
            </CardContent>
          </Card>
          
          {/* Feature 2 */}
          <Card className="border-2 hover:border-indigo-500 hover:shadow-lg transition-all duration-300">
            <CardHeader className="pb-2">
              <div className="w-12 h-12 rounded-lg bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center mb-2">
                <Sparkles className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
              </div>
              <CardTitle>AI Customization</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 dark:text-gray-400">Leverage Claude AI to tailor your resume for each job with intelligent keyword optimization.</p>
            </CardContent>
          </Card>
          
          {/* Feature 3 */}
          <Card className="border-2 hover:border-purple-500 hover:shadow-lg transition-all duration-300">
            <CardHeader className="pb-2">
              <div className="w-12 h-12 rounded-lg bg-purple-100 dark:bg-purple-900 flex items-center justify-center mb-2">
                <PenLine className="h-6 w-6 text-purple-600 dark:text-purple-400" />
              </div>
              <CardTitle>Cover Letters</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 dark:text-gray-400">Generate personalized cover letters that complement your resume and highlight your qualifications.</p>
            </CardContent>
          </Card>
          
          {/* Feature 4 */}
          <Card className="border-2 hover:border-sky-500 hover:shadow-lg transition-all duration-300">
            <CardHeader className="pb-2">
              <div className="w-12 h-12 rounded-lg bg-sky-100 dark:bg-sky-900 flex items-center justify-center mb-2">
                <FileDown className="h-6 w-6 text-sky-600 dark:text-sky-400" />
              </div>
              <CardTitle>Multiple Formats</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 dark:text-gray-400">Download your optimized resume in multiple formats including PDF, DOCX, and plain text.</p>
            </CardContent>
          </Card>
        </div>
      </section>
      
      {/* How It Works Section - 5 steps */}
      <section className="container px-4 md:px-6 py-16 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">How It Works</h2>
          <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">Five simple steps to optimize your resume and land more interviews</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-8 relative">
          {/* Step 1 */}
          <div className="relative">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold z-10">1</div>
            <Card className="h-full border-t-4 border-blue-600 pt-6">
              <CardHeader className="pb-2">
                <div className="w-12 h-12 rounded-lg bg-blue-100 dark:bg-blue-900 flex items-center justify-center mb-2">
                  <Upload className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <CardTitle>Upload Resume</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 dark:text-gray-400">Upload your existing resume or create a new one from scratch.</p>
              </CardContent>
            </Card>
          </div>
          
          {/* Step 2 */}
          <div className="relative">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold z-10">2</div>
            <Card className="h-full border-t-4 border-indigo-600 pt-6">
              <CardHeader className="pb-2">
                <div className="w-12 h-12 rounded-lg bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center mb-2">
                  <FileText className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <CardTitle>Add Job Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 dark:text-gray-400">Paste the job description or provide a link to the job posting.</p>
              </CardContent>
            </Card>
          </div>
          
          {/* Step 3 */}
          <div className="relative">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-purple-600 text-white flex items-center justify-center font-bold z-10">3</div>
            <Card className="h-full border-t-4 border-purple-600 pt-6">
              <CardHeader className="pb-2">
                <div className="w-12 h-12 rounded-lg bg-purple-100 dark:bg-purple-900 flex items-center justify-center mb-2">
                  <Search className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <CardTitle>Get ATS Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 dark:text-gray-400">Our AI analyzes your resume against the job description using advanced NLP.</p>
              </CardContent>
            </Card>
          </div>
          
          {/* Step 4 */}
          <div className="relative">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-sky-600 text-white flex items-center justify-center font-bold z-10">4</div>
            <Card className="h-full border-t-4 border-sky-600 pt-6">
              <CardHeader className="pb-2">
                <div className="w-12 h-12 rounded-lg bg-sky-100 dark:bg-sky-900 flex items-center justify-center mb-2">
                  <Sparkles className="h-6 w-6 text-sky-600 dark:text-sky-400" />
                </div>
                <CardTitle>Customize & Generate</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 dark:text-gray-400">Get an optimized version of your resume tailored to the specific job.</p>
              </CardContent>
            </Card>
          </div>
          
          {/* Step 5 */}
          <div className="relative">
            <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-green-600 text-white flex items-center justify-center font-bold z-10">5</div>
            <Card className="h-full border-t-4 border-green-600 pt-6">
              <CardHeader className="pb-2">
                <div className="w-12 h-12 rounded-lg bg-green-100 dark:bg-green-900 flex items-center justify-center mb-2">
                  <Download className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <CardTitle>Download & Apply</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 dark:text-gray-400">Download your optimized resume and start applying with confidence.</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Call to Action Section */}
      <section className="container px-4 md:px-6 py-16">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-8 md:p-12 shadow-xl text-white">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Ready to Land Your Dream Job?</h2>
            <p className="text-lg md:text-xl mb-8 opacity-90">Start optimizing your resume today and increase your chances of getting interviews.</p>
            <Button asChild size="lg" className="bg-white text-blue-600 hover:bg-gray-100 transition-all duration-300 shadow-lg hover:shadow-xl">
              <Link href="/resumes/new">Customize Your Resume Now</Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
