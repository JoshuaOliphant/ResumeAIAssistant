"""
Initialize NLP resources for the application.
This script should be imported at application startup to ensure all necessary NLP resources are available.
"""
import os
import nltk
import sys

# Import spaCy initialization
from app.core.spacy_init import initialize_spacy

def initialize_nlp():
    """
    Initialize all NLP resources required by the application.
    This includes both NLTK and spaCy resources.
    
    Returns:
        A tuple containing (nltk_initialized, spacy_model)
    """
    # Initialize NLTK resources
    nltk_initialized = initialize_nltk()
    
    # Initialize spaCy model
    spacy_model = initialize_spacy()
    
    return nltk_initialized, spacy_model

def initialize_nltk():
    """
    Download all necessary NLTK data packages required by the application.
    
    Returns:
        True if all packages were successfully initialized, False otherwise
    """
    # Set NLTK data path to a writable location
    nltk_data_dir = os.path.join(os.getcwd(), 'nltk_data')
    os.makedirs(nltk_data_dir, exist_ok=True)
    nltk.data.path.insert(0, nltk_data_dir)
    
    # Download all required NLTK packages
    packages = [
        'punkt',
        'stopwords',
        'averaged_perceptron_tagger',
        'maxent_ne_chunker',
        'words'
    ]
    
    # Verify if packages are already downloaded
    for package in packages:
        try:
            # Try to find the resource first
            try:
                nltk.data.find(f'{package}')
                print(f"NLTK package '{package}' already available.")
            except LookupError:
                # If not found, download it
                print(f"Downloading NLTK package: {package}")
                nltk.download(package, download_dir=nltk_data_dir, quiet=False)
                print(f"Successfully downloaded {package} to {nltk_data_dir}")
        except Exception as e:
            print(f"Error with NLTK package {package}: {e}", file=sys.stderr)
    
    # Verify that stopwords are accessible
    try:
        stopwords = nltk.corpus.stopwords.words('english')
        print(f"Stopwords initialization successful: {len(stopwords)} words loaded")
        return True
    except Exception as e:
        print(f"Failed to initialize stopwords: {e}", file=sys.stderr)
        return False