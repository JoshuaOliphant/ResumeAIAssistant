import { NextRequest, NextResponse } from 'next/server';
import { API_BASE_URL } from '@/lib/api-config';

/**
 * API route to generate an AI-enhanced customization plan using Claude
 * This is a temporary implementation until the backend endpoint is available
 */
export async function POST(request: NextRequest) {
  try {
    // Parse request body
    const body = await request.json();
    const { resume_id, job_description_id, customization_strength, ats_analysis } = body;
    
    // Get auth token from request headers
    const authHeader = request.headers.get('authorization');
    
    if (!resume_id || !job_description_id) {
      return NextResponse.json(
        { detail: 'Resume ID and Job Description ID are required' },
        { status: 400 }
      );
    }
    
    // Try to forward the request to the backend first
    try {
      const apiResponse = await fetch(`${API_BASE_URL}/customize/plan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authHeader && { 'Authorization': authHeader }),
        },
        body: JSON.stringify({
          resume_id,
          job_description_id,
          customization_strength,
          ats_analysis: ats_analysis || undefined,
        }),
      });
      
      if (apiResponse.ok) {
        // If the backend endpoint works, return its response
        const data = await apiResponse.json();
        return NextResponse.json(data);
      }
      
      // If we get here, the backend endpoint failed, but we'll fall back to local implementation
      console.log(`Backend endpoint failed with status ${apiResponse.status}. Using local implementation.`);
    } catch (backendError) {
      console.log(`Backend request failed: ${(backendError as Error).message}. Using local implementation.`);
    }
    
    // FALLBACK IMPLEMENTATION: Generate a plan using the ATS analysis data
    // This simulates what the backend would return until the backend endpoint is available
    console.log('Using local implementation for customization plan generation');
    
    if (!ats_analysis) {
      return NextResponse.json(
        { detail: 'ATS analysis data is required for local implementation' },
        { status: 400 }
      );
    }
    
    // Extract keywords from analysis
    const matching = Array.isArray(ats_analysis.matching_keywords) ? 
      ats_analysis.matching_keywords.map((k: any) => typeof k === 'object' ? k.keyword : k) : [];
      
    const missing = Array.isArray(ats_analysis.missing_keywords) ? 
      ats_analysis.missing_keywords.map((k: any) => typeof k === 'object' ? k.keyword : k) : [];
    
    // Generate a basic plan using the keyword data
    const plan = {
      summary: `Your resume has a ${ats_analysis.match_score || 0}% match with the job description. This plan will help you optimize your resume for this specific position.`,
      job_analysis: ats_analysis.job_description_summary || 'This job requires skills in ' + missing.join(', '),
      keywords_to_add: missing.slice(0, 10),
      formatting_suggestions: [
        'Use bullet points for achievements',
        'Include metrics and quantifiable results',
        'Keep formatting consistent throughout the document'
      ],
      recommendations: [
        {
          section: 'Professional Summary',
          what: 'Update summary to highlight relevant experience',
          why: 'Tailor your summary to directly address the job requirements',
          before_text: 'Experienced professional with diverse skills and background.',
          after_text: `Experienced professional with skills in ${matching.slice(0, 3).join(', ')}, seeking to leverage expertise in ${missing.slice(0, 3).join(', ')}.`,
          description: 'Make your summary more specific to the job requirements.'
        },
        {
          section: 'Skills',
          what: 'Add missing keywords',
          why: 'Include key skills requested in the job description',
          before_text: 'Skills: ' + matching.slice(0, 5).join(', '),
          after_text: 'Skills: ' + [...matching.slice(0, 5), ...missing.slice(0, 5)].join(', '),
          description: 'Add relevant skills that you genuinely possess.'
        }
      ]
    };
    
    return NextResponse.json(plan);
  } catch (error) {
    console.error('Error generating customization plan:', error);
    return NextResponse.json(
      { detail: `Failed to generate customization plan: ${(error as Error).message}` },
      { status: 500 }
    );
  }
}
