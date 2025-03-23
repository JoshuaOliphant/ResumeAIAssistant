/**
 * API client for interacting with the Resume AI Assistant backend
 */

// API base URL - adjust this based on your environment
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api/v1';

// Types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
}

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface Resume {
  id: string;
  title: string;
  user_id: string | null;
  created_at: string;
  updated_at: string;
  current_version?: ResumeVersion;
}

export interface ResumeVersion {
  id: string;
  resume_id: string;
  content: string;
  version_number: number;
  is_customized: number;
  job_description_id?: string;
  created_at: string;
}

export interface ResumeDetail extends Resume {
  versions: ResumeVersion[];
}

export interface JobDescription {
  id: string;
  title: string;
  description: string;
  company: string;
  user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ATSAnalysisRequest {
  resume_id: string;
  job_description_id: string;
}

export interface ATSAnalysisResponse {
  resume_id: string;
  job_description_id: string;
  match_score: number;
  matching_keywords: string[];
  missing_keywords: string[];
  improvements: string[];
}

/**
 * Generic fetch wrapper with error handling and authentication
 */
async function fetchWithErrorHandling<T>(
  url: string, 
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    // Add auth headers if available
    const headers = {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(options?.headers || {})
    };

    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers
    });
    
    // Handle non-2xx responses
    if (!response.ok) {
      if (response.status === 401) {
        // Handle authentication errors
        // Clear token if it's invalid
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
        }
        return { error: 'Authentication required. Please log in.' };
      }
      
      // Try to parse error message from response
      try {
        const errorData = await response.json();
        return { error: errorData.detail || `Error: ${response.status} ${response.statusText}` };
      } catch {
        return { error: `Error: ${response.status} ${response.statusText}` };
      }
    }

    // For 204 No Content responses
    if (response.status === 204) {
      return { data: {} as T };
    }

    // Parse successful response
    const data = await response.json();
    return { data };
  } catch (error) {
    console.error('API request failed:', error);
    return { error: 'Failed to connect to the server. Please check your connection.' };
  }
}

// Authentication Functions

/**
 * Login user and get access token
 */
export async function login(username: string, password: string): Promise<ApiResponse<Token>> {
  // Use URLSearchParams for form data as required by OAuth2 password flow
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const response = await fetchWithErrorHandling<Token>('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  });

  // Store token if login successful
  if (response.data && typeof window !== 'undefined') {
    localStorage.setItem('auth_token', response.data.access_token);
  }

  return response;
}

/**
 * Register a new user
 */
export async function register(
  email: string, 
  username: string, 
  password: string, 
  full_name: string
): Promise<ApiResponse<User>> {
  return fetchWithErrorHandling<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, username, password, full_name }),
  });
}

/**
 * Get current user profile
 */
export async function getCurrentUser(): Promise<ApiResponse<User>> {
  return fetchWithErrorHandling<User>('/auth/me');
}

/**
 * Logout user (client-side only)
 */
export function logout(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('auth_token');
  }
}

// Resume Functions

/**
 * Get all resumes
 */
export async function getResumes(): Promise<ApiResponse<Resume[]>> {
  return fetchWithErrorHandling<Resume[]>('/resumes');
}

/**
 * Get a specific resume with all versions
 */
export async function getResume(resumeId: string): Promise<ApiResponse<ResumeDetail>> {
  return fetchWithErrorHandling<ResumeDetail>(`/resumes/${resumeId}`);
}

/**
 * Create a new resume
 */
export async function createResume(title: string, content: string): Promise<ApiResponse<Resume>> {
  return fetchWithErrorHandling<Resume>('/resumes', {
    method: 'POST',
    body: JSON.stringify({ title, content }),
  });
}

/**
 * Update a resume
 */
export async function updateResume(
  resumeId: string, 
  data: { title?: string; content?: string }
): Promise<ApiResponse<Resume>> {
  return fetchWithErrorHandling<Resume>(`/resumes/${resumeId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a resume
 */
export async function deleteResume(resumeId: string): Promise<ApiResponse<void>> {
  return fetchWithErrorHandling<void>(`/resumes/${resumeId}`, {
    method: 'DELETE',
  });
}

/**
 * Get all versions of a resume
 */
export async function getResumeVersions(resumeId: string): Promise<ApiResponse<ResumeVersion[]>> {
  return fetchWithErrorHandling<ResumeVersion[]>(`/resumes/${resumeId}/versions`);
}

/**
 * Create a new version of a resume
 */
export async function createResumeVersion(
  resumeId: string,
  content: string,
  isCustomized: boolean = false,
  jobDescriptionId?: string
): Promise<ApiResponse<ResumeVersion>> {
  return fetchWithErrorHandling<ResumeVersion>(`/resumes/${resumeId}/versions`, {
    method: 'POST',
    body: JSON.stringify({
      content,
      is_customized: isCustomized ? 1 : 0,
      job_description_id: jobDescriptionId
    }),
  });
}

// Job Description Functions

/**
 * Get all job descriptions
 */
export async function getJobDescriptions(): Promise<ApiResponse<JobDescription[]>> {
  return fetchWithErrorHandling<JobDescription[]>('/jobs');
}

/**
 * Get a specific job description
 */
export async function getJobDescription(jobId: string): Promise<ApiResponse<JobDescription>> {
  return fetchWithErrorHandling<JobDescription>(`/jobs/${jobId}`);
}

/**
 * Create a new job description
 */
export async function createJobDescription(
  title: string,
  company: string,
  description: string
): Promise<ApiResponse<JobDescription>> {
  return fetchWithErrorHandling<JobDescription>('/jobs', {
    method: 'POST',
    body: JSON.stringify({ title, company, description }),
  });
}

/**
 * Update a job description
 */
export async function updateJobDescription(
  jobId: string,
  data: { title?: string; company?: string; description?: string }
): Promise<ApiResponse<JobDescription>> {
  return fetchWithErrorHandling<JobDescription>(`/jobs/${jobId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a job description
 */
export async function deleteJobDescription(jobId: string): Promise<ApiResponse<void>> {
  return fetchWithErrorHandling<void>(`/jobs/${jobId}`, {
    method: 'DELETE',
  });
}

// ATS Analysis Functions

/**
 * Analyze a resume against a job description
 */
export async function analyzeResume(
  resumeId: string,
  jobDescriptionId: string
): Promise<ApiResponse<ATSAnalysisResponse>> {
  return fetchWithErrorHandling<ATSAnalysisResponse>('/ats/analyze', {
    method: 'POST',
    body: JSON.stringify({ resume_id: resumeId, job_description_id: jobDescriptionId }),
  });
}

// Cover Letter Functions

/**
 * Generate a cover letter
 */
export async function generateCoverLetter(
  resumeId: string,
  jobDescriptionId: string,
  customInstructions?: string
): Promise<ApiResponse<{ cover_letter: string }>> {
  return fetchWithErrorHandling<{ cover_letter: string }>('/cover-letter/generate', {
    method: 'POST',
    body: JSON.stringify({
      resume_id: resumeId,
      job_description_id: jobDescriptionId,
      custom_instructions: customInstructions
    }),
  });
}

// Utility Functions

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return typeof window !== 'undefined' && Boolean(localStorage.getItem('auth_token'));
}

/**
 * Get authentication headers for requests
 */
export function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}
