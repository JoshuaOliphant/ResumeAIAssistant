import { NextRequest, NextResponse } from 'next/server';

/**
 * API route to generate an AI-enhanced customization plan using Claude
 * 
 * NOTE: This route is deprecated. It was part of the old architecture and is no longer 
 * in use. The new architecture uses the WebSocket-based four-stage workflow
 * implemented in the PydanticAI integration.
 * 
 * This file is kept for reference but returns a deprecation notice.
 * 
 * TODO: Remove this deprecated API route entirely in the next major version
 */
export async function POST(request: NextRequest) {
  return NextResponse.json(
    { 
      detail: 'This endpoint is deprecated. The application now uses the WebSocket-based four-stage workflow for resume customization.' 
    },
    { status: 410 } // 410 Gone
  );
}
