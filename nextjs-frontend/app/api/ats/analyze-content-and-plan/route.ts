import { NextRequest, NextResponse } from 'next/server';
import { API_BASE_URL } from '@/lib/api-config';

/**
 * API route to perform ATS analysis on raw content and generate a customization plan
 * This is similar to analyze-and-plan but works directly with content rather than IDs
 */
export async function POST(request: NextRequest) {
  try {
    // Parse request body
    const body = await request.json();
    const { resume_content, job_description_content, customization_level } = body;
    
    // Get auth token from request headers
    const authHeader = request.headers.get('authorization');
    
    if (!resume_content || !job_description_content) {
      return NextResponse.json(
        { detail: 'Resume content and job description content are required' },
        { status: 400 }
      );
    }
    
    // Forward the request to the backend (proxy pattern)
    // Use API_BASE_URL without appending API_VERSION to avoid double prefix
    const apiResponse = await fetch(`${API_BASE_URL}/ats/analyze-content-and-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader && { 'Authorization': authHeader }),
      },
      body: JSON.stringify({
        resume_content,
        job_description_content,
        customization_level,
      }),
    });
    
    if (!apiResponse.ok) {
      const errorData = await apiResponse.json().catch(() => ({}));
      return NextResponse.json(
        { detail: errorData.detail || `Failed to perform content analysis and planning (${apiResponse.status})` },
        { status: apiResponse.status }
      );
    }
    
    // Return the analysis and plan
    const data = await apiResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error during content analysis and planning:', error);
    return NextResponse.json(
      { detail: `Failed to perform content analysis and planning: ${(error as Error).message}` },
      { status: 500 }
    );
  }
}