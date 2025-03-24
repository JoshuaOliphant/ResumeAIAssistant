import re
import time
import httpx
import trafilatura
import logfire
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from app.core.logging import log_function_call, setup_httpx_instrumentation


@log_function_call
async def scrape_job_description(url: str) -> Dict[str, Any]:
    """
    Scrape job description from a URL.
    
    Args:
        url: URL to scrape
    
    Returns:
        Dictionary containing job title, company, and description
    """
    # Start timer for performance tracking
    start_time = time.time()
    
    # Create a span in OpenTelemetry for tracing
    with logfire.span("scrape_job_description_operation") as span:
        span.set_attribute("url", url)
        
        # Log operation start
        logfire.info("Starting job description scraping", url=url)
        
        try:
            # Try with Trafilatura first - it handles networking and many edge cases
            logfire.info("Attempting to fetch URL with Trafilatura", url=url)
            
            downloaded = trafilatura.fetch_url(url)
            
            if downloaded:
                logfire.info(
                    "Successfully fetched URL with Trafilatura", 
                    url=url, 
                    content_length=len(downloaded)
                )
                
                # Try to extract main content with Trafilatura
                main_content = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
                
                # Parse with BeautifulSoup for structured data extraction
                soup = BeautifulSoup(downloaded, 'html.parser')
                
                # Extract job title and company
                job_title = extract_job_title(soup, url)
                company_name = extract_company_name(soup, url)
                
                # Log extracted metadata
                logfire.info(
                    "Extracted job metadata", 
                    url=url,
                    job_title=job_title,
                    company_name=company_name,
                    has_main_content=main_content is not None,
                    main_content_length=len(main_content) if main_content else 0
                )
                
                # Decide on the best description text
                if main_content and len(main_content) > 100:
                    # Use Trafilatura's extracted text if it looks good
                    description = main_content
                    logfire.info("Using Trafilatura's extracted text for description")
                else:
                    # Fall back to BeautifulSoup-based extraction
                    logfire.info("Falling back to BeautifulSoup for description extraction")
                    description = extract_job_description(soup, url)
                
                # Log success
                elapsed_time = time.time() - start_time
                logfire.info(
                    "Job scraping completed successfully with Trafilatura",
                    url=url,
                    job_title=job_title,
                    company_name=company_name,
                    description_length=len(description),
                    duration_seconds=round(elapsed_time, 2)
                )
                
                # Return the job data
                return {
                    "title": job_title,
                    "company": company_name,
                    "description": description
                }
            
            # Fall back to httpx if trafilatura's fetch_url fails
            logfire.info("Trafilatura fetch failed, falling back to HTTPX", url=url)
            
            # Create HTTPX client with Logfire instrumentation
            async with httpx.AsyncClient() as client:
                # Set up instrumentation for this specific client instance
                setup_httpx_instrumentation(
                    client=client,
                    capture_headers=True,  # Capture non-sensitive headers for debugging
                )
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                
                logfire.info(
                    "Sending HTTPX request", 
                    url=url, 
                    method="GET",
                    headers={k: v for k, v in headers.items()}
                )
                
                # The instrumented client will automatically log the request/response
                response = await client.get(url, headers=headers, follow_redirects=True, timeout=30)
                response.raise_for_status()
                
                logfire.info(
                    "HTTPX request successful",
                    url=url,
                    status_code=response.status_code,
                    content_length=len(response.text)
                )
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract data
                job_title = extract_job_title(soup, url)
                company_name = extract_company_name(soup, url)
                description = extract_job_description(soup, url)
                
                # Log extracted data
                logfire.info(
                    "Extracted job data with HTTPX/BeautifulSoup",
                    url=url,
                    job_title=job_title,
                    company_name=company_name,
                    description_length=len(description)
                )
                
                # Log success
                elapsed_time = time.time() - start_time
                logfire.info(
                    "Job scraping completed successfully with HTTPX",
                    url=url,
                    duration_seconds=round(elapsed_time, 2)
                )
                
                job_data = {
                    "title": job_title,
                    "company": company_name,
                    "description": description
                }
                
                return job_data
                
        except Exception as e:
            # Log error details
            elapsed_time = time.time() - start_time
            logfire.error(
                "Failed to scrape job description",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Re-raise with a clearer message
            raise Exception(f"Failed to scrape job description: {str(e)}")


@log_function_call
def extract_job_title(soup: BeautifulSoup, url: str) -> Optional[str]:
    """
    Extract job title from the HTML.
    """
    # Try common title patterns
    title = None
    
    # Create a span for tracing
    with logfire.span("extract_job_title") as span:
        span.set_attribute("url", url)
        
        # Try h1 elements first
        logfire.info("Trying to extract job title from h1 elements", url=url)
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            text = h1.get_text().strip()
            if text and 5 < len(text) < 100:  # Reasonable length for a job title
                title = text
                logfire.info("Found job title in h1 element", title=title, url=url)
                break
        
        # Try common job title selectors if h1 failed
        if not title:
            logfire.info("No title found in h1, trying CSS selectors", url=url)
            selectors = [
                'title',
                '.job-title',
                '.jobTitle',
                '.job-headline',
                '[data-testid="jobsearch-JobInfoHeader-title"]',  # Indeed
                '.topcard__title',  # LinkedIn
                '.jobs-unified-top-card__job-title',  # LinkedIn
                '.posting-headline h2',  # Greenhouse
                '[data-automation="job-detail-title"]',  # SEEK
                '.js-job-title',  # Workday
            ]
            
            for selector in selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text().strip()
                        if text and 5 < len(text) < 100:
                            title = text
                            logfire.info("Found job title using selector", title=title, selector=selector, url=url)
                            break
                except Exception as e:
                    logfire.warning(
                        "Error when using selector for title extraction",
                        selector=selector,
                        error=str(e),
                        url=url
                    )
                    continue
        
        # Extract from title element if nothing else worked
        if not title:
            logfire.info("No title found in selectors, trying page title", url=url)
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text().strip()
                logfire.info("Found page title", page_title=title_text, url=url)
                # Try to extract job title from page title
                job_title_pattern = r'(.*?)\s*(\||\-|at|@)\s*(.*)'
                match = re.search(job_title_pattern, title_text)
                if match:
                    title = match.group(1).strip()
                    logfire.info("Extracted job title from page title", title=title, url=url)
        
        # Log the final result
        result = title or "Untitled Job"
        logfire.info("Job title extraction completed", title=result, url=url)
        
        return result


@log_function_call
def extract_company_name(soup: BeautifulSoup, url: str) -> Optional[str]:
    """
    Extract company name from the HTML.
    """
    company = None
    
    # Create a span for tracing
    with logfire.span("extract_company_name") as span:
        span.set_attribute("url", url)
        
        # Try common company name selectors
        logfire.info("Trying to extract company name using CSS selectors", url=url)
        selectors = [
            '.company',
            '.company-name',
            '.companyName',
            '.employer-name',
            '[data-testid="jobsearch-JobInfoHeader-companyName"]',  # Indeed
            '.topcard__org-name-link',  # LinkedIn
            '.jobs-unified-top-card__company-name',  # LinkedIn
            '.posting-headline h3',  # Greenhouse
            '[data-automation="advertiser-name"]',  # SEEK
            '.js-company-name',  # Workday
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text().strip()
                    if text and 2 < len(text) < 50:  # Reasonable length for a company name
                        company = text
                        logfire.info("Found company name using selector", company=company, selector=selector, url=url)
                        break
            except Exception as e:
                logfire.warning(
                    "Error when using selector for company extraction",
                    selector=selector,
                    error=str(e),
                    url=url
                )
                continue
        
        # Try to extract from URL if no company name found
        if not company:
            logfire.info("No company name found in selectors, trying URL domain", url=url)
            # Extract domain from URL
            domain_match = re.search(r'https?://(?:www\.)?(.*?)\.', url)
            if domain_match:
                domain = domain_match.group(1)
                if domain not in ['google', 'indeed', 'linkedin', 'glassdoor', 'monster', 'careers']:
                    company = domain.capitalize()
                    logfire.info("Extracted company name from URL domain", company=company, domain=domain, url=url)
        
        # Log the final result
        logfire.info("Company name extraction completed", company=company, url=url)
        
        return company


@log_function_call
def extract_job_description(soup: BeautifulSoup, url: str) -> str:
    """
    Extract job description from the HTML.
    First try Trafilatura for high-quality content extraction,
    then fall back to BeautifulSoup selectors if needed.
    """
    # Create a span for tracing
    with logfire.span("extract_job_description") as span:
        span.set_attribute("url", url)
        
        # First try with Trafilatura - it's specialized for content extraction
        logfire.info("Attempting to extract job description with Trafilatura", url=url)
        try:
            # Get the raw HTML
            html_content = str(soup)
            
            # Use Trafilatura to extract the main content
            extracted_text = trafilatura.extract(html_content, include_comments=False, include_tables=True)
            
            if extracted_text and len(extracted_text) > 100:
                # Clean up the text
                extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
                logfire.info(
                    "Successfully extracted job description with Trafilatura",
                    description_length=len(extracted_text),
                    url=url
                )
                return extracted_text
            else:
                logfire.info(
                    "Trafilatura extraction insufficient",
                    extracted_text_length=len(extracted_text) if extracted_text else 0,
                    url=url
                )
        except Exception as e:
            # Log the error
            logfire.warning(
                "Trafilatura extraction failed",
                error=str(e),
                error_type=type(e).__name__,
                url=url
            )
            # If Trafilatura fails, continue with BeautifulSoup approach
            pass
        
        # Fall back to BeautifulSoup selectors
        logfire.info("Falling back to BeautifulSoup selectors for job description", url=url)
        selectors = [
            '.job-description',
            '.jobsearch-jobDescriptionText',  # Indeed
            '#jobDescriptionText',  # Indeed
            '.description__text',  # LinkedIn
            '.jobs-description',  # LinkedIn
            '.jobs-box__html-content',  # LinkedIn
            '.show-more-less-html__markup',  # LinkedIn
            '.jobs-unified-description',  # LinkedIn newer format
            '.p-main-description',  # Greenhouse
            '[data-automation="jobDescription"]',  # SEEK
            '.job-details',  # Workday
            '#job-description',
            '[itemprop="description"]',
            'article',
            '.job-posting-body',
            '.main-content',
        ]
        
        description_text = ""
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        text = element.get_text().strip()
                        if text and len(text) > 100:  # Reasonable minimum length
                            description_text = text
                            logfire.info(
                                "Found job description using selector",
                                selector=selector,
                                description_length=len(description_text),
                                url=url
                            )
                            break
                    if description_text:
                        break
            except Exception as e:
                logfire.warning(
                    "Error when using selector for description extraction",
                    selector=selector,
                    error=str(e),
                    url=url
                )
                continue
        
        # If we still don't have a description, try to get all text from the page 
        # and extract the largest paragraph block
        if not description_text:
            logfire.info("No description found in selectors, trying paragraphs", url=url)
            paragraphs = soup.find_all('p')
            if paragraphs:
                max_length = 0
                for p in paragraphs:
                    text = p.get_text().strip()
                    if len(text) > max_length:
                        max_length = len(text)
                        description_text = text
                
                if description_text:
                    logfire.info(
                        "Found job description in paragraph",
                        paragraph_count=len(paragraphs),
                        description_length=len(description_text),
                        url=url
                    )
        
        # If still no description, get the main content area based on heuristics
        if not description_text or len(description_text) < 100:
            logfire.info("Description insufficient, trying main content areas", url=url)
            # Find the main content area - often this has the most text
            main_tags = soup.find_all(['main', 'article', 'section', 'div'], class_=lambda c: c and any(x in str(c).lower() for x in ['main', 'content', 'job', 'description']))
            
            if main_tags:
                logfire.info(f"Found {len(main_tags)} potential main content areas", url=url)
                
                max_length = 0
                for tag in main_tags:
                    text = tag.get_text().strip()
                    # Remove excessive whitespace
                    text = re.sub(r'\s+', ' ', text)
                    if len(text) > max_length:
                        max_length = len(text)
                        description_text = text
                
                if description_text:
                    logfire.info(
                        "Found job description in main content area",
                        description_length=len(description_text),
                        url=url
                    )
        
        # Clean up the text
        if description_text:
            # Remove excessive whitespace
            description_text = re.sub(r'\s+', ' ', description_text)
            # Remove very common headers that might be part of the scraped text
            description_text = re.sub(r'Job Description|About the Role|About the Company|Requirements|Qualifications|Responsibilities|About Us', '', description_text)
            
            logfire.info(
                "Cleaned up job description",
                final_description_length=len(description_text),
                url=url
            )
        else:
            logfire.warning("Could not extract job description", url=url)
        
        result = description_text.strip() or "No job description found."
        return result
