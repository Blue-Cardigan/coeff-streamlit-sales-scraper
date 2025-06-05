import requests
from bs4 import BeautifulSoup
import streamlit as st
from caching import scrape_memory # Import the cache instance
from urllib.parse import urljoin, urlparse # Added for link processing
import collections # Added for future crawling logic

# New helper function to fetch and parse HTML into BeautifulSoup object
def fetch_and_parse(url):
    """Fetches URL content and returns a BeautifulSoup object and the effective URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup, response.url # Return soup and effective URL (after redirects)
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching {url}: {e}")
        return None, url # Return None for soup, original URL on error
    except Exception as e: # Catch other potential errors during request/soup creation
        st.error(f"An unexpected error occurred while fetching/parsing {url}: {e}")
        return None, url

# New helper function to extract text from a BeautifulSoup object
def extract_text_from_soup(soup):
    """Extracts and cleans text content from a BeautifulSoup object."""
    if not soup:
        return ""
        
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
    return text

# New helper function to extract internal links from a BeautifulSoup object
def extract_internal_links(soup, base_url):
    """Extracts unique, absolute internal links from a BeautifulSoup object."""
    if not soup:
        return set()

    internal_links = set()
    base_domain = urlparse(base_url).netloc
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        # Join the base_url with the found href to make it absolute
        absolute_link = urljoin(base_url, href)
        # Parse the absolute link to check its domain
        link_domain = urlparse(absolute_link).netloc
        
        # Check if it's an HTTP/HTTPS link and belongs to the same domain
        if link_domain == base_domain and absolute_link.startswith(('http://', 'https://')):
            internal_links.add(absolute_link)
            
    return internal_links

@scrape_memory.cache # Apply the cache decorator
def scrape_page_data(url):
    """Scrapes a single page for its text content and internal links. This function is cached."""
    soup, effective_url = fetch_and_parse(url)
    
    if not soup:
        # fetch_and_parse already logged an error via st.error
        return {'url': url, 'text': None, 'links': set(), 'error': f"Failed to fetch or parse {url}."}

    text = extract_text_from_soup(soup)
    links = extract_internal_links(soup, effective_url) # Use effective_url as base for links
    
    if not text and not links: # If no text and no links, consider it a partial success with warning
        # Check if an error was already logged by fetch_and_parse for this URL
        # This condition might be tricky if st.error in fetch_and_parse is the only indicator
        # For now, let's assume if soup is present, fetch was okay.
        st.warning(f"No text content or internal links found on {effective_url} after parsing.")
        # We still return the data, as the page might be genuinely empty or non-HTML
        
    return {'url': effective_url, 'text': text, 'links': links, 'error': None}

# Original scrape_website function is now replaced by scrape_page_data
# and its helpers fetch_and_parse, extract_text_from_soup, extract_internal_links.

# Placeholder for the new crawling function to be added next
# def crawl_website(start_url, max_depth=1, max_pages=10):
#     pass

def crawl_website(start_url, max_depth=1, max_pages=10):
    """Crawls a website starting from start_url, up to max_depth and max_pages.
    
    Args:
        start_url (str): The initial URL to start crawling.
        max_depth (int): Maximum depth of links to follow from the start_url.
                         0 means only scrape the start_url.
                         1 means scrape start_url and links found on it.
        max_pages (int): Maximum total number of pages to scrape for this site.
        
    Returns:
        list: A list of dictionaries, where each dictionary is the result
              from scrape_page_data for a successfully scraped page.
    """
    if not start_url.startswith(('http://', 'https://')):
        st.error(f"Invalid start URL: {start_url}. Must be http or https.")
        return []

    queue = collections.deque([(start_url, 0)])
    visited_urls = {start_url}
    all_scraped_data = []

    while queue and len(all_scraped_data) < max_pages:
        current_url, current_depth = queue.popleft()
        
        st.write(f"Scraping: {current_url} (Depth: {current_depth})")

        page_data = scrape_page_data(current_url)

        if page_data and not page_data.get('error'):
            all_scraped_data.append(page_data)
            
            # If current depth is less than max_depth, add new internal links to queue
            if current_depth < max_depth:
                new_links = page_data.get('links', set())
                for link in new_links:
                    if link not in visited_urls and len(visited_urls) < max_pages: # Check visited_urls before adding to queue and also overall pages
                        visited_urls.add(link)
                        queue.append((link, current_depth + 1))
        elif page_data and page_data.get('error'):
            # Error already logged by scrape_page_data or fetch_and_parse via st.error
            st.warning(f"Skipping {current_url} due to error: {page_data.get('error')}")

    if not all_scraped_data:
        st.warning(f"Could not retrieve any data from {start_url} with depth {max_depth} and max pages {max_pages}.")

    return all_scraped_data 