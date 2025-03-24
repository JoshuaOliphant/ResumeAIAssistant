// Development mode auth configuration
// This file provides a mock authentication mechanism for development only

// Set to true to enable development mode authentication (bypasses backend auth)
// Set to false to use the real backend API
export const AUTH_DEV_MODE = false;

// Mock user data for development
export const MOCK_USER = {
  id: "dev-user-123",
  email: "user@example.com",
  username: "devuser",
  full_name: "Development User",
};

// Mock token for development
export const MOCK_TOKEN = "dev-token-xyz";