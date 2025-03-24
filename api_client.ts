/**
 * API client for interacting with the Resume AI Assistant backend
 */

const API_BASE_URL = 'http://localhost:5001';

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchWithErrorHandling<T>(
  url: string, 
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${url}`, options);
    
    // Handle non-2xx responses
    if (!response.ok) {
      if (response.status === 401) {
        // Handle authentication errors
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

    // Parse successful response
    const data = await response.json();
    return { data };
  } catch (error) {
    console.error('API request failed:', error);
    return { error: 'Failed to connect to the server. Please check your connection.' };
  }
}

/**
 * Analyze a resume against a job description
 */
export async function analyzeResume(resumeText: string, jobDescription: string) {
  return fetchWithErrorHandling('/api/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ resume: resumeText, job_description: jobDescription }),
  });
}

/**
 * Get analysis history for the current user
 */
export async function getAnalysisHistory() {
  return fetchWithErrorHandling('/api/history');
}

/**
 * Get detailed analysis for a specific analysis ID
 */
export async function getAnalysisDetails(analysisId: string) {
  return fetchWithErrorHandling(`/api/analysis/${analysisId}`);
}

/**
 * User authentication functions
 */
export async function login(email: string, password: string) {
  return fetchWithErrorHandling('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });
}

export async function register(email: string, password: string, name: string) {
  return fetchWithErrorHandling('/api/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password, name }),
  });
}

export async function logout() {
  return fetchWithErrorHandling('/api/auth/logout', {
    method: 'POST',
  });
}

/**
 * Get the current user profile
 */
export async function getUserProfile() {
  return fetchWithErrorHandling('/api/user/profile');
}

// Helper to check if user is authenticated
export function isAuthenticated() {
  // This would typically check for a token in localStorage or cookies
  return typeof window !== 'undefined' && Boolean(localStorage.getItem('auth_token'));
}

// Add auth token to requests
export function getAuthHeaders() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
