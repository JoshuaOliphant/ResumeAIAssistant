import re
import nltk
import os
from typing import List, Dict, Any, Optional, Set, Tuple

# Import NLP initialization
from app.core.nltk_init import initialize_nlp

# Initialize NLP resources
nltk_initialized, spacy_model = initialize_nlp()

# Now import NLTK modules after initialization
from nltk.corpus import stopwords

from app.schemas.ats import KeywordMatch, ATSImprovement


async def analyze_resume_for_ats(
    resume_content: str,
    job_description: str
) -> Dict[str, Any]:
    """
    Analyze a resume against a job description for ATS compatibility.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
    
    Returns:
        Dictionary with match score, matching keywords, missing keywords, and improvements
    """
    # Extract keywords from both documents
    resume_keywords = extract_keywords(resume_content)
    job_keywords = extract_keywords(job_description)
    
    # Find matching and missing keywords
    matching = []
    missing = []
    
    for keyword, count in job_keywords.items():
        if keyword in resume_keywords:
            matching.append(KeywordMatch(
                keyword=keyword,
                count_in_resume=resume_keywords[keyword],
                count_in_job=count,
                is_match=True
            ))
        else:
            missing.append(KeywordMatch(
                keyword=keyword,
                count_in_resume=0,
                count_in_job=count,
                is_match=False
            ))
    
    # Sort by count in job description (most important first)
    matching = sorted(matching, key=lambda x: x.count_in_job, reverse=True)
    missing = sorted(missing, key=lambda x: x.count_in_job, reverse=True)
    
    # Calculate match score (0-100)
    total_important_keywords = len([k for k, v in job_keywords.items() if v > 1])
    matched_important_keywords = len([m for m in matching if m.count_in_job > 1])
    
    if total_important_keywords == 0:
        match_score = 50  # Default if no important keywords found
    else:
        match_score = int((matched_important_keywords / total_important_keywords) * 100)
        match_score = min(max(match_score, 0), 100)  # Ensure it's between 0-100
    
    # Generate improvement suggestions
    improvements = generate_improvement_suggestions(resume_content, job_description, matching, missing)
    
    return {
        "match_score": match_score,
        "matching_keywords": matching,
        "missing_keywords": missing,
        "improvements": improvements
    }


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
    phrases = extract_ngrams(text, tokens, 2, 3)
    
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


def extract_ngrams(text: str, tokens: List[str], min_n: int = 2, max_n: int = 3) -> List[str]:
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
