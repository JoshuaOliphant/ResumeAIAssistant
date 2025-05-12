/**
 * API client for interacting with the Resume AI Assistant backend
 */

import { API_BASE_URL, BACKEND_API_URL, API_VERSION } from "@/lib/api-config";









// Define common types
export type User = {
  id: string;
  email: string;
  username: string;
  full_name?: string;
};

export type Resume = {
  id: string;
  title: string;
  user_id?: string;
  created_at: string;
  updated_at: string;
  current_version: ResumeVersion;
};

export type ResumeVersion = {
  id: string;
  resume_id: string;
  content: string;
  version_number: number;
  is_customized: boolean;
  job_description_id?: string;
  created_at: string;
};

export type JobDescription = {
  id: string;
  title: string;
  company?: string;
  description: string;
  user_id?: string;
  created_at: string;
  updated_at: string;
};

export type ATSAnalysisResult = {
  id: string;
  resume_id: string;
  job_description_id: string;
  match_score: number;
  matching_keywords: { keyword: string; count: number }[];
  missing_keywords: string[];
  improvement_suggestions: { [category: string]: string[] };
  
  // New fields from enhanced analysis
  improvements?: { category: string; suggestion: string; priority: number }[];
  job_type?: string;
  section_scores?: { section: string; score: number; weight: number }[];
  confidence?: string;
  keyword_density?: number;
  
  // Rich data fields for updated components
  matching_keywords_rich?: { keyword: string; count_in_resume: number; count_in_job: number; is_match: boolean }[];
  missing_keywords_rich?: { keyword: string; count_in_resume: number; count_in_job: number; is_match: boolean }[];
};

export type ResumeDiff = {
  id: string;
  title: string;
  original_content: string;
  customized_content: string;
  diff_content: string;
  diff_statistics: {
    additions: number;
    deletions: number;
    modifications: number;
  };
  section_analysis: {
    [section: string]: {
      changes: number;
      additions: number;
      deletions: number;
    };
  };
  is_diff_view: boolean;
};

// Authentication types
export type LoginCredentials = {
  username: string;
  password: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
};

// Error handling
export class ApiError extends Error {
  public status: number;
  public data: any;

  constructor(status: number, message: string, data?: any) {
    // Format the message to include data details if available
    let formattedMessage = 'An unknown error occurred';
    
    if (data?.detail) {
      if (typeof data.detail === 'string') {
        formattedMessage = data.detail;
      } else if (typeof data.detail === 'object') {
        try {
          formattedMessage = JSON.stringify(data.detail);
        } catch (e) {
          formattedMessage = 'Validation error occurred';
        }
      }
    } else if (typeof message === 'string') {
      formattedMessage = message;
    }
    
    super(formattedMessage);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

// Helper function for fetch requests
async function fetchWithAuth(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  // Get the token from localStorage
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;

  // Set up headers
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  try {
    // Ensure endpoint has correct versioning prefix
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    // Use BACKEND_API_URL with single API_VERSION to avoid double prefixing
    const fullUrl = `${BACKEND_API_URL}${API_VERSION}${cleanEndpoint}`;
    console.log(`Fetching from: ${fullUrl}`);
    const response = await fetch(fullUrl, {
      ...options,
      headers,
    });
    
    console.log(`Response status: ${response.status} ${response.statusText}`);
    
    // Read the response body
    const data = await response.json().catch((err) => {
      console.error(`Error parsing JSON: ${err.message}`);
      return {};
    });
    
    console.log(`Response data:`, data);

    // Check if the request was successful
    if (!response.ok) {
      throw new ApiError(
        response.status,
        data.detail || 'An error occurred',
        data
      );
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(500, 'Network error', error);
  }
}

// Authentication
export const AuthService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const formData = new URLSearchParams();
      formData.append('username', credentials.username);
      formData.append('password', credentials.password);

      const response = await fetch(`${BACKEND_API_URL}${API_VERSION}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });

      // Handle non-OK responses
      if (!response.ok) {
        let errorMessage = 'Login failed. Please check your credentials.';
        let errorData = {};
        
        try {
          errorData = await response.json();
          if (errorData && (errorData as any).detail) {
            errorMessage = (errorData as any).detail;
          }
        } catch (e) {
          // If parsing JSON fails, use default error message
        }
        
        throw new ApiError(
          response.status,
          errorMessage,
          errorData
        );
      }

      const data = await response.json();
      
      // Store the token in localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('auth_token', data.access_token);
      }
      
      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(500, 'Network error during login. Please try again.', error);
    }
  },

  async register(user: {
    email: string;
    username: string;
    password: string;
    full_name?: string;
  }): Promise<User> {
    try {
      const response = await fetch(`${BACKEND_API_URL}${API_VERSION}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(user),
      });

      // Handle non-OK responses
      if (!response.ok) {
        let errorMessage = 'Registration failed. Please try again.';
        let errorData = {};
        
        try {
          errorData = await response.json();
          if (errorData && (errorData as any).detail) {
            errorMessage = (errorData as any).detail;
          }
        } catch (e) {
          // If parsing JSON fails, use default error message
        }
        
        throw new ApiError(
          response.status,
          errorMessage,
          errorData
        );
      }

      return response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(500, 'Network error during registration. Please try again.', error);
    }
  },

  async getCurrentUser(): Promise<User> {
    return fetchWithAuth('/auth/me');
  },

  logout(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  },
};

// Resumes
export const ResumeService = {
  async getResumes(): Promise<Resume[]> {
    return fetchWithAuth('/resumes');
  },

  async getResume(id: string): Promise<Resume> {
    return fetchWithAuth(`/resumes/${id}`);
  },

  async createResume(resume: { title: string; content: string }): Promise<Resume> {
    return fetchWithAuth('/resumes', {
      method: 'POST',
      body: JSON.stringify(resume),
    });
  },

  async updateResume(
    id: string,
    updates: { title?: string; content?: string }
  ): Promise<Resume> {
    return fetchWithAuth(`/resumes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  },

  async deleteResume(id: string): Promise<void> {
    return fetchWithAuth(`/resumes/${id}`, {
      method: 'DELETE',
    });
  },

  async getResumeVersions(resumeId: string): Promise<ResumeVersion[]> {
    return fetchWithAuth(`/resumes/${resumeId}/versions`);
  },

  async createResumeVersion(
    resumeId: string,
    version: {
      content: string;
      is_customized: boolean;
      job_description_id?: string;
    }
  ): Promise<ResumeVersion> {
    return fetchWithAuth(`/resumes/${resumeId}/versions`, {
      method: 'POST',
      body: JSON.stringify(version),
    });
  },

  async getResumeDiff(
    resumeId: string,
    versionId: string,
    originalVersionId?: string
  ): Promise<ResumeDiff> {
    const endpoint = originalVersionId
      ? `/resumes/${resumeId}/versions/${versionId}/diff?original_version_id=${originalVersionId}`
      : `/resumes/${resumeId}/versions/${versionId}/diff`;
    
    return fetchWithAuth(endpoint);
  },
};

// Job Descriptions
export const JobService = {
  async getJobs(): Promise<JobDescription[]> {
    return fetchWithAuth('/jobs');
  },

  async getJob(id: string): Promise<JobDescription> {
    return fetchWithAuth(`/jobs/${id}`);
  },

  async createJob(job: {
    title: string;
    company?: string;
    description: string;
  }): Promise<JobDescription> {
    return fetchWithAuth('/jobs', {
      method: 'POST',
      body: JSON.stringify(job),
    });
  },

  async updateJob(
    id: string,
    updates: { title?: string; company?: string; description?: string }
  ): Promise<JobDescription> {
    return fetchWithAuth(`/jobs/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  },

  async deleteJob(id: string): Promise<void> {
    return fetchWithAuth(`/jobs/${id}`, {
      method: 'DELETE',
    });
  },

  async importFromUrl(url: string): Promise<{ title: string; company?: string; description: string }> {
    // Use JINA API to extract job description
    console.log(`Extracting job description from URL: ${url}`);
    
    try {
      console.log(`Sending job URL extraction request for: ${url}`);
      // Try to use the JINA API via our Next.js proxy
      const response = await fetch(`/api/extract-job?url=${encodeURIComponent(url)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(typeof window !== 'undefined' && localStorage.getItem('auth_token') 
            ? { Authorization: `Bearer ${localStorage.getItem('auth_token')}` } 
            : {}),
        },
      });
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Failed to extract job description (HTTP ${response.status})`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error using JINA API:', error);
      
      // No fallback in production mode
      
      throw error;
    }
  },
};

// ATS Analysis
export const ATSService = {
  async analyzeResume(
    resumeId: string,
    jobDescriptionId: string,
    options?: { headers?: Record<string, string> }
  ): Promise<ATSAnalysisResult> {
    try {
      console.log('ATSService.analyzeResume - input params:', { resumeId, jobDescriptionId });
      // Fix: Create an ATSAnalysisRequest object exactly matching the expected backend schema
      const requestBody = JSON.stringify({
        resume_id: resumeId,
        job_description_id: jobDescriptionId
      });
      console.log('ATSService.analyzeResume - request body:', requestBody);
      
      // Bypass NextJS API routes and go directly to the backend
      // to avoid path prefixing issues
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
      const headers = {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...(options?.headers || {})
      };
      
      console.log(`Sending request to: ${BACKEND_API_URL}/api/v1/ats/analyze`);
      const response = await fetch(`${BACKEND_API_URL}/api/v1/ats/analyze`, {
        method: 'POST',
        headers,
        body: requestBody,
      });
      
      console.log(`Response status: ${response.status} ${response.statusText}`);
      
      // Important: Check if response is present before trying to parse JSON
      if (!response) {
        throw new ApiError(0, 'Network request failed: No response received', null);
      }
      
      const data = await response.json().catch((err) => {
        console.error(`Error parsing JSON: ${err.message}`);
        throw new ApiError(response.status, `Failed to parse response: ${err.message}`, err);
      });
      
      if (!response.ok) {
        // Improved error handling
        let errorMessage = 'An error occurred';
        
        // Try to extract a human-readable error message
        if (data) {
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (data.detail && typeof data.detail === 'object') {
            // For validation errors which might be nested
            errorMessage = JSON.stringify(data.detail);
          }
        }
        
        throw new ApiError(
          response.status,
          errorMessage,
          data
        );
      }
      
      // Verify we have valid data
      if (!data) {
        throw new ApiError(response.status, 'Response contained no data', null);
      }
      
      return data;
    } catch (error) {
      console.error('Error in analyzeResume:', error);
      
      // If it's already an ApiError, just rethrow it
      if (error instanceof ApiError) {
        throw error;
      }
      
      // Convert any other errors to ApiError with a more helpful message
      if (error instanceof Error) {
        throw new ApiError(0, `Network or connection error: ${error.message}`, error);
      }
      
      // Fallback for unknown errors
      throw new ApiError(0, 'Unknown error during analysis request', error);
    }
  },

  // Direct content analysis (without saving)
  async analyzeContent(
    resumeContent: string,
    jobDescriptionContent: string
  ): Promise<ATSAnalysisResult> {
    return fetchWithAuth('/ats/analyze-content', {
      method: 'POST',
      body: JSON.stringify({
        resume_content: resumeContent,
        job_description_content: jobDescriptionContent,
      }),
    });
  },
  
  // Advanced AI-driven analysis for creating better customization plans
  async analyzeAndPlan(
    resumeId: string,
    jobDescriptionId: string,
    customizationLevel: 'conservative' | 'balanced' | 'extensive' = 'balanced'
  ): Promise<any> {
    return fetchWithAuth('/ats/analyze-and-plan', {
      method: 'POST',
      body: JSON.stringify({
        resume_id: resumeId,
        job_description_id: jobDescriptionId,
        customization_level: customizationLevel === 'conservative' ? 1 : 
                            customizationLevel === 'balanced' ? 2 : 3,
      }),
    });
  },
  
  // Direct content advanced analysis (without saving)
  async analyzeContentAndPlan(
    resumeContent: string,
    jobDescriptionContent: string,
    customizationLevel: 'conservative' | 'balanced' | 'extensive' = 'balanced'
  ): Promise<any> {
    return fetchWithAuth('/ats/analyze-content-and-plan', {
      method: 'POST',
      body: JSON.stringify({
        resume_content: resumeContent,
        job_description_content: jobDescriptionContent,
        customization_level: customizationLevel === 'conservative' ? 1 : 
                            customizationLevel === 'balanced' ? 2 : 3,
      }),
    });
  },
};

// Customization
export const CustomizationService = {
  async customizeResume(
    resumeId: string,
    jobDescriptionId: string,
    customizationLevel: 'conservative' | 'balanced' | 'extensive' = 'balanced',
    customizationPlan?: any,
    options?: { headers?: Record<string, string> }
  ): Promise<ResumeVersion> {
    console.log('customizeResume - input params:', { 
      resumeId, 
      jobDescriptionId, 
      customizationLevel,
      hasPlan: !!customizationPlan
    });
    
    const requestBody = JSON.stringify({
      resume_id: resumeId,
      job_description_id: jobDescriptionId,
      customization_strength: customizationLevel === 'conservative' ? 1 : customizationLevel === 'balanced' ? 2 : 3,
      focus_areas: '',
      customization_plan: customizationPlan || undefined,
    });
    
    // Bypass NextJS API routes and go directly to the backend
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...(options?.headers || {})
    };
    
    const response = await fetch(`${BACKEND_API_URL}/api/v1/customize/`, {
      method: 'POST',
      headers,
      body: requestBody,
    });
    
    console.log(`Customize response status: ${response.status} ${response.statusText}`);
    
    const data = await response.json().catch((err) => {
      console.error(`Error parsing customize response JSON: ${err.message}`);
      return {};
    });
    
    if (!response.ok) {
      throw new ApiError(
        response.status,
        data.detail || 'Failed to customize resume',
        data
      );
    }
    
    return data;
  },

  // Direct content customization (without saving)
  async customizeContent(
    resumeContent: string,
    jobDescriptionContent: string,
    customizationLevel: 'conservative' | 'balanced' | 'extensive' = 'balanced',
    customizationPlan?: any
  ): Promise<{ customized_content: string }> {
    return fetchWithAuth('/customize/content', {
      method: 'POST',
      body: JSON.stringify({
        resume_content: resumeContent,
        job_description_content: jobDescriptionContent,
        customization_strength: customizationLevel === 'conservative' ? 1 : customizationLevel === 'balanced' ? 2 : 3,
        customization_plan: customizationPlan || undefined,
      }),
    });
  },
  
  // Generate an advanced customization plan only (without implementing)
  async generateCustomizationPlan(
    resumeId: string,
    jobDescriptionId: string,
    customizationLevel: 'conservative' | 'balanced' | 'extensive' = 'balanced',
    atsAnalysis?: any,
    options?: { headers?: Record<string, string> }
  ): Promise<any> {
    console.log('generateCustomizationPlan - input params:', { 
      resumeId, 
      jobDescriptionId, 
      customizationLevel,
      hasAnalysis: !!atsAnalysis
    });
    
    const requestBody = JSON.stringify({
      resume_id: resumeId,
      job_description_id: jobDescriptionId,
      customization_strength: customizationLevel === 'conservative' ? 1 : customizationLevel === 'balanced' ? 2 : 3,
      ats_analysis: atsAnalysis || undefined,
    });
    
    // Use NextJS API routes to handle the request instead of direct backend call
    // This ensures proper error handling and authentication forwarding
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...(options?.headers || {})
    };
    
    const response = await fetch('/api/customize/plan', {
      method: 'POST',
      headers,
      body: requestBody,
    });
    
    console.log(`Plan response status: ${response.status} ${response.statusText}`);
    
    const data = await response.json().catch((err) => {
      console.error(`Error parsing plan JSON: ${err.message}`);
      return {};
    });
    
    if (!response.ok) {
      throw new ApiError(
        response.status,
        data.detail || 'Failed to generate customization plan',
        data
      );
    }
    
    return data;
  },
};

// Cover Letter
export const CoverLetterService = {
  async generateCoverLetter(
    resumeId: string,
    jobDescriptionId: string,
    tone: 'professional' | 'conversational' | 'enthusiastic' = 'professional'
  ): Promise<{ content: string }> {
    return fetchWithAuth('/cover-letter/generate', {
      method: 'POST',
      body: JSON.stringify({
        resume_id: resumeId,
        job_description_id: jobDescriptionId,
        tone,
      }),
    });
  },

  // Direct content generation (without saving)
  async generateFromContent(
    resumeContent: string,
    jobDescriptionContent: string,
    tone: 'professional' | 'conversational' | 'enthusiastic' = 'professional'
  ): Promise<{ content: string }> {
    return fetchWithAuth('/cover-letter/generate-from-content', {
      method: 'POST',
      body: JSON.stringify({
        resume_content: resumeContent,
        job_description_content: jobDescriptionContent,
        tone,
      }),
    });
  },
};

// Export
export const ExportService = {
  async exportResumeToPdf(resumeId: string, versionId?: string): Promise<Blob> {
    const endpoint = versionId
      ? `/export/resume/${resumeId}/pdf?version_id=${versionId}`
      : `/export/resume/${resumeId}/pdf`;
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null}`,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        error.detail || 'Export failed',
        error
      );
    }

    return response.blob();
  },

  async exportResumeToDocx(resumeId: string, versionId?: string): Promise<Blob> {
    const endpoint = versionId
      ? `/export/resume/${resumeId}/docx?version_id=${versionId}`
      : `/export/resume/${resumeId}/docx`;
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null}`,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        error.detail || 'Export failed',
        error
      );
    }

    return response.blob();
  },

  async exportCoverLetterToPdf(
    coverLetterContent: string,
    fileName: string = 'cover-letter'
  ): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/export/cover-letter/pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null}`,
      },
      body: JSON.stringify({
        content: coverLetterContent,
        file_name: fileName,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        error.detail || 'Export failed',
        error
      );
    }

    return response.blob();
  },

  async exportCoverLetterToDocx(
    coverLetterContent: string,
    fileName: string = 'cover-letter'
  ): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/export/cover-letter/docx`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null}`,
      },
      body: JSON.stringify({
        content: coverLetterContent,
        file_name: fileName,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        error.detail || 'Export failed',
        error
      );
    }

    return response.blob();
  },
};