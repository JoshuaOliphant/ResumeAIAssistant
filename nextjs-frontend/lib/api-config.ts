// API Configuration

// The value hardcoded to 5001 since we've confirmed that's what the backend is using
const BACKEND_PORT = 5001;

// Backend API URL - point directly to the FastAPI backend
// Use fixed port value for reliable local development
export const API_BASE_URL = `http://localhost:${BACKEND_PORT}/api/v1`;

// For use within the client.ts file to make sure we don't double-prefix
// Use fixed port value for reliable local development
export const BACKEND_API_URL = `http://localhost:${BACKEND_PORT}`;

// API version prefix used in both client and backend
export const API_VERSION = '/api/v1';

// Log API configuration to debug connection issues
console.info('API Configuration:', {
  API_BASE_URL,
  BACKEND_API_URL,
  API_VERSION,
});