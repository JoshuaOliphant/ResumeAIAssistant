"""
Initialize NLTK data for the application.
This script should be imported at application startup to ensure all necessary NLTK data is available.
"""
import os
import nltk
import sys

def initialize_nltk():
    """
    Download all necessary NLTK data packages required by the application.
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
    except Exception as e:
        print(f"Failed to initialize stopwords: {e}", file=sys.stderr)