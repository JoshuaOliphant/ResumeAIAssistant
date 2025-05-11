import re
import nltk
import os
import math
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
from nltk.util import ngrams

# Import NLP initialization
from app.core.nltk_init import initialize_nlp

# Initialize NLP resources
nltk_initialized, spacy_model = initialize_nlp()

# Now import NLTK modules after initialization
from nltk.corpus import stopwords

from app.schemas.ats import KeywordMatch, ATSImprovement

# Resume section patterns for detection
RESUME_SECTIONS = {
    "contact_info": [
        "contact information", "personal information", "contact details", "contact", 
        "personal details", "profile", "personal profile", "bio", "about me"
    ],
    "summary": [
        "professional summary", "summary", "executive summary", "career summary", 
        "profile summary", "professional profile", "career objective", "objective",
        "about me", "career profile", "summary of qualifications", "professional overview"
    ],
    "experience": [
        "experience", "work experience", "professional experience", "employment",
        "employment history", "work history", "career history", "job history",
        "professional background", "career accomplishments", "professional activities"
    ],
    "education": [
        "education", "educational background", "academic background", "academic history",
        "qualifications", "academic qualifications", "educational qualifications",
        "training", "academic training", "certifications & education", "degrees"
    ],
    "skills": [
        "skills", "technical skills", "core skills", "key skills", "professional skills",
        "competencies", "core competencies", "skill set", "expertise", "areas of expertise",
        "core capabilities", "professional skills", "strengths", "key strengths",
        "qualifications", "professional competencies", "technical competencies"
    ],
    "projects": [
        "projects", "project experience", "key projects", "professional projects",
        "research projects", "major projects", "notable projects", "project portfolio",
        "case studies", "portfolio", "project highlights", "selected projects"
    ],
    "certifications": [
        "certifications", "professional certifications", "licenses", "licensure",
        "credentials", "accreditations", "professional licenses", "qualifications",
        "certificates", "professional development", "training & certifications"
    ],
    "achievements": [
        "awards", "honors", "achievements", "accomplishments", "recognition",
        "awards & recognition", "honors & awards", "accolades", "distinctions",
        "notable achievements", "professional achievements", "key accomplishments"
    ],
    "languages": [
        "languages", "language skills", "language proficiencies", "foreign languages",
        "linguistic proficiency", "language competencies"
    ]
}

# Section importance weights for different job types
SECTION_WEIGHTS = {
    "default": {
        "summary": 0.7,
        "experience": 1.5,
        "skills": 1.8,
        "education": 0.8,
        "projects": 1.0,
        "certifications": 0.9,
        "achievements": 0.7,
        "languages": 0.5
    },
    "technical": {
        "skills": 2.0,
        "experience": 1.6,
        "projects": 1.5,
        "education": 0.9,
        "certifications": 1.0
    },
    "management": {
        "experience": 2.0,
        "achievements": 1.5,
        "summary": 1.3,
        "skills": 1.2
    },
    "entry_level": {
        "education": 1.8,
        "skills": 1.5,
        "projects": 1.5,
        "experience": 1.0,
    }
}

# Skills taxonomy and hierarchy
SKILLS_TAXONOMY = {
    # Programming Languages family relationships
    "programming": ["python", "java", "javascript", "c++", "c#", "ruby", "php", "typescript", "go", "swift"],
    "python": ["django", "flask", "fastapi", "pyramid", "numpy", "pandas", "scikit-learn", "tensorflow", "pytorch"],
    "java": ["spring", "hibernate", "maven", "junit", "struts", "jsf", "jpa", "jdbc"],
    "javascript": ["node.js", "react", "angular", "vue", "express", "jquery", "typescript", "nextjs", "nuxt"],
    "web_development": ["html", "css", "javascript", "react", "angular", "vue", "django", "flask", "node", "express"],
    
    # Data Science and Analytics
    "data_science": ["machine learning", "deep learning", "statistics", "data mining", "nlp", "computer vision", 
                     "predictive modeling", "python", "r", "tensorflow", "pytorch", "sklearn"],
    "data_analysis": ["sql", "data visualization", "etl", "data cleaning", "excel", "tableau", "power bi", 
                      "python", "r", "pandas", "numpy", "statistical analysis"],
    
    # DevOps and Cloud
    "devops": ["ci/cd", "jenkins", "docker", "kubernetes", "terraform", "ansible", "aws", "azure", "gcp", 
               "monitoring", "git", "github actions", "gitlab ci", "circleci"],
    "cloud": ["aws", "azure", "gcp", "cloud architecture", "serverless", "lambda", "ec2", "s3", "dynamodb", 
              "cloud security", "cloud migration", "docker", "kubernetes"],
    
    # Management and Leadership
    "leadership": ["team management", "strategy", "project management", "people management", "mentoring", 
                   "team building", "cross-functional", "stakeholder management"],
    "project_management": ["agile", "scrum", "kanban", "waterfall", "jira", "project planning", "risk management", 
                           "budgeting", "stakeholder communication"]
}


async def analyze_resume_for_ats(
    resume_content: str,
    job_description: str
) -> Dict[str, Any]:
    """
    Enhanced analysis of a resume against a job description for ATS compatibility.
    
    This implementation uses algorithmic analysis rather than an AI model, so it won't
    depend on the model provider configuration.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
    
    Returns:
        Dictionary with match score, matching keywords, missing keywords, and improvements
    """
    # Start tracking processing time
    start_time = time.time()
    
    # Detect job type based on job description
    job_type = detect_job_type(job_description)
    
    # Identify sections in the resume
    resume_sections = identify_sections(resume_content)
    
    # Process job description to extract key elements
    jd_elements = process_job_description(job_description)
    
    # Extract all keywords from both documents
    resume_keywords = extract_keywords(resume_content)
    job_keywords = extract_keywords(job_description)
    
    # Extract n-grams for more accurate matching
    resume_ngrams = extract_ngrams(resume_content)
    job_ngrams = extract_ngrams(job_description)
    
    # Perform matching with semantic relationship recognition
    match_results = perform_matching(resume_content, resume_sections, resume_ngrams, 
                                    job_description, jd_elements, job_ngrams)
    
    # Calculate section-based scores
    section_scores = calculate_section_scores(resume_sections, jd_elements, job_type)
    
    # Calculate overall score with calibration
    overall_score = calculate_calibrated_score(match_results, section_scores)
    
    # Format matching keywords for the response
    matching = []
    for keyword in match_results['top_matching_keywords']:
        if keyword in resume_keywords:
            matching.append(KeywordMatch(
                keyword=keyword,
                count_in_resume=int(resume_keywords.get(keyword, 1)),
                count_in_job=int(jd_elements['keywords'].get(keyword, 1)),
                is_match=True
            ))
    
    # Format missing keywords for the response
    missing = []
    for keyword in match_results['top_missing_keywords']:
        missing.append(KeywordMatch(
            keyword=keyword,
            count_in_resume=0,
            count_in_job=int(jd_elements['keywords'].get(keyword, 1)),
            is_match=False
        ))
    
    # Generate improved suggestions
    improvements = generate_enhanced_suggestions(
        resume_content, 
        job_description, 
        match_results, 
        section_scores, 
        job_type
    )
    
    # Add section analysis to the response
    section_analysis = []
    for section, score in section_scores.items():
        if section in SECTION_WEIGHTS.get(job_type, SECTION_WEIGHTS['default']):
            section_analysis.append({
                'section': section.capitalize(),
                'score': score,
                'weight': SECTION_WEIGHTS.get(job_type, SECTION_WEIGHTS['default']).get(section, 1.0)
            })
    
    # Calculate processing time
    processing_time = time.time() - start_time
    
    # Log performance metrics
    logfire.info(
        "ATS analysis performance metrics",
        processing_time=round(processing_time, 2),
        resume_size=len(resume_content),
        job_description_size=len(job_description),
        section_count=len(resume_sections),
        match_score=round(overall_score)
    )
    
    return {
        "match_score": round(overall_score),
        "matching_keywords": matching,
        "missing_keywords": missing,
        "improvements": improvements,
        "job_type": job_type,
        "section_scores": section_analysis,
        "confidence": calculate_confidence(match_results),
        "keyword_density": match_results.get('keyword_density', 0),
        "processing_time": processing_time
    }


def detect_job_type(job_description: str) -> str:
    """
    Detect job type based on job description content.
    
    Args:
        job_description: The job description text
        
    Returns:
        Job type (technical, management, entry_level, or default)
    """
    job_lower = job_description.lower()
    
    # Technical role indicators
    tech_keywords = [
        'developer', 'engineer', 'programmer', 'software', 'data scientist', 
        'technical', 'architect', 'devops', 'administrator', 'analyst',
        'python', 'java', 'javascript', 'aws', 'azure', 'cloud', 'fullstack'
    ]
    
    # Management role indicators
    mgmt_keywords = [
        'manager', 'director', 'head of', 'lead', 'chief', 'senior', 
        'executive', 'leadership', 'supervisor', 'principal', 'management'
    ]
    
    # Entry-level indicators
    entry_keywords = [
        'entry', 'junior', 'internship', 'intern', 'trainee', 
        'associate', 'assistant', 'graduate', 'entry level', 'early career'
    ]
    
    # Count occurrences
    tech_count = sum(job_lower.count(kw) for kw in tech_keywords)
    mgmt_count = sum(job_lower.count(kw) for kw in mgmt_keywords)
    entry_count = sum(job_lower.count(kw) for kw in entry_keywords)
    
    # Determine job type based on highest count
    counts = {
        'technical': tech_count,
        'management': mgmt_count,
        'entry_level': entry_count
    }
    
    job_type = max(counts, key=counts.get) if max(counts.values()) > 0 else 'default'
    return job_type


def identify_sections(text: str) -> Dict[str, str]:
    """
    Identify resume sections and their content.
    
    Args:
        text: The resume text
        
    Returns:
        Dictionary mapping section names to content
    """
    sections = {}
    lines = text.split('\n')
    current_section = "unknown"
    section_content = []
    
    # Check for sections based on common headers and patterns
    for line in lines:
        line_lower = line.strip().lower()
        
        # Check if line is a section header
        found_section = False
        for section_name, section_patterns in RESUME_SECTIONS.items():
            # Check exact matches first
            if line_lower in section_patterns:
                # Save previous section
                if section_content:
                    sections[current_section] = '\n'.join(section_content)
                
                # Start new section
                current_section = section_name
                section_content = []
                found_section = True
                break
            
            # Check for header patterns (all caps, followed by colon, etc)
            elif any(pattern in line_lower for pattern in section_patterns):
                # Save previous section
                if section_content:
                    sections[current_section] = '\n'.join(section_content)
                
                # Start new section
                current_section = section_name
                section_content = []
                found_section = True
                break
            
            # Check for markdown-style headers
            elif line_lower.startswith(('#')):
                header_text = re.sub(r'^#+\s*', '', line_lower)
                for section_name, section_patterns in RESUME_SECTIONS.items():
                    if any(pattern in header_text for pattern in section_patterns):
                        # Save previous section
                        if section_content:
                            sections[current_section] = '\n'.join(section_content)
                        
                        # Start new section
                        current_section = section_name
                        section_content = []
                        found_section = True
                        break
        
        # If not a section header, add to current section content
        if not found_section:
            section_content.append(line)
    
    # Add the last section
    if section_content:
        sections[current_section] = '\n'.join(section_content)
    
    return sections


def process_job_description(text: str) -> Dict[str, Any]:
    """
    Process job description to extract key elements like requirements, responsibilities,
    qualifications, title, etc. with their relative importance.
    
    Args:
        text: The job description text
        
    Returns:
        Dictionary with parsed job description elements
    """
    elements = {
        'title': '',
        'requirements': [],
        'responsibilities': [],
        'qualifications': [],
        'keywords': defaultdict(float),  # keyword -> weight mapping
        'sections': {}
    }
    
    # Extract title (usually first line or "Job Title:" or similar)
    lines = text.split('\n')
    for i, line in enumerate(lines[:5]):  # Check first 5 lines
        if re.search(r'job\s+title|position|role', line.lower()):
            title_match = re.search(r'(?:job\s+title|position|role)\s*[:-]\s*(.+)', line, re.IGNORECASE)
            if title_match:
                elements['title'] = title_match.group(1).strip()
                break
        elif i == 0 and len(line.strip()) < 80 and not line.strip().lower().startswith(('job ', 'about ', 'company')):
            # First line, relatively short, not a header
            elements['title'] = line.strip()
    
    # Process sections
    current_section = "general"
    section_content = []
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Check if line is a section header
        if re.match(r'^#+\s+', line) or re.match(r'^\*{2}[^*]+\*{2}$', line):  # Markdown headers or **bold**
            # Save previous section
            if section_content:
                elements['sections'][current_section] = '\n'.join(section_content)
            
            # Determine new section
            clean_header = re.sub(r'^#+\s+|\*+', '', line_lower).strip()
            if any(kw in clean_header for kw in ['requirement', 'qualification', 'what you need']):
                current_section = "requirements"
            elif any(kw in clean_header for kw in ['responsibilit', 'what you will do', 'duties']):
                current_section = "responsibilities"
            elif any(kw in clean_header for kw in ['benefit', 'offer', 'what we offer']):
                current_section = "benefits"
            elif any(kw in clean_header for kw in ['about us', 'company', 'who we are']):
                current_section = "company"
            else:
                current_section = clean_header
            
            section_content = []
        else:
            section_content.append(line)
        
        # Extract requirements & responsibilities from bullets/numbered lists
        if line_lower.strip().startswith(('- ', '* ', '• ')):
            item = re.sub(r'^[-*•]\s+', '', line).strip()
            
            if current_section == "requirements":
                elements['requirements'].append(item)
            elif current_section == "responsibilities":
                elements['responsibilities'].append(item)
        
        # Process each line for weighted keywords
        extract_weighted_keywords(line, elements['keywords'], current_section)
    
    # Save the last section
    if section_content:
        elements['sections'][current_section] = '\n'.join(section_content)
    
    return elements


def extract_weighted_keywords(line: str, keywords_dict: Dict[str, float], section_name: str):
    """
    Extract keywords from a line and assign weights based on position and context.
    
    Args:
        line: The line of text
        keywords_dict: Dictionary to update with keywords and weights
        section_name: Current section name
    """
    # Position weights
    HEADER_WEIGHT = 2.0
    BULLET_WEIGHT = 1.2
    
    line_lower = line.lower()
    weight = 1.0
    
    # Adjust weight based on line formatting and position
    if re.match(r'^#+\s+', line):  # Markdown header
        weight = HEADER_WEIGHT
    elif line.isupper():  # ALL CAPS
        weight = 1.8
    elif re.match(r'^\*{2}[^*]+\*{2}$', line):  # **bold**
        weight = 1.5
    elif line_lower.strip().startswith(('- ', '* ', '• ')):  # Bullet points
        weight = BULLET_WEIGHT
    
    # Boost weight for requirements and qualifications sections
    if section_name in ["requirements", "qualifications"]:
        weight *= 1.5
    
    # Further boost for explicit required skills
    required_match = re.search(r'required|must have|necessary', line_lower)
    if required_match:
        weight *= 1.3
    
    # Process the text with n-grams
    tokens = process_text(line_lower)
    
    # Add single tokens with their weights
    stop_words = get_combined_stopwords()
    for token in tokens:
        if token not in stop_words and len(token) > 2:
            keywords_dict[token] += weight
    
    # Process n-grams
    for n in range(2, 4):  # 2-3 grams
        n_grams = list(ngrams(tokens, n))
        for gram in n_grams:
            if all(token not in stop_words for token in gram):
                gram_text = ' '.join(gram)
                if len(gram_text) > 3:  # Avoid very short n-grams
                    # Assign higher weight to multi-word technical terms
                    if is_technical_term(gram_text):
                        keywords_dict[gram_text] += weight * 1.5
                    else:
                        keywords_dict[gram_text] += weight * 1.2


def is_technical_term(term: str) -> bool:
    """
    Check if a term is a technical term based on the skills taxonomy.
    
    Args:
        term: The term to check
        
    Returns:
        True if term is in the skills taxonomy, False otherwise
    """
    # Flatten the skills taxonomy
    all_skills = set()
    for category, skills in SKILLS_TAXONOMY.items():
        all_skills.add(category)
        all_skills.update(skills)
    
    return term.lower() in all_skills


def process_text(text: str) -> List[str]:
    """
    Process text by tokenizing and removing stop words.
    
    Args:
        text: The text to process
        
    Returns:
        List of processed tokens
    """
    # Remove URLs and HTML-like content
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)
    
    # Replace non-alphanumeric with space
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    
    # Tokenize and lowercase
    tokens = re.findall(r'\b\w+\b', text.lower())
    
    # Keep only meaningful words
    tokens = [
        word for word in tokens 
        if any(c.isalnum() for c in word) 
        and len(word) > 2  # Filter out very short words
    ]
    return tokens


def extract_ngrams(text: str) -> Dict[str, int]:
    """
    Extract n-grams from text with their frequencies.
    
    Args:
        text: The text to extract n-grams from
        
    Returns:
        Dictionary mapping n-grams to frequencies
    """
    result = defaultdict(int)
    
    # Convert to lowercase and tokenize
    tokens = process_text(text.lower())
    stop_words = get_combined_stopwords()
    
    # Extract n-grams of different sizes
    for n in range(1, 4):  # 1-3 grams
        n_grams = list(ngrams(tokens, n))
        for gram in n_grams:
            # Filter out n-grams with stop words
            if n > 1 and any(token in stop_words for token in gram):
                continue
            
            gram_text = ' '.join(gram)
            if len(gram_text) > 3:  # Avoid very short n-grams
                result[gram_text] += 1
    
    return result


def perform_matching(
    resume_text: str, 
    resume_sections: Dict[str, str], 
    resume_ngrams: Dict[str, int], 
    job_description: str, 
    jd_elements: Dict[str, Any], 
    job_ngrams: Dict[str, int]
) -> Dict[str, Any]:
    """
    Perform weighted matching between resume and job description.
    
    Args:
        resume_text: The resume text
        resume_sections: Dictionary of resume sections
        resume_ngrams: Dictionary of resume n-grams
        job_description: The job description text
        jd_elements: Dictionary of job description elements
        job_ngrams: Dictionary of job description n-grams
        
    Returns:
        Dictionary with matching results
    """
    result = {
        'exact_matches': {},
        'semantic_matches': {},
        'total_job_keywords': 0,
        'matched_job_keywords': 0,
        'weighted_match_score': 0,
        'top_matching_keywords': [],
        'top_missing_keywords': [],
        'keyword_density': 0
    }
    
    # Get weighted job keywords
    weighted_job_keywords = jd_elements['keywords']
    result['total_job_keywords'] = len(weighted_job_keywords)
    
    # 1. Exact matching with n-grams
    for job_keyword, job_weight in weighted_job_keywords.items():
        if job_keyword in resume_ngrams:
            match_weight = job_weight
            result['exact_matches'][job_keyword] = {
                'weight': match_weight,
                'frequency': resume_ngrams[job_keyword]
            }
            result['matched_job_keywords'] += 1
            result['weighted_match_score'] += match_weight
    
    # 2. Semantic matching with skill taxonomy
    for job_keyword, job_weight in weighted_job_keywords.items():
        # Skip already exactly matched
        if job_keyword in result['exact_matches']:
            continue
        
        # Check if this is a skill with related skills
        for category, skills in SKILLS_TAXONOMY.items():
            # If job keyword is in a category's skills
            if job_keyword in skills:
                # Check if resume has the category or any of its skills
                if category in resume_ngrams:
                    result['semantic_matches'][job_keyword] = {
                        'matched_with': category,
                        'weight': job_weight * 0.8,  # Reduce weight for category match
                        'confidence': 'medium'
                    }
                    result['weighted_match_score'] += job_weight * 0.8
                    result['matched_job_keywords'] += 0.8  # Partial match
                    break
                
                # Check for sibling skills
                for skill in skills:
                    if skill != job_keyword and skill in resume_ngrams:
                        result['semantic_matches'][job_keyword] = {
                            'matched_with': skill,
                            'weight': job_weight * 0.7,  # Reduce weight for sibling match
                            'confidence': 'medium'
                        }
                        result['weighted_match_score'] += job_weight * 0.7
                        result['matched_job_keywords'] += 0.7  # Partial match
                        break
                        
            # If job keyword is a category
            elif job_keyword == category:
                # Check if resume has any of its skills
                for skill in skills:
                    if skill in resume_ngrams:
                        result['semantic_matches'][job_keyword] = {
                            'matched_with': skill,
                            'weight': job_weight * 0.85,  # Higher match for skill under category
                            'confidence': 'high'
                        }
                        result['weighted_match_score'] += job_weight * 0.85
                        result['matched_job_keywords'] += 0.85  # Strong partial match
                        break
    
    # Calculate keyword density
    total_resume_words = len(process_text(resume_text))
    if total_resume_words > 0:
        matched_keywords_count = sum(data['frequency'] for data in result['exact_matches'].values())
        result['keyword_density'] = (matched_keywords_count / total_resume_words) * 100
    
    # Sort and get top matching and missing keywords
    all_matches = {**result['exact_matches'], **result['semantic_matches']}
    
    # Sort matches by weight and frequency
    sorted_matches = sorted(
        all_matches.items(), 
        key=lambda x: x[1].get('weight', 0) * (x[1].get('frequency', 1) if 'frequency' in x[1] else 1),
        reverse=True
    )
    result['top_matching_keywords'] = [keyword for keyword, _ in sorted_matches[:15]]
    
    # Get missing keywords (those not in exact or semantic matches)
    missing_keywords = {
        kw: weight for kw, weight in weighted_job_keywords.items() 
        if kw not in result['exact_matches'] and kw not in result['semantic_matches']
    }
    sorted_missing = sorted(missing_keywords.items(), key=lambda x: x[1], reverse=True)
    result['top_missing_keywords'] = [keyword for keyword, _ in sorted_missing[:15]]
    
    return result


def calculate_section_scores(
    resume_sections: Dict[str, str], 
    jd_elements: Dict[str, Any], 
    job_type: str
) -> Dict[str, float]:
    """
    Calculate scores for each resume section based on job requirements.
    
    Args:
        resume_sections: Dictionary of resume sections
        jd_elements: Dictionary of job description elements
        job_type: The job type (technical, management, etc.)
        
    Returns:
        Dictionary mapping section names to scores
    """
    section_scores = {}
    section_weights = SECTION_WEIGHTS.get(job_type, SECTION_WEIGHTS['default'])
    
    # Process each resume section
    for section_name, section_content in resume_sections.items():
        if section_name == "unknown":
            continue
            
        # Get the appropriate weight for this section
        section_weight = section_weights.get(section_name, 1.0)
        
        # Skip empty sections
        if not section_content.strip():
            section_scores[section_name] = 0
            continue
        
        # Calculate match score for this section
        section_tokens = process_text(section_content.lower())
        section_text = ' '.join(section_tokens)
        
        matches = 0
        total_keywords = 0
        
        # Check matches against job keywords
        for keyword, weight in jd_elements['keywords'].items():
            total_keywords += 1
            if ' ' in keyword:  # Multi-word keyword
                if keyword in section_text:
                    matches += weight
            else:  # Single word
                if keyword in section_tokens:
                    matches += weight
        
        # Calculate section score
        if total_keywords > 0:
            raw_score = (matches / total_keywords) * 100
            # Apply section weight
            weighted_score = raw_score * section_weight
            section_scores[section_name] = min(round(weighted_score, 2), 100)
        else:
            section_scores[section_name] = 0
    
    return section_scores


def calculate_calibrated_score(
    match_results: Dict[str, Any], 
    section_scores: Dict[str, float]
) -> float:
    """
    Calculate overall ATS score with calibration to match industry benchmarks.
    
    Args:
        match_results: Dictionary with matching results
        section_scores: Dictionary with section scores
        
    Returns:
        Calibrated ATS score
    """
    # Base factors
    exact_match_score = 0
    semantic_match_score = 0
    section_coverage_score = 0
    density_score = 0
    
    # Calculate exact match component - MORE RESPONSIVE SIGMOID CURVE
    if match_results['total_job_keywords'] > 0:
        raw_match_ratio = match_results['weighted_match_score'] / (match_results['total_job_keywords'] * 2)
        # Modified sigmoid with steeper curve for more responsiveness
        exact_match_score = (1 / (1 + math.exp(-12 * (raw_match_ratio - 0.4)))) * 55
    
    # Calculate section coverage component
    important_sections = ['experience', 'skills', 'education', 'summary']
    covered_sections = sum(1 for section in important_sections if section in section_scores and section_scores[section] > 0)
    section_coverage_score = (covered_sections / len(important_sections)) * 12
    
    # Calculate semantic match component
    semantic_matches_count = len(match_results['semantic_matches'])
    semantic_match_score = min(semantic_matches_count * 1.8, 18)
    
    # Calculate keyword density component
    optimal_density = 5.0  # 5% is generally considered optimal
    density = match_results.get('keyword_density', 0)
    if density <= optimal_density:
        density_score = (density / optimal_density) * 10
    else:
        # Less penalization for keyword density over optimal
        density_score = 10 - min(((density - optimal_density) / 7) * 10, 8)
    
    # Calculate bonus for high-value keywords
    high_value_keywords = sum(1 for kw in match_results.get('exact_matches', {}) 
                          if kw in match_results.get('top_matching_keywords', [])[:5])
    high_value_bonus = min(high_value_keywords * 1.5, 5)
    
    # Calculate overall score with industry-calibrated baseline
    base_score_adjustment = 30
    scaling_factor = 0.8
    raw_score = base_score_adjustment + (
        exact_match_score + semantic_match_score + section_coverage_score + 
        density_score + high_value_bonus
    ) * scaling_factor
    
    # Ensure score is within 0-100 range
    final_score = max(0, min(100, raw_score))
    
    return final_score


def calculate_confidence(match_results: Dict[str, Any]) -> str:
    """
    Calculate confidence level of the ATS score.
    
    Args:
        match_results: Dictionary with matching results
        
    Returns:
        Confidence level (low, medium, high)
    """
    # Factors affecting confidence
    total_keywords = match_results['total_job_keywords']
    exact_matches = len(match_results['exact_matches'])
    semantic_matches = len(match_results['semantic_matches'])
    
    # Determine confidence
    if total_keywords < 5:
        return "low"  # Too few keywords to be confident
    elif exact_matches / total_keywords > 0.7:
        return "high"  # High exact match ratio
    elif (exact_matches + semantic_matches) / total_keywords > 0.5:
        return "medium"  # Decent combined match ratio
    else:
        return "low"  # Low match ratio


def generate_enhanced_suggestions(
    resume_content: str, 
    job_description: str, 
    match_results: Dict[str, Any], 
    section_scores: Dict[str, float],
    job_type: str
) -> List[ATSImprovement]:
    """
    Generate detailed improvement suggestions based on analysis.
    
    Args:
        resume_content: The resume content
        job_description: The job description text
        match_results: Dictionary with matching results
        section_scores: Dictionary with section scores
        job_type: The job type
        
    Returns:
        List of improvement suggestions
    """
    improvements = []
    
    # 1. Missing critical keywords
    if match_results['top_missing_keywords']:
        critical_keywords = match_results['top_missing_keywords'][:5]
        improvements.append(ATSImprovement(
            category="Missing Keywords",
            suggestion=f"Add these critical keywords from the job description: {', '.join(critical_keywords)}",
            priority=1
        ))
    
    # 2. Section-specific suggestions
    section_weights = SECTION_WEIGHTS.get(job_type, SECTION_WEIGHTS['default'])
    low_scoring_sections = []
    
    for section, score in section_scores.items():
        if section in section_weights and section_weights[section] >= 1.0 and score < 50:
            low_scoring_sections.append(section)
    
    # Prioritize important sections
    if 'skills' in low_scoring_sections:
        improvements.append(ATSImprovement(
            category="Skills Section",
            suggestion="Your skills section needs improvement. Add more relevant skills and match key terms from the job description.",
            priority=1
        ))
    
    if 'experience' in low_scoring_sections:
        improvements.append(ATSImprovement(
            category="Experience Section",
            suggestion="Enhance your experience section to better match job requirements. Use similar terminology and highlight relevant accomplishments.",
            priority=1
        ))
    
    if 'education' in low_scoring_sections and job_type in ['entry_level', 'academic']:
        improvements.append(ATSImprovement(
            category="Education Section",
            suggestion="Your education section should be more detailed for this job type. Include relevant coursework and achievements.",
            priority=2
        ))
    
    # 3. Keyword density suggestion
    density = match_results.get('keyword_density', 0)
    if density < 3:
        improvements.append(ATSImprovement(
            category="Keyword Density",
            suggestion="Your resume has a low keyword density. Incorporate more relevant terms from the job description naturally throughout your resume.",
            priority=2
        ))
    elif density > 7:
        improvements.append(ATSImprovement(
            category="Keyword Density",
            suggestion="Your resume may have too many keywords which could appear as 'keyword stuffing'. Focus on natural incorporation of key terms.",
            priority=3
        ))
    
    # 4. Job-type specific suggestions
    if job_type == 'technical' and ('skills' not in low_scoring_sections):
        improvements.append(ATSImprovement(
            category="Technical Details",
            suggestion="For technical roles, include more specific technical accomplishments with metrics and outcomes.",
            priority=2
        ))
    elif job_type == 'management' and ('leadership' not in resume_content.lower()):
        improvements.append(ATSImprovement(
            category="Leadership Experience",
            suggestion="For management roles, emphasize your leadership experience, team management, and strategic decision-making skills.",
            priority=1
        ))
    elif job_type == 'entry_level' and not re.search(r'(internship|project|coursework|education)', resume_content, re.IGNORECASE):
        improvements.append(ATSImprovement(
            category="Entry-Level Focus",
            suggestion="For entry-level positions, highlight education, coursework, projects, and internships to compensate for limited professional experience.",
            priority=1
        ))
    
    # 5. Check for quantifiable results
    if not re.search(r'(\d+%|\d+x|increased|decreased|improved|reduced|saved|generated|delivered|achieved|won|awarded)', resume_content, re.IGNORECASE):
        improvements.append(ATSImprovement(
            category="Quantified Results",
            suggestion="Add measurable achievements with percentages, numbers, or specific metrics to strengthen your experience.",
            priority=1
        ))
    
    # 6. Action verbs suggestion
    action_verbs_pattern = r'(managed|developed|created|implemented|led|designed|analyzed|built|launched|achieved|improved|increased|reduced|negotiated|coordinated)'
    action_verbs = re.findall(action_verbs_pattern, resume_content, re.IGNORECASE)
    if len(action_verbs) < 5:
        improvements.append(ATSImprovement(
            category="Action Verbs",
            suggestion="Use more powerful action verbs to strengthen your accomplishments and responsibilities description.",
            priority=2
        ))
    
    # 7. Resume length suggestion
    word_count = len(resume_content.split())
    if word_count < 300:
        improvements.append(ATSImprovement(
            category="Resume Length",
            suggestion="Your resume appears too short. Add more relevant details about your experience and skills.",
            priority=3
        ))
    elif word_count > 800 and job_type != 'management':
        improvements.append(ATSImprovement(
            category="Resume Length",
            suggestion="Your resume may be too long. Focus on the most relevant experience and skills for this position.",
            priority=3
        ))
    
    # Return limited to 5 highest priority suggestions
    return sorted(improvements, key=lambda x: x.priority)[:5]


def extract_keywords(text: str) -> Dict[str, int]:
    """
    Extract important keywords from text, filtering out common words.
    Uses spaCy for enhanced NLP capabilities if available, with fallback to basic NLTK.
    
    Args:
        text: The text to extract keywords from
    
    Returns:
        Dictionary mapping keywords to their frequency
    """
    # Convert to lowercase
    text = text.lower()
    
    # Try to use spaCy for enhanced NLP if available
    if spacy_model is not None:
        return extract_keywords_with_spacy(text)
    else:
        # Fallback to basic NLTK approach
        return extract_keywords_with_nltk(text)


def extract_keywords_with_spacy(text: str) -> Dict[str, int]:
    """
    Extract keywords using spaCy's NLP capabilities.
    
    Args:
        text: The text to extract keywords from
    
    Returns:
        Dictionary mapping keywords to their frequency
    """
    # Process the text with spaCy
    doc = spacy_model(text)
    
    # Get stopwords from both spaCy and NLTK for better filtering
    stop_words = get_combined_stopwords()
    
    # Extract single tokens (filtering stopwords, punctuation, etc.)
    tokens = []
    for token in doc:
        if (
            not token.is_stop 
            and not token.is_punct 
            and not token.is_space 
            and token.text.lower() not in stop_words 
            and len(token.text) > 2
        ):
            tokens.append(token.text.lower())
    
    # Extract named entities (organizations, products, etc.)
    entities = []
    for ent in doc.ents:
        # Only include certain entity types that are relevant for resumes/jobs
        if ent.label_ in ['ORG', 'PRODUCT', 'GPE', 'WORK_OF_ART', 'EVENT', 'LAW', 'LANGUAGE']:
            entities.append(ent.text.lower())
    
    # Extract noun chunks (for technical terms and skills)
    noun_chunks = []
    for chunk in doc.noun_chunks:
        # Filter out chunks that are just stopwords or too short
        chunk_text = chunk.text.lower()
        if not all(token.is_stop for token in chunk) and len(chunk_text) > 3:
            noun_chunks.append(chunk_text)
    
    # Extract phrases using n-grams (2-3 word combinations)
    phrases = extract_ngrams_from_tokens(text, tokens, 2, 3)
    
    # Combine all extracted elements and count frequencies
    all_elements = tokens + entities + noun_chunks + phrases
    keyword_freq = {}
    for element in all_elements:
        if element in keyword_freq:
            keyword_freq[element] += 1
        else:
            keyword_freq[element] = 1
    
    # Filter to keep only keywords appearing more than once or technical terms
    filtered_keywords = filter_technical_terms(keyword_freq)
    
    return filtered_keywords


def extract_keywords_with_nltk(text: str) -> Dict[str, int]:
    """
    Extract keywords using basic NLTK and regex approach (original implementation).
    
    Args:
        text: The text to extract keywords from
    
    Returns:
        Dictionary mapping keywords to their frequency
    """
    # Simple tokenization approach - split by whitespace and punctuation
    tokens = re.findall(r'\b\w+\b', text)
    
    # Remove stopwords and short words
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [
        token for token in tokens 
        if token not in stop_words 
        and token.isalpha() 
        and len(token) > 2
    ]
    
    # Extract phrases (2-3 word combinations) that might be important
    phrases = []
    for i in range(len(tokens) - 1):
        if tokens[i].isalpha() and tokens[i+1].isalpha():
            phrases.append(f"{tokens[i]} {tokens[i+1]}")
    
    for i in range(len(tokens) - 2):
        if tokens[i].isalpha() and tokens[i+1].isalpha() and tokens[i+2].isalpha():
            phrases.append(f"{tokens[i]} {tokens[i+1]} {tokens[i+2]}")
    
    # Count keyword frequencies
    keyword_freq = {}
    for token in filtered_tokens:
        if token in keyword_freq:
            keyword_freq[token] += 1
        else:
            keyword_freq[token] = 1
    
    # Add important phrases
    for phrase in phrases:
        if phrase in text.lower():
            if phrase in keyword_freq:
                keyword_freq[phrase] += 1
            else:
                keyword_freq[phrase] = 1
    
    # Filter to keep only keywords appearing more than once or technical terms
    filtered_keywords = filter_technical_terms(keyword_freq)
    
    return filtered_keywords


def get_combined_stopwords() -> Set[str]:
    """
    Get a combined set of stopwords from NLTK and custom additions.
    
    Returns:
        Set of stopwords
    """
    # Get NLTK stopwords
    stop_words = set(stopwords.words('english'))
    
    # Add custom stopwords relevant to resumes and job descriptions
    custom_stopwords = {
        'resume', 'cv', 'curriculum', 'vitae', 'job', 'description', 'position',
        'responsibilities', 'requirements', 'qualifications', 'apply', 'please',
        'email', 'contact', 'www', 'http', 'https', 'com', 'org', 'net',
        'year', 'years', 'month', 'months', 'day', 'days', 'experience',
        'role', 'roles', 'responsibility', 'team', 'company', 'work', 'working'
    }
    
    return stop_words.union(custom_stopwords)


def extract_ngrams_from_tokens(text: str, tokens: List[str], min_n: int = 2, max_n: int = 3) -> List[str]:
    """
    Extract n-grams (phrases of n words) from text.
    
    Args:
        text: The original text
        tokens: List of already extracted tokens
        min_n: Minimum number of words in a phrase
        max_n: Maximum number of words in a phrase
    
    Returns:
        List of extracted phrases
    """
    # Simple tokenization for phrase extraction
    words = re.findall(r'\b\w+\b', text)
    phrases = []
    
    # Extract phrases of different lengths
    for n in range(min_n, max_n + 1):
        for i in range(len(words) - n + 1):
            if all(words[i+j].isalpha() for j in range(n)):
                phrase = ' '.join(words[i:i+n])
                if phrase in text.lower():
                    phrases.append(phrase)
    
    return phrases


def filter_technical_terms(keyword_freq: Dict[str, int]) -> Dict[str, int]:
    """
    Filter keywords to keep only those appearing more than once or technical terms.
    
    Args:
        keyword_freq: Dictionary mapping keywords to their frequency
    
    Returns:
        Filtered dictionary of keywords
    """
    # Technical terms pattern - expanded to include more technologies and skills
    technical_pattern = r'(python|java|javascript|typescript|react|node|sql|nosql|aws|azure|gcp|docker|kubernetes|machine learning|data science|artificial intelligence|blockchain|devops|agile|scrum|kanban|html|css|api|rest|graphql|mongodb|express|vue|angular|swift|kotlin|c\+\+|ruby|php|golang|rust|scala|hadoop|spark|tensorflow|pytorch|nlp|ci\/cd|git|github|gitlab|bitbucket|jira|confluence|jenkins|terraform|ansible|chef|puppet|linux|unix|windows|macos|ios|android|cloud|saas|paas|iaas|frontend|backend|fullstack|database|security|testing|qa|ux|ui|design|product|project|management|leadership|communication|teamwork|problem solving|critical thinking|creativity|innovation|analytical|detail oriented|results driven|customer focused|strategic thinking|negotiation|presentation|mentoring|coaching|training)'
    
    filtered_keywords = {}
    for keyword, count in keyword_freq.items():
        if count > 1 or re.search(technical_pattern, keyword.lower()):
            filtered_keywords[keyword] = count
    
    return filtered_keywords


def generate_improvement_suggestions(
    resume_content: str, 
    job_description: str, 
    matching: List[KeywordMatch], 
    missing: List[KeywordMatch]
) -> List[ATSImprovement]:
    """
    Generate improvement suggestions based on the resume and job description.
    
    Args:
        resume_content: The content of the resume
        job_description: The job description text
        matching: List of matching keywords
        missing: List of missing keywords
    
    Returns:
        List of improvement suggestions
    """
    improvements = []
    
    # Suggest adding missing important keywords
    important_missing = [k for k in missing if k.count_in_job > 1][:5]  # Top 5 important missing keywords
    if important_missing:
        keywords_str = ", ".join([k.keyword for k in important_missing])
        improvements.append(ATSImprovement(
            category="Missing Keywords",
            suggestion=f"Consider adding these important keywords from the job description: {keywords_str}",
            priority=1
        ))
    
    # Check if resume has quantifiable results
    if not re.search(r'(\d+%|\d+x|increased|decreased|improved|reduced|saved|generated|delivered|achieved|won|awarded)', resume_content, re.IGNORECASE):
        improvements.append(ATSImprovement(
            category="Quantified Results",
            suggestion="Add measurable achievements with percentages, numbers, or specific metrics",
            priority=1
        ))
    
    # Check for education section
    if not re.search(r'(education|university|college|degree|bachelor|master|phd|diploma)', resume_content, re.IGNORECASE):
        improvements.append(ATSImprovement(
            category="Education",
            suggestion="Include an education section with your degrees and academic achievements",
            priority=2
        ))
    
    # Check for skills section
    if not re.search(r'(skills|competencies|expertise|proficient in|proficiency|skilled in)', resume_content, re.IGNORECASE):
        improvements.append(ATSImprovement(
            category="Skills Section",
            suggestion="Add a dedicated skills section listing your technical and soft skills",
            priority=2
        ))
    
    # Check for action verbs
    action_verbs = re.findall(r'(managed|developed|created|implemented|led|designed|analyzed|built|launched|achieved|improved|increased|reduced|negotiated|coordinated)', resume_content, re.IGNORECASE)
    if len(action_verbs) < 5:
        improvements.append(ATSImprovement(
            category="Action Verbs",
            suggestion="Use more powerful action verbs to describe your accomplishments",
            priority=2
        ))
    
    # Check resume length (rough estimate based on word count)
    word_count = len(resume_content.split())
    if word_count < 200:
        improvements.append(ATSImprovement(
            category="Resume Length",
            suggestion="Your resume appears too short. Consider adding more details about your experience",
            priority=3
        ))
    elif word_count > 800:
        improvements.append(ATSImprovement(
            category="Resume Length",
            suggestion="Your resume may be too long. Consider focusing on the most relevant experience",
            priority=3
        ))
    
    return improvements
