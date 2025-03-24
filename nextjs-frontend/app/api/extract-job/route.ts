import { NextRequest, NextResponse } from 'next/server';

/**
 * API route to extract job description from a URL using Jina API
 */
export async function GET(request: NextRequest) {
  // Get URL from query params
  const searchParams = request.nextUrl.searchParams;
  const url = searchParams.get('url');

  if (!url) {
    return NextResponse.json(
      { detail: 'URL is required' },
      { status: 400 }
    );
  }

  // Validate URL format
  try {
    new URL(url);
  } catch (error) {
    return NextResponse.json(
      { detail: 'Invalid URL format' },
      { status: 400 }
    );
  }

  // Get Jina API key from environment variables
  const jinaApiKey = process.env.JINA_API_KEY;
  
  // Check if we have a key
  if (!jinaApiKey) {
    console.error('JINA_API_KEY is not set in environment variables');
    return NextResponse.json(
      { detail: 'Server configuration error - API key missing' },
      { status: 500 }
    );
  }
  
  // Log that we have an API key (length only, for security)
  console.log(`JINA API Key is available (length: ${jinaApiKey.length})`)
  // Load all environment variables for debugging
  console.log('Environment variables loaded:', Object.keys(process.env).filter(key => !key.includes('KEY')).join(', '))

  try {
    // Call Jina API
    console.log(`Using Jina API to extract content from: ${url}`);
    // According to Jina API documentation, the URL format should be:
    // https://r.jina.ai/URL_TO_EXTRACT
    const jinaUrl = `https://r.jina.ai/${url}`;
    
    console.log(`Making request to: ${jinaUrl}`);
    const response = await fetch(jinaUrl, {
      headers: {
        'Authorization': `Bearer ${jinaApiKey}`
      },
      next: {
        revalidate: 3600 // Cache for 1 hour
      }
    });

    // Log the full response status for debugging
    console.log(`Jina API response status: ${response.status} ${response.statusText}`);
    
    if (response.status === 401 || response.status === 403) {
      console.error(`Jina API authentication error: ${response.status} ${response.statusText}`);
      // For auth errors, we want to return a 500 error since it's a server configuration issue
      return NextResponse.json(
        { detail: 'Server configuration error with the job extraction service. Please contact support.' },
        { status: 500 }
      );
    } else if (response.status === 404) {
      return NextResponse.json(
        { detail: 'The job posting URL could not be found. Please verify the URL is correct and accessible.' },
        { status: 404 }
      );
    } else if (!response.ok) {
      console.error(`Jina API error: ${response.status} ${response.statusText}`);
      return NextResponse.json(
        { detail: `Failed to access job posting URL (HTTP ${response.status})` },
        { status: 500 } // Always return 500 for server errors to avoid confusing the client
      );
    }
    
    // Log the response headers for debugging
    console.log('Jina API response headers:');
    response.headers.forEach((value, key) => {
      console.log(`${key}: ${value}`);
    });

    // Parse the response
    const content = await response.text();
    console.log(`Response content (first 200 chars): ${content.substring(0, 200)}`);
    
    // Try to parse as JSON first (the API might return JSON directly)
    let jsonData;
    try {
      jsonData = JSON.parse(content);
      console.log('Successfully parsed response as JSON');
      
      // If we have JSON data with markdown content, return it
      if (jsonData.markdown_content) {
        return NextResponse.json({
          title: jsonData.title || "Job Posting",
          company: jsonData.company_name || undefined,
          description: jsonData.markdown_content,
          url
        });
      }
      
      // If we have JSON but no markdown content, try to use text_content
      if (jsonData.text_content) {
        return NextResponse.json({
          title: jsonData.title || "Job Posting",
          company: jsonData.company_name || undefined,
          description: jsonData.text_content,
          url
        });
      }
      
      // If we have JSON but don't recognize the format, fall back to text processing
      console.log('JSON response doesn\'t have expected fields, falling back to text processing');
    } catch (error) {
      console.log('Response is not JSON, processing as text');
    }
    
    // Extract title and content using regex
    const titleMatch = content.match(/Title:\s*(.+?)(?:\n|$)/);
    const title = titleMatch ? titleMatch[1] : "Job Posting";

    // Split content into lines
    const contentLines = content.split('\n');

    // Get content after "Markdown Content:" marker
    let markdownLines;
    try {
      const markdownStart = contentLines.indexOf('Markdown Content:');
      if (markdownStart !== -1) {
        console.log('Found "Markdown Content:" marker at line', markdownStart);
        markdownLines = contentLines.slice(markdownStart + 1);
      } else {
        console.log('No "Markdown Content:" marker found');
        // Remove header lines if marker not found
        markdownLines = contentLines.filter(
          line => !line.startsWith('Title:') && !line.startsWith('URL Source:')
        );
      }
    } catch (error) {
      console.error('Error processing content lines:', error);
      // Remove header lines if marker not found
      markdownLines = contentLines.filter(
        line => !line.startsWith('Title:') && !line.startsWith('URL Source:')
      );
    }

    // Clean up the content
    const cleanedLines = markdownLines
      .filter(line => !line.startsWith('![') && !line.startsWith('[![')) // Skip image lines
      .map(line => {
        // Remove markdown links but keep the text
        let cleaned = line.replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1');
        // Remove multiple spaces and newlines
        cleaned = cleaned.replace(/\s+/g, ' ').trim();
        return cleaned;
      })
      .filter(Boolean); // Remove empty lines

    const cleanedContent = cleanedLines.join('\n').trim();

    if (!cleanedContent) {
      return NextResponse.json(
        { detail: 'No content could be extracted from the job posting URL. Please verify the URL points to a valid job posting.' },
        { status: 400 }
      );
    }

    // Try to extract company name
    const companyMatch = title.match(/at\s+([^|]+)/) || title.match(/([^|]+)(?:\s+is\s+hiring|\s+job)/i);
    const company = companyMatch ? companyMatch[1].trim() : undefined;

    // Return the extracted job description
    return NextResponse.json({
      title,
      company,
      description: cleanedContent,
      url
    });
  } catch (error) {
    console.error('Error extracting job description:', error);
    return NextResponse.json(
      { detail: `Failed to extract job description: ${(error as Error).message}` },
      { status: 500 }
    );
  }
}