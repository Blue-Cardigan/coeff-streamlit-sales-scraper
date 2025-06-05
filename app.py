import streamlit as st
import pandas as pd
import os # Added for OPENAI_API_KEY retrieval
from utils import load_data, get_website_list
from scraper import scrape_website
from llm_processor import get_openai_client, get_structured_responses, FIXED_QUESTIONS

# --- App Configuration ---
st.set_page_config(layout="wide", page_title="Website Analyzer AI")

# --- Global Variables ---
CSV_FILE_PATH = "apollo-contacts-export-batch1-5.csv"

# Helper function to convert results to CSV for download
@st.cache_data # Cache the conversion
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- Main App ---
def main():
    st.title("🤖 Website Content Analyzer AI")
    st.markdown("This app scrapes websites from a CSV, extracts content, and uses AI to answer predefined questions. Caching is used for web scraping and AI calls to speed up repeated analyses.")

    # --- Sidebar ---
    st.sidebar.header("Configuration")
    openai_api_key_env = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key_env:
        st.sidebar.error("OPENAI_API_KEY environment variable not set!")
        st.warning("Please set your OPENAI_API_KEY environment variable to use the AI features.")
    else:
        st.sidebar.success("OPENAI_API_KEY found in environment.")

    st.sidebar.info(f"Using CSV file: `{CSV_FILE_PATH}`. Clear cache if you modify underlying data or scraping/LLM logic significantly (see `caching.py`).")
    if st.sidebar.button("Clear Cache (Scraping & LLM)"):
        from caching import scrape_memory, llm_memory
        scrape_memory.clear()
        llm_memory.clear()
        st.sidebar.success("Scraping and LLM caches cleared!")

    # --- Load Data ---
    data_df = load_data(CSV_FILE_PATH)

    if data_df is None:
        st.error(f"Could not load data from {CSV_FILE_PATH}. Please ensure the file exists and is correctly formatted.")
        return

    websites = get_website_list(data_df)
    if not websites:
        st.warning("No valid websites found in the CSV to process.")
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
            with st.spinner(f"Scraping {selected_website}..."):
                scraped_content = scrape_website(selected_website) 
            
            if scraped_content:
                st.success(f"Website scraped successfully! (Content length: {len(scraped_content)} chars)")
                with st.expander("View Scraped Content (first 2000 characters)", expanded=False):
                    st.text_area("Scraped Text", scraped_content[:2000], height=300, disabled=True, key=f"text_{selected_website}")
                
                if st.button("Analyze Content with AI", key=f"analyze_{selected_website}"):
                    client_config = {"api_key": openai_api_key_env}
                    with st.spinner("AI is thinking... This might take a moment."):
                        # Pass the full FIXED_QUESTIONS config
                        responses = get_structured_responses(scraped_content, FIXED_QUESTIONS, client_config)
                    
                    st.subheader("AI Analysis Results:")
                    if responses:
                        # responses keys are already question texts, matching question_texts order if LLM returns all
                        for q_text in question_texts: 
                            answer = responses.get(q_text, "Not answered")
                            st.markdown(f"**❓ {q_text}**")
                            st.info(f"{answer if answer else 'No answer generated.'}")
                    else:
                        st.error("Could not retrieve AI responses.")
            else:
                st.error(f"Failed to scrape content from {selected_website}.")
    
    # --- Batch Analysis & Download ---
    st.header("Batch Analysis of All Websites")
    st.markdown("Process all valid websites from the CSV and download the results as a CSV file.")

    if not openai_api_key_env:
        st.warning("OpenAI API Key is required for batch analysis. Please set it in your environment variables.")
    
    if st.button("Analyze All Websites & Prepare Results", disabled=(not openai_api_key_env)):
        if not openai_api_key_env:
            st.error("Cannot perform batch analysis without OpenAI API Key.")
            return

        all_results = []
        total_websites = len(websites)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, website_url in enumerate(websites):
            status_text.text(f"Processing ({i+1}/{total_websites}): {website_url}")
            try:
                scraped_content = scrape_website(website_url) 
                
                current_result = {"Website URL": website_url}
                # Initialize with default error message for all question texts
                for q_text in question_texts: 
                    current_result[q_text] = "Error: Scraping failed or no content"

                if scraped_content:
                    client_config = {"api_key": openai_api_key_env}
                    # Pass the full FIXED_QUESTIONS config
                    ai_responses = get_structured_responses(scraped_content, FIXED_QUESTIONS, client_config)
                    current_result.update(ai_responses) # Update with actual answers
                else:
                    st.warning(f"Skipping AI analysis for {website_url} due to scraping issues.")
                
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
                    results_df[col] = "Not processed/Missing"
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