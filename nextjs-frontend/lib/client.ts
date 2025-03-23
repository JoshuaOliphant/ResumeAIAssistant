/**
 * API client for interacting with the Resume AI Assistant backend
 */

const API_BASE_URL = '/api/v1';

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
    super(message);
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
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    // Read the response body
    const data = await response.json().catch(() => ({}));

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

      const response = await fetch(`${API_BASE_URL}/auth/login`, {
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
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
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
    return fetchWithAuth('/jobs/import-from-url', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  },
};

// ATS Analysis
export const ATSService = {
  async analyzeResume(
    resumeId: string,
    jobDescriptionId: string
  ): Promise<ATSAnalysisResult> {
    return fetchWithAuth('/ats/analyze', {
      method: 'POST',
      body: JSON.stringify({
        resume_id: resumeId,
        job_description_id: jobDescriptionId,
      }),
    });
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
};

// Customization
export const CustomizationService = {
  async customizeResume(
    resumeId: string,
    jobDescriptionId: string
  ): Promise<ResumeVersion> {
    return fetchWithAuth('/customize/resume', {
      method: 'POST',
      body: JSON.stringify({
        resume_id: resumeId,
        job_description_id: jobDescriptionId,
      }),
    });
  },

  // Direct content customization (without saving)
  async customizeContent(
    resumeContent: string,
    jobDescriptionContent: string
  ): Promise<{ customized_content: string }> {
    return fetchWithAuth('/customize/content', {
      method: 'POST',
      body: JSON.stringify({
        resume_content: resumeContent,
        job_description_content: jobDescriptionContent,
      }),
    });
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