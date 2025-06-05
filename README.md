# Marketing Scraper Streamlit App

This Streamlit application scrapes websites from a provided CSV file, extracts content, and uses the OpenAI GPT API to answer predefined questions based on the scraped content.

## Features

- Reads company and website data from a CSV file.
- Scrapes website content.
- Processes scraped content using OpenAI's GPT model to answer specific questions.
- Displays results in a user-friendly Streamlit interface.

## Setup

1.  Clone the repository.
2.  Create a virtual environment:
    `python -m venv venv`
    `source venv/bin/activate` (on macOS/Linux) or `venv\Scripts\activate` (on Windows)
3.  Install dependencies:
    `pip install -r requirements.txt`
4.  Set up your OpenAI API key as an environment variable:
    `export OPENAI_API_KEY='your_api_key_here'`
5.  Place your CSV file (e.g., `apollo-contacts-export-batch1-5.csv`) in the project root.
6.  Run the Streamlit app:
    `streamlit run app.py`
