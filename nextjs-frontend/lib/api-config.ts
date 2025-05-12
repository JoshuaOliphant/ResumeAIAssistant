// API Configuration

// Backend API URL - point directly to the FastAPI backend
// Use environment variables if available, otherwise fall back to localhost
export const API_BASE_URL = 
  (typeof window !== 'undefined' && window.location.hostname === 'localhost') 
    ? 'http://localhost:5001/api/v1'
    : '/api/v1'; // Use relative URL in production

// For use within the client.ts file to make sure we don't double-prefix
// Use an environment variable for the backend URL, default to the current host
export const BACKEND_API_URL = 
  (typeof window !== 'undefined' && window.location.hostname === 'localhost') 
    ? 'http://localhost:5001'
    : ''; // Empty string means use the current host in production

// API version prefix used in both client and backend
export const API_VERSION = '/api/v1';