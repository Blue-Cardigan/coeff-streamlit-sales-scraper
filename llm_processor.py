import openai
import os
import streamlit as st
from caching import llm_memory # Import the cache instance
import json # Import the json library

FIXED_QUESTIONS = [
    {
        "id": "is_consultancy_agency_outsourcing",
        "text": "Based on the website content, does this company primarily operate as a consultancy, an agency, or an outsourcing firm that provides custom digital, software, or data solutions and services to other businesses/clients, rather than focusing on selling its own distinct product(s)?",
        "type": "json_yes_no",
        "json_key": "is_consultancy_response" # The key LLM should use in its JSON output
    },
    {
        "id": "main_product_service",
        "text": "What is the main product or service offered by this company according to the website content?",
        "type": "text"
    },
    {
        "id": "technologies_industries",
        "text": "Are there any specific technologies or industries mentioned that this company focuses on according to the website?",
        "type": "text"
    }
]

def get_openai_client():
    """Initializes and returns the OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OPENAI_API_KEY environment variable not set. Please set it to use the OpenAI API.")
        return None
    try:
        client = openai.OpenAI(api_key=api_key)
        return client
    except Exception as e:
        st.error(f"Error initializing OpenAI client: {e}")
        return None

@llm_memory.cache
def get_structured_responses(text_content: str, questions_config: list[dict], client_config: dict, model="gpt-3.5-turbo"):
    """
    Uses OpenAI GPT to answer a list of fixed questions based on the provided text content.
    This function is cached.

    Args:
        text_content: The text scraped from the website.
        questions_config: A list of question configuration dictionaries.
        client_config: A dictionary containing API key for client re-hydration.
        model: The default OpenAI model to use for text questions.

    Returns:
        A dictionary with question texts as keys and GPT's answers as values.
    """
    client = openai.OpenAI(api_key=client_config.get('api_key'))
    
    if not client_config.get('api_key'):
        st.error("OpenAI API key not provided for LLM processing.")
        return {q_conf["text"]: "Error: OpenAI API key not configured for this call." for q_conf in questions_config}

    if not text_content:
        return {q_conf["text"]: "Error: No text content provided to analyze." for q_conf in questions_config}

    responses = {}
    max_tokens_per_response = 200
    json_model = "gpt-3.5-turbo-0125" # Model that supports JSON mode

    max_chars_for_content = 40000 
    if len(text_content) > max_chars_for_content:
        text_content_for_llm = text_content[:max_chars_for_content]
        st.warning(f"Website content was too long and has been truncated to {max_chars_for_content} characters for LLM analysis.")
    else:
        text_content_for_llm = text_content

    for q_config in questions_config:
        question_text = q_config["text"]
        question_type = q_config.get("type", "text")
        current_model = model

        try:
            if question_type == "json_yes_no":
                json_key = q_config.get("json_key", "answer")
                prompt_messages = [
                    {"role": "system", "content": f"You are an AI assistant that analyzes website content. For the following question, you must respond in JSON format with a single key '{json_key}' and a value of either 'Yes' or 'No'. Base your answer *only* on the provided text."},
                    {"role": "user", "content": f"Website Content:\n---\n{text_content_for_llm}\n---\n\nQuestion: {question_text}"}
                ]
                current_model = json_model # Override model for JSON mode
                
                completion = client.chat.completions.create(
                    model=current_model,
                    messages=prompt_messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=max_tokens_per_response 
                )
                answer_raw = completion.choices[0].message.content.strip()
                try:
                    json_response = json.loads(answer_raw)
                    answer = json_response.get(json_key, "Error: JSON key not found")
                except json.JSONDecodeError:
                    st.error(f"Failed to decode JSON response for question: {question_text}. Raw: {answer_raw}")
                    answer = "Error: Invalid JSON response"
            else: # Default text-based question
                prompt = f"""Based on the following website content, please answer the question.
Be concise and focus only on information explicitly available in the text.
If the information is not found, state that.

Website Content:
---
{text_content_for_llm}
---

Question: {question_text}
Answer:"""
                completion = client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {"role": "system", "content": "You are an AI assistant that analyzes website content and answers specific questions based *only* on the provided text."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=max_tokens_per_response 
                )
                answer = completion.choices[0].message.content.strip()
            
            responses[question_text] = answer

        except openai.APIError as e:
            st.error(f"OpenAI API error for question \"{question_text}\": {e}")
            responses[question_text] = f"Error: OpenAI API error - {e}"
        except Exception as e:
            st.error(f"An unexpected error occurred while processing question \"{question_text}\": {e}")
            responses[question_text] = f"Error: An unexpected error: {e}"
            
    return responses 