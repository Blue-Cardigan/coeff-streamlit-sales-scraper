import pandas as pd
import streamlit as st

def load_data(file_input):
    """Loads data from a CSV file (path or file-like object) and returns a DataFrame."""
    if file_input is None:
        st.info("Please upload a CSV file to begin.")
        return None
    try:
        df = pd.read_csv(file_input, engine='python')
        return df
    except FileNotFoundError: # This error is less likely if using file_uploader, but good for path inputs
        st.error(f"Error: The file was not found.")
        return None
    except pd.errors.EmptyDataError:
        st.error("Error: The uploaded CSV file is empty.")
        return None
    except pd.errors.ParserError as e:
        st.error(f"Error: Could not parse the CSV file. Pandas error: {e}. Please ensure it's a valid CSV.")
        return None
    except Exception as e:
        st.error(f"Error loading or parsing CSV file: {e}")
        return None

def get_website_list(df):
    """Extracts a list of websites from the DataFrame."""
    if df is None or 'Website' not in df.columns:
        st.warning("DataFrame is empty or 'Website' column is missing.")
        return []
    
    # Drop rows where 'Website' is NaN or empty, and ensure it's a string
    websites = df['Website'].dropna().astype(str).unique().tolist()
    valid_websites = [site for site in websites if site.strip() and (site.startswith('http://') or site.startswith('https://'))]
    
    if not valid_websites and websites:
        st.warning("No valid website URLs (starting with http:// or https://) found in the 'Website' column after filtering.")
    elif not websites:
        st.info("No websites found in the 'Website' column.")
        
    return valid_websites 