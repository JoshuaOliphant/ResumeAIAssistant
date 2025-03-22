import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function ApiDocsPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">API Documentation</h1>
      
      <div className="space-y-8">
        <section>
          <p className="text-lg mb-6">
            The Resume AI Assistant API allows you to integrate our resume analysis capabilities into your own applications.
            Below you'll find documentation for all available endpoints.
          </p>
          
          <Tabs defaultValue="analyze">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="analyze">Resume Analysis</TabsTrigger>
              <TabsTrigger value="auth">Authentication</TabsTrigger>
              <TabsTrigger value="history">User History</TabsTrigger>
            </TabsList>
            
            <TabsContent value="analyze" className="p-4 border rounded-md mt-2">
              <h2 className="text-xl font-semibold mb-4">Resume Analysis Endpoints</h2>
              
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>POST /api/analyze</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="mb-4">Analyze a resume against a job description.</p>
                  
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-medium">Request Body:</h3>
                      <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
{`{
  "resume": "Full resume text...",
  "job_description": "Full job description text..."
}`}
                      </pre>
                    </div>
                    
                    <div>
                      <h3 className="font-medium">Response:</h3>
                      <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
{`{
  "analysis_id": "abc123",
  "match_score": 75,
  "keyword_matches": ["python", "react", "typescript"],
  "missing_keywords": ["docker", "kubernetes"],
  "section_scores": {
    "summary": 80,
    "experience": 70,
    "skills": 85,
    "education": 90
  },
  "suggestions": [
    "Add experience with Docker to your technical skills",
    "Emphasize cloud deployment experience in your work history"
  ]
}`}
                      </pre>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle>GET /api/analysis/{"{analysis_id}"}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="mb-4">Retrieve a specific analysis by ID.</p>
                  
                  <div>
                    <h3 className="font-medium">Response:</h3>
                    <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
{`{
  "analysis_id": "abc123",
  "created_at": "2025-03-22T12:34:56Z",
  "match_score": 75,
  "keyword_matches": ["python", "react", "typescript"],
  "missing_keywords": ["docker", "kubernetes"],
  "section_scores": {
    "summary": 80,
    "experience": 70,
    "skills": 85,
    "education": 90
  },
  "suggestions": [
    "Add experience with Docker to your technical skills",
    "Emphasize cloud deployment experience in your work history"
  ]
}`}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="auth" className="p-4 border rounded-md mt-2">
              <h2 className="text-xl font-semibold mb-4">Authentication Endpoints</h2>
              
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>POST /api/auth/register</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="mb-4">Register a new user account.</p>
                  
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-medium">Request Body:</h3>
                      <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
{`{
  "email": "user@example.com",
  "password": "secure_password",
  "name": "John Doe"
}`}
                      </pre>
                    </div>
                    
                    <div>
                      <h3 className="font-medium">Response:</h3>
                      <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
{`{
  "user_id": "user123",
  "email": "user@example.com",
  "name": "John Doe"
}`}
                      </pre>
                    </div>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle>POST /api/auth/login</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="mb-4">Authenticate a user and receive an access token.</p>
                  
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-medium">Request Body:</h3>
                      <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
{`{
  "email": "user@example.com",
  "password": "secure_password"
}`}
                      </pre>
                    </div>
                    
                    <div>
                      <h3 className="font-medium">Response:</h3>
                      <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
{`{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "user_id": "user123",
    "email": "user@example.com",
    "name": "John Doe"
  }
}`}
                      </pre>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="history" className="p-4 border rounded-md mt-2">
              <h2 className="text-xl font-semibold mb-4">User History Endpoints</h2>
              
              <Card>
                <CardHeader>
                  <CardTitle>GET /api/history</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="mb-4">Retrieve analysis history for the authenticated user.</p>
                  
                  <div>
                    <h3 className="font-medium">Response:</h3>
                    <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
{`{
  "analyses": [
    {
      "analysis_id": "abc123",
      "created_at": "2025-03-22T12:34:56Z",
      "job_title": "Senior Frontend Developer",
      "match_score": 75
    },
    {
      "analysis_id": "def456",
      "created_at": "2025-03-20T10:22:33Z",
      "job_title": "Full Stack Engineer",
      "match_score": 82
    }
  ]
}`}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </section>
        
        <section>
          <h2 className="text-2xl font-semibold mb-4">API Authentication</h2>
          <p className="mb-4">
            All API requests (except for registration and login) require authentication using a bearer token.
          </p>
          
          <Card>
            <CardHeader>
              <CardTitle>Authentication Header</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-4">Include the following header with all authenticated requests:</p>
              <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto">
{`Authorization: Bearer YOUR_ACCESS_TOKEN`}
              </pre>
            </CardContent>
          </Card>
        </section>
        
        <section>
          <h2 className="text-2xl font-semibold mb-4">Rate Limiting</h2>
          <p>
            The API is rate-limited to 100 requests per hour per user. If you exceed this limit,
            you'll receive a 429 Too Many Requests response.
          </p>
        </section>
      </div>
    </div>
  );
}
