import streamlit as st
import pandas as pd
import os # Added for OPENAI_API_KEY retrieval
from utils import load_data, get_website_list
from scraper import scrape_page_data, crawl_website
from llm_processor import get_structured_responses, FIXED_QUESTIONS

# --- App Configuration ---
st.set_page_config(layout="wide", page_title="Website Analyzer AI")

# --- Global Variables ---
# CSV_FILE_PATH = "apollo-contacts-export-batch1-5.csv" # Removed

# Helper function to convert results to CSV for download
@st.cache_data # Cache the conversion
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- Main App ---
def main():
    st.title("🤖 Website Content Analyzer AI")
    st.markdown("Upload a CSV file with website URLs. The app will scrape them, extract content, and use AI to answer predefined questions. Caching is used for web scraping and AI calls to speed up repeated analyses.")

    # --- Sidebar ---
    st.sidebar.header("Configuration")
    
    uploaded_file = st.sidebar.file_uploader("Upload your CSV file", type=["csv"], help="CSV should contain a 'Website' column with URLs.")
    
    # Crawl Parameters
    st.sidebar.subheader("Crawling Options")
    max_depth = st.sidebar.number_input("Max Crawl Depth", min_value=0, max_value=5, value=1, help="How many link levels to follow from the start page. 0 means only the start page, 1 means start page + its direct links, etc.")
    max_pages = st.sidebar.number_input("Max Pages per Site", min_value=1, max_value=50, value=5, help="Maximum number of pages to scrape for each website during crawling.")
    
    openai_api_key_env = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key_env:
        st.sidebar.error("OPENAI_API_KEY environment variable not set!")
        st.warning("Please set your OPENAI_API_KEY environment variable to use the AI features.")
    else:
        st.sidebar.success("OPENAI_API_KEY found in environment.")

    st.sidebar.info("Clear cache if you modify underlying data or scraping/LLM logic significantly (see `caching.py`).")
    if st.sidebar.button("Clear Cache (Scraping & LLM)"):
        from caching import scrape_memory, llm_memory
        scrape_memory.clear()
        llm_memory.clear()
        st.sidebar.success("Scraping and LLM caches cleared!")

    # --- Load Data ---
    data_df = None
    if uploaded_file is not None:
        data_df = load_data(uploaded_file)
    else:
        st.info("Please upload a CSV file using the sidebar to start analysis.")
        return # Exit early if no file is uploaded

    if data_df is None:
        # load_data in utils.py already shows an error, st.info("Could not load data from the uploaded CSV.") is redundant
        return # Exit if data loading failed

    websites = get_website_list(data_df)
    if not websites:
        st.warning("No valid websites (starting with http:// or https://) found in the 'Website' column of the uploaded CSV, or the column is missing/empty.")
        return

    # Extract question texts for display and column headers
    question_texts = [q_conf["text"] for q_conf in FIXED_QUESTIONS]

    # --- Single Website Analysis ---
    st.header("Single Website Analysis")
    selected_website = st.selectbox("Select a website to analyze:", ["-"] + websites, key="single_website_select")

    if selected_website != "-":
        st.subheader(f"Analyzing: {selected_website}")
        if not openai_api_key_env:
            st.error("OpenAI API Key is required for analysis. Please set it.")
        else:
            # Use crawl_website instead of scrape_page_data
            with st.spinner(f"Crawling {selected_website} (depth: {max_depth}, max pages: {max_pages})..."):
                # max_depth and max_pages are now available from the sidebar
                crawled_pages_data = crawl_website(selected_website, max_depth, max_pages)
            
            aggregated_text = ""
            main_page_content_display = "No content retrieved from the main page."
            successfully_crawled_pages = 0
            errors_encountered = []

            if crawled_pages_data:
                for page_data in crawled_pages_data:
                    if page_data.get('text') and not page_data.get('error'):
                        successfully_crawled_pages += 1
                        # Add a separator for clarity if multiple pages are aggregated
                        aggregated_text += page_data['text'] + "\n\n--- Page Separator ---\n\n"
                        # Try to get content from the originally selected URL for display
                        if page_data['url'] == selected_website: # Check against the input selected_website
                           main_page_content_display = page_data['text']
                    elif page_data.get('error'):
                        errors_encountered.append(f"Error on {page_data.get('url', 'unknown URL')}: {page_data.get('error')}")
                
                # If main_page_content_display is still the default and we have some aggregated_text, use that for display
                if main_page_content_display == "No content retrieved from the main page." and aggregated_text:
                    main_page_content_display = aggregated_text.split("\n\n--- Page Separator ---\n\n")[0]

                st.success(f"Crawling complete! {successfully_crawled_pages} page(s) scraped successfully. Total content length: {len(aggregated_text)} chars.")
                if errors_encountered:
                    with st.expander("View Crawling Errors", expanded=False):
                        for err in errors_encountered:
                            st.warning(err)

                with st.expander("View Content from Main Page (first 2000 characters)", expanded=False):
                    st.text_area("Main Page Scraped Text", main_page_content_display[:2000], height=300, disabled=True, key=f"text_{selected_website}_main")
                
                if st.button("Analyze Content with AI", key=f"analyze_{selected_website}"):
                    if not aggregated_text:
                        st.warning("No text content was successfully scraped from the website. Cannot analyze.")
                    else:
                        client_config = {"api_key": openai_api_key_env}
                        with st.spinner("AI is thinking... This might take a moment."):
                            responses = get_structured_responses(aggregated_text, FIXED_QUESTIONS, client_config)
                        
                        st.subheader("AI Analysis Results:")
                        if responses:
                            for q_text in question_texts: 
                                answer = responses.get(q_text, "Not answered")
                                st.markdown(f"**❓ {q_text}**")
                                st.info(f"{answer if answer else 'No answer generated.'}")
                        else:
                            st.error("Could not retrieve AI responses.")
            else:
                st.error(f"Failed to crawl or retrieve any data from {selected_website}.")
    
    # --- Batch Analysis & Download ---
    st.header("Batch Analysis of All Websites")
    st.markdown("Process all valid websites from the uploaded CSV and download the results as a CSV file.")

    if not openai_api_key_env:
        st.warning("OpenAI API Key is required for batch analysis. Please set it in your environment variables.")
    
    if st.button("Analyze All Websites & Prepare Results", disabled=(not openai_api_key_env or data_df is None)):
        if not openai_api_key_env:
            st.error("Cannot perform batch analysis without OpenAI API Key.")
            return
        if data_df is None: # Should be caught by the button's disabled state, but good check
            st.error("Cannot perform batch analysis without uploaded CSV data.")
            return

        all_results = []
        total_websites = len(websites)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, website_url in enumerate(websites):
            status_text.text(f"Processing ({i+1}/{total_websites}): {website_url} (Depth: {max_depth}, Pages: {max_pages})")
            try:
                # Use crawl_website for batch processing
                crawled_pages_data = crawl_website(website_url, max_depth, max_pages)
                
                aggregated_site_text = ""
                successfully_crawled_pages_count = 0
                site_errors = []

                if crawled_pages_data:
                    for page_data in crawled_pages_data:
                        if page_data.get('text') and not page_data.get('error'):
                            successfully_crawled_pages_count += 1
                            aggregated_site_text += page_data['text'] + "\n\n--- Page Separator ---\n\n"
                        elif page_data.get('error'):
                            site_errors.append(f"Error on {page_data.get('url', 'sub-page')}: {page_data.get('error')}")
                
                current_result = {"Website URL": website_url}
                # Initialize with default message
                for q_text in question_texts: 
                    current_result[q_text] = "Error: Crawling failed, no content, or AI analysis issue"

                if aggregated_site_text:
                    st.write(f"Crawled {successfully_crawled_pages_count} pages for {website_url}. Total content: {len(aggregated_site_text)} chars.")
                    if site_errors:
                        st.write(f"Errors encountered during crawl for {website_url}: {', '.join(site_errors[:2])}...") # Show a few errors
                    
                    client_config = {"api_key": openai_api_key_env}
                    ai_responses = get_structured_responses(aggregated_site_text, FIXED_QUESTIONS, client_config)
                    current_result.update(ai_responses) # Update with actual answers
                elif crawled_pages_data: # Crawl happened but no text yielded, or only errors
                    warning_msg = f"Crawling for {website_url} yielded no text content."
                    if site_errors:
                        warning_msg += f" Errors: {', '.join(site_errors[:2])}..."
                    st.warning(warning_msg)
                    for q_text in question_texts: 
                        current_result[q_text] = "No text content from crawl"
                else: # crawl_website returned empty list or None
                    st.warning(f"Skipping AI analysis for {website_url} due to crawling issues (no data returned from crawl_website).")
                    for q_text in question_texts: 
                        current_result[q_text] = "Crawling returned no data"
                
                all_results.append(current_result)

            except Exception as e:
                st.error(f"Error processing {website_url}: {e}")
                error_result = {"Website URL": website_url}
                for q_text in question_texts:
                    error_result[q_text] = f"Error: {e}"
                all_results.append(error_result)
            
            progress_bar.progress((i + 1) / total_websites)
        
        status_text.success(f"Batch processing complete for {len(all_results)} websites!")

        if all_results:
            results_df = pd.DataFrame(all_results)
            
            # Reorder columns to have Website URL first, then the fixed questions in order
            column_order = ["Website URL"] + question_texts # Use extracted question_texts
            # Ensure all columns exist, fill missing with empty string or error msg if necessary
            for col in column_order:
                if col not in results_df.columns:
                    results_df[col] = "Not processed/Missing" # Should not happen if initialized properly
            results_df = results_df[column_order]
            
            st.subheader("Batch Analysis Results Summary")
            st.dataframe(results_df)
            
            csv_data = convert_df_to_csv(results_df) 
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv_data,
                file_name="website_analysis_results.csv",
                mime="text/csv",
            )
        else:
            st.info("No results to display or download.")

if __name__ == "__main__":
    main() 