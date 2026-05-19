import sys
import os

# Add the project directory to sys.path so we can import web_search
# Dynamically compute project directory based on this script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = script_dir
sys.path.insert(0, project_dir)

from web_search import WebSearch

def test_search():
    try:
        ws = WebSearch()
        print("WebSearch initialized successfully.")
        
        query = "What is the capital of Italy?"
        print(f"Performing search for: {query}")
        
        result = ws.search(query=query, max_results=1)
        print("\nSearch Result:")
        print(result)
        print("\nTest passed!")
    except Exception as e:
        print(f"\nTest failed with error: {e}")

if __name__ == "__main__":
    test_search()

