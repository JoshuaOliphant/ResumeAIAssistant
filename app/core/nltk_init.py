"""
Initialize NLTK data for the application.
This script should be imported at application startup to ensure all necessary NLTK data is available.
"""
import os
import nltk

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
    
    for package in packages:
        try:
            nltk.download(package, download_dir=nltk_data_dir, quiet=False)
        except Exception as e:
            print(f"Error downloading NLTK package {package}: {e}")