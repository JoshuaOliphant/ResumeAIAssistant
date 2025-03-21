import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from typing import List, Dict, Any

# Download necessary NLTK resources
nltk.download('punkt')
nltk.download('stopwords')

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
    
    Args:
        text: The text to extract keywords from
    
    Returns:
        Dictionary mapping keywords to their frequency
    """
    # Convert to lowercase and tokenize
    tokens = word_tokenize(text.lower())
    
    # Remove stopwords, punctuation, and short words
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
    technical_pattern = r'(python|java|javascript|react|node|sql|aws|azure|docker|kubernetes|machine learning|data science|artificial intelligence|blockchain|devops|agile|scrum|html|css|api|nosql|mongodb|express|vue|angular|swift|kotlin|c\+\+|ruby|php|golang|rust|scala|hadoop|spark|tensorflow|pytorch|nlp|ci\/cd|git|github|gitlab|bitbucket|jira|confluence|jenkins|terraform|ansible|chef|puppet)'
    
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
