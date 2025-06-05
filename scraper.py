import requests
from bs4 import BeautifulSoup
import streamlit as st
from caching import scrape_memory # Import the cache instance

@scrape_memory.cache # Apply the cache decorator
def scrape_website(url):
    """Scrapes the website URL and returns its text content. This function is cached."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10) # Added timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if not text:
            st.warning(f"No text content found on {url} after parsing.")
            return None
            
        return text
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while scraping {url}: {e}")
        return None 