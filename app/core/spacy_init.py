"""
Initialize spaCy NLP models for the application.
This script should be imported at application startup to ensure the necessary spaCy models are available.
"""
import os
import sys
import importlib.util

def initialize_spacy():
    """
    Load the spaCy model required by the application.
    Falls back to a warning if the model is not available.
    
    Returns:
        The loaded spaCy model or None if not available
    """
    try:
        # First check if we already have a loaded model
        if hasattr(initialize_spacy, 'nlp') and initialize_spacy.nlp is not None:
            print("spaCy model already loaded")
            return initialize_spacy.nlp
        
        # Try importing spaCy with error handling
        try:
            import spacy
            print("spaCy imported successfully")
        except ImportError:
            print("WARNING: spaCy is not installed. Please install it using:")
            print("pip install spacy")
            print("Falling back to basic NLP functionality.")
            return None
        except Exception as e:
            print(f"Error importing spaCy: {e}")
            print("Falling back to basic NLP functionality.")
            return None
        
        # Try to load the model with comprehensive error handling
        try:
            print("Loading spaCy model: en_core_web_sm")
            nlp = spacy.load("en_core_web_sm")
            print(f"Successfully loaded spaCy model: {nlp.meta['name']}")
            initialize_spacy.nlp = nlp
            return nlp
        except OSError:
            # If the model is not found, try to download it
            print("Model not found. Checking if we can download it...")
            
            # Check if en_core_web_sm is available as a module
            if importlib.util.find_spec("en_core_web_sm") is not None:
                try:
                    print("en_core_web_sm module found, loading...")
                    import en_core_web_sm
                    nlp = en_core_web_sm.load()
                    print(f"Successfully loaded spaCy model: {nlp.meta['name']}")
                    initialize_spacy.nlp = nlp
                    return nlp
                except Exception as e:
                    print(f"Error loading en_core_web_sm: {e}")
                    print("Falling back to basic NLP functionality.")
                    return None
            else:
                print("WARNING: en_core_web_sm module not found. Please install it using:")
                print("python -m spacy download en_core_web_sm")
                print("or pip install en-core-web-sm")
                print("Falling back to basic NLP functionality.")
                return None
    except ImportError:
        print("WARNING: spaCy is not installed. Please install it using:")
        print("pip install spacy")
        print("Falling back to basic NLP functionality.")
        return None
    except Exception as e:
        print(f"Error initializing spaCy: {e}", file=sys.stderr)
        print("Falling back to basic NLP functionality.")
        return None

# Initialize the nlp attribute
initialize_spacy.nlp = None
