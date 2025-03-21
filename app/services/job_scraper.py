import re
import httpx
import trafilatura
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup


async def scrape_job_description(url: str) -> Dict[str, Any]:
    """
    Scrape job description from a URL.
    
    Args:
        url: URL to scrape
    
    Returns:
        Dictionary containing job title, company, and description
    """
    try:
        # Try with Trafilatura first - it handles networking and many edge cases
        downloaded = trafilatura.fetch_url(url)
        
        if downloaded:
            # Try to extract main content with Trafilatura
            main_content = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            
            # Parse with BeautifulSoup for structured data extraction
            soup = BeautifulSoup(downloaded, 'html.parser')
            
            # Extract job title and company
            job_title = extract_job_title(soup, url)
            company_name = extract_company_name(soup, url)
            
            # Decide on the best description text
            if main_content and len(main_content) > 100:
                # Use Trafilatura's extracted text if it looks good
                description = main_content
            else:
                # Fall back to BeautifulSoup-based extraction
                description = extract_job_description(soup, url)
            
            # Return the job data
            return {
                "title": job_title,
                "company": company_name,
                "description": description
            }
        
        # Fall back to httpx if trafilatura's fetch_url fails
        async with httpx.AsyncClient() as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=10)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data
            job_data = {
                "title": extract_job_title(soup, url),
                "company": extract_company_name(soup, url),
                "description": extract_job_description(soup, url)
            }
            
            return job_data
            
    except Exception as e:
        raise Exception(f"Failed to scrape job description: {str(e)}")


def extract_job_title(soup: BeautifulSoup, url: str) -> Optional[str]:
    """
    Extract job title from the HTML.
    """
    # Try common title patterns
    title = None
    
    # Try h1 elements first
    h1_tags = soup.find_all('h1')
    for h1 in h1_tags:
        text = h1.get_text().strip()
        if text and 5 < len(text) < 100:  # Reasonable length for a job title
            title = text
            break
    
    # Try common job title selectors if h1 failed
    if not title:
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
                        break
            except Exception:
                continue
    
    # Extract from title element if nothing else worked
    if not title:
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text().strip()
            # Try to extract job title from page title
            job_title_pattern = r'(.*?)\s*(\||\-|at|@)\s*(.*)'
            match = re.search(job_title_pattern, title_text)
            if match:
                title = match.group(1).strip()
    
    return title or "Untitled Job"


def extract_company_name(soup: BeautifulSoup, url: str) -> Optional[str]:
    """
    Extract company name from the HTML.
    """
    company = None
    
    # Try common company name selectors
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
                    break
        except Exception:
            continue
    
    # Try to extract from URL if no company name found
    if not company:
        # Extract domain from URL
        domain_match = re.search(r'https?://(?:www\.)?(.*?)\.', url)
        if domain_match:
            domain = domain_match.group(1)
            if domain not in ['google', 'indeed', 'linkedin', 'glassdoor', 'monster', 'careers']:
                company = domain.capitalize()
    
    return company


def extract_job_description(soup: BeautifulSoup, url: str) -> str:
    """
    Extract job description from the HTML.
    First try Trafilatura for high-quality content extraction,
    then fall back to BeautifulSoup selectors if needed.
    """
    # First try with Trafilatura - it's specialized for content extraction
    try:
        # Get the raw HTML
        html_content = str(soup)
        
        # Use Trafilatura to extract the main content
        extracted_text = trafilatura.extract(html_content, include_comments=False, include_tables=True)
        
        if extracted_text and len(extracted_text) > 100:
            # Clean up the text
            extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
            return extracted_text
    except Exception:
        # If Trafilatura fails, continue with BeautifulSoup approach
        pass
    
    # Fall back to BeautifulSoup selectors
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
                        break
                if description_text:
                    break
        except Exception:
            continue
    
    # If we still don't have a description, try to get all text from the page 
    # and extract the largest paragraph block
    if not description_text:
        paragraphs = soup.find_all('p')
        if paragraphs:
            max_length = 0
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > max_length:
                    max_length = len(text)
                    description_text = text
    
    # If still no description, get the main content area based on heuristics
    if not description_text or len(description_text) < 100:
        # Find the main content area - often this has the most text
        main_tags = soup.find_all(['main', 'article', 'section', 'div'], class_=lambda c: c and any(x in str(c).lower() for x in ['main', 'content', 'job', 'description']))
        
        max_length = 0
        for tag in main_tags:
            text = tag.get_text().strip()
            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text)
            if len(text) > max_length:
                max_length = len(text)
                description_text = text
    
    # Clean up the text
    if description_text:
        # Remove excessive whitespace
        description_text = re.sub(r'\s+', ' ', description_text)
        # Remove very common headers that might be part of the scraped text
        description_text = re.sub(r'Job Description|About the Role|About the Company|Requirements|Qualifications|Responsibilities|About Us', '', description_text)
        
    return description_text.strip() or "No job description found."
