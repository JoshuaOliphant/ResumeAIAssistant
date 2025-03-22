import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function Home() {
  return (
    <div className="space-y-12">
      <section className="py-12 md:py-24 lg:py-32 flex flex-col items-center text-center">
        <div className="container px-4 md:px-6">
          <div className="space-y-4 md:space-y-6">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tighter">
              Optimize Your Resume with AI
            </h1>
            <p className="mx-auto max-w-[700px] text-gray-600 dark:text-gray-400 md:text-xl">
              Get personalized insights and recommendations to improve your resume and increase your chances of landing your dream job.
            </p>
            <div className="space-x-4">
              <Button asChild size="lg">
                <Link href="/analyze">Analyze Your Resume</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link href="/how-it-works">Learn More</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      <section className="container px-4 md:px-6 py-12">
        <h2 className="text-3xl font-bold text-center mb-8">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Upload</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Upload your resume and the job description you're applying for.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Analyze</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Our AI analyzes your resume against the job description using advanced NLP techniques.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Optimize</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Get actionable recommendations to improve your resume and increase your chances of getting an interview.</p>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="container px-4 md:px-6 py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <h2 className="text-3xl font-bold text-center mb-8">Key Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>ATS Optimization</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Ensure your resume passes through Applicant Tracking Systems with our ATS-focused analysis.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Keyword Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Identify missing keywords and phrases that are crucial for your target position.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Section Improvement</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Get section-by-section feedback to strengthen every part of your resume.</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Format Checking</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Ensure your resume follows industry best practices for formatting and structure.</p>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
