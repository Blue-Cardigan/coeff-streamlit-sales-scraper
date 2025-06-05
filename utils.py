import pandas as pd
import streamlit as st

def load_data(csv_file_path):
    """Loads data from a CSV file and returns a DataFrame."""
    try:
        df = pd.read_csv(csv_file_path)
        return df
    except FileNotFoundError:
        st.error(f"Error: The file {csv_file_path} was not found.")
        return None
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
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