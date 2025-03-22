import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HowItWorksPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">How Resume AI Assistant Works</h1>
      
      <div className="space-y-12">
        <section>
          <h2 className="text-2xl font-semibold mb-4">Our Advanced ATS Analysis</h2>
          <p className="text-lg mb-6">
            Resume AI Assistant uses advanced Natural Language Processing (NLP) to analyze your resume against job descriptions, 
            providing insights that help you optimize your application for Applicant Tracking Systems (ATS).
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Semantic Matching</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  We go beyond simple keyword matching to understand the semantic meaning of your skills and experiences,
                  identifying matches even when terms aren't identical.
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>Section-Based Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  Our system analyzes each section of your resume independently, providing targeted feedback
                  for your professional summary, work experience, skills, and education.
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
        
        <section>
          <h2 className="text-2xl font-semibold mb-4">The Analysis Process</h2>
          
          <ol className="space-y-8">
            <li className="bg-gray-50 p-6 rounded-lg">
              <h3 className="text-xl font-medium mb-2">1. Document Processing</h3>
              <p>
                We extract and process the text from your resume and the job description, breaking them down into
                analyzable components while preserving their structure.
              </p>
            </li>
            
            <li className="bg-gray-50 p-6 rounded-lg">
              <h3 className="text-xl font-medium mb-2">2. Keyword and Skill Extraction</h3>
              <p>
                Our NLP engine identifies key skills, qualifications, and requirements from the job description,
                then searches for matching elements in your resume.
              </p>
            </li>
            
            <li className="bg-gray-50 p-6 rounded-lg">
              <h3 className="text-xl font-medium mb-2">3. Multi-Factor Scoring</h3>
              <p>
                We evaluate your resume across multiple dimensions, including keyword match, content relevance,
                section completeness, and formatting best practices.
              </p>
            </li>
            
            <li className="bg-gray-50 p-6 rounded-lg">
              <h3 className="text-xl font-medium mb-2">4. Actionable Recommendations</h3>
              <p>
                Based on our analysis, we provide specific, actionable suggestions to improve your resume,
                focusing on the changes that will have the biggest impact on your application success.
              </p>
            </li>
          </ol>
        </section>
        
        <section>
          <h2 className="text-2xl font-semibold mb-4">Industry-Specific Insights</h2>
          <p className="text-lg mb-6">
            Our analysis adapts to different industries and position levels, recognizing that resume expectations
            vary across fields and career stages.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Tech Industry</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  For tech roles, we emphasize technical skills, certifications, and project experience,
                  helping you highlight your most relevant technical qualifications.
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>Business & Finance</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  For business positions, we focus on quantifiable achievements, leadership experience,
                  and relevant industry knowledge.
                </p>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>Creative Fields</CardTitle>
              </CardHeader>
              <CardContent>
                <p>
                  For creative roles, we help you balance showcasing your portfolio work with the
                  professional experience and skills that hiring managers seek.
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}
