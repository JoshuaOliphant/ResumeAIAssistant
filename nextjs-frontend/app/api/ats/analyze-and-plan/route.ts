import { NextRequest, NextResponse } from 'next/server';
import { API_BASE_URL } from '@/lib/api-config';

/**
 * API route to perform ATS analysis and generate a customization plan in one step
 * This implements the evaluator-optimizer pattern described in the Anthropic blog
 */
export async function POST(request: NextRequest) {
  try {
    // Parse request body
    const body = await request.json();
    const { resume_id, job_description_id, customization_level } = body;
    
    // Get auth token from request headers
    const authHeader = request.headers.get('authorization');
    
    if (!resume_id || !job_description_id) {
      return NextResponse.json(
        { detail: 'Resume ID and Job Description ID are required' },
        { status: 400 }
      );
    }
    
    // Forward the request to the backend (proxy pattern)
    // Use API_BASE_URL without appending API_VERSION to avoid double prefix
    const apiResponse = await fetch(`${API_BASE_URL}/ats/analyze-and-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader && { 'Authorization': authHeader }),
      },
      body: JSON.stringify({
        resume_id,
        job_description_id,
        customization_level,
      }),
    });
    
    if (!apiResponse.ok) {
      const errorData = await apiResponse.json().catch(() => ({}));
      return NextResponse.json(
        { detail: errorData.detail || `Failed to perform analysis and planning (${apiResponse.status})` },
        { status: apiResponse.status }
      );
    }
    
    // Return the analysis and plan
    const data = await apiResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error during analysis and planning:', error);
    return NextResponse.json(
      { detail: `Failed to perform analysis and planning: ${(error as Error).message}` },
      { status: 500 }
    );
  }
}