import os
from web_extract import WebExtract

def test_extraction():
    """
    Test the WebExtract class with a sample URL.
    """
    try:
        # Initialize the extract manager (loads keys from apy_keys.env)
        extractor = WebExtract()
        print("WebExtract initialized successfully.")
        
        # Target URL for testing
        test_urls = ["https://www.ansa.it/canale_lifestyle/notizie/societa_diritti/2026/04/14/la-rete-dellodio-online-cosi-diventa-virale_43b2617c-8ba5-4d29-8c48-16d45ce8fc99.html"]
        print(f"Extracting content from: {test_urls}")
        
        # Perform extraction
        # Using default parameters as specified in the notebook
        results = extractor.extract(urls=test_urls)
        
        print("\n--- Extraction Results ---")
        print(results[:500] + "..." if len(results) > 500 else results)
        print("--- End of Results ---\n")
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"An error occurred during extraction test: {e}")

if __name__ == "__main__":
    test_extraction()
