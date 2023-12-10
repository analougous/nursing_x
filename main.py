import streamlit as st
import os
from PyPDF2 import PdfReader
import docx
import functions
from functions import improved_parse_document_sections, analyze_and_suggest_improvements
import io
import requests
import json
import openai

# Function to handle query
def handle_query(query, document_text, api_key, model):
    # Add a reference to the nursing knowledge base in the prompt
    prompt = f"Based on the nursing resume knowledge base:\n\n{document_text}\n\nUser: {query}\nAI:"
    response = get_openai_chat_response(api_key, model, prompt, max_tokens=1000)
    return response

# Function to extract text from PDF
def extract_text_from_pdf(file_stream):
    reader = PdfReader(file_stream)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

# Function to extract text from DOCX
def extract_text_from_docx(file_stream):
    doc = docx.Document(file_stream)
    text = [paragraph.text for paragraph in doc.paragraphs]
    return '\n'.join(text)

# Function to get response from OpenAI API
def get_openai_chat_response(api_key, model, prompt, max_tokens):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    data = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens
    }
    response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
    return response.json()

def main():
    # Initialize 'document_text' and 'history' in session state if they do not exist
    if 'document_text' not in st.session_state:
        st.session_state['document_text'] = ""
    if 'history' not in st.session_state:
        st.session_state['history'] = []

    page = st.sidebar.radio("Go to", ["Home", "Nurse Job Listings"], key='main_page_selection')

    if page == "Home":
        display_home_page()
    elif page == "Nurse Job Listings":
        display_job_search_page()

def display_home_page():
    st.title("Nursing Resume Assistant")
    # User input text field
    user_input = st.text_input("Enter your query related to the uploaded document:", key="home_user_input")

    # Process the query
    if st.button("Get AI Response", key="home_query_button"):
        process_user_query(user_input)

    # Modified to handle multiple resume uploads
    uploaded_files = st.file_uploader("Upload your resumes", type=["pdf", "docx"], accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_extension = uploaded_file.name.split('.')[-1]
            if file_extension == 'pdf':
                resume_text = extract_text_from_pdf(uploaded_file)
            elif file_extension == 'docx':
                resume_text = extract_text_from_docx(uploaded_file)
            
            # Parsing and analyzing the resume
            resume_sections = improved_parse_document_sections(resume_text)
            suggestions = analyze_and_suggest_improvements(resume_sections)

            # Displaying suggestions for each resume
            st.subheader(f"Resume Analysis and Suggestions for {uploaded_file.name}")
            for section, suggestion in suggestions.items():
                st.markdown(f"### {section}")
                st.write(suggestion)


def process_user_query(user_input):
    resume_sections = functions.parse_document_sections(st.session_state.get('document_text', ''))
    section_response = functions.find_relevant_section(resume_sections, user_input)

    # Load the OpenAI API key from an environment variable
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    if OPENAI_API_KEY is None:
        st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        return

    # Add user query to history and get AI response
    st.session_state['history'].append(('user', user_input))
    response = handle_query(user_input, st.session_state.get('document_text', ), OPENAI_API_KEY, 'gpt-3.5-turbo')

    # Initialize session state variables
    if 'document_text' not in st.session_state:
        st.session_state.document_text = ""
    
    if section_response != "Sorry, I couldn't find relevant information.":
        st.write(section_response)

    # Display AI response
    if 'choices' in response and response['choices']:
        ai_response = response['choices'][0]['message']['content']
        st.session_state['history'].append(('ai', ai_response))
        display_conversation_history()
    else:
        st.error("No response received from the AI.")

def display_conversation_history():
    # Display the conversation history
    for i, (role, text) in enumerate(st.session_state.get('history', [])):
        if role == 'user':
            st.markdown(f"**User:**\n{text}", unsafe_allow_html=True)
        else:
            st.markdown(f"**AI:**\n{text}", unsafe_allow_html=True)

def process_uploaded_file(uploaded_file):
    # Initialize 'document_text' in session state if it does not exist
    if 'document_text' not in st.session_state:
        st.session_state['document_text'] = ""

    resume_text = st.session_state['document_text']
    resume_sections = functions.parse_document_sections(resume_text)

    # Process the file based on its type
    if uploaded_file.type == "application/pdf":
        st.session_state['document_text'] = extract_text_from_pdf(io.BytesIO(uploaded_file.read()))
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        st.session_state['document_text'] = extract_text_from_docx(io.BytesIO(uploaded_file.read()))
    else:
        st.session_state['document_text'] = uploaded_file.getvalue().decode("utf-8")
        st.write("Extracted Resume Sections:")
    for section, content in resume_sections.items():
        st.subheader(section)
        st.write(content)

def display_job_search_page():
    st.title("Job Search from Indeed")
    job_query = st.text_input("Enter job title", key="job_search_query")
    job_location = st.text_input("Enter location", key="job_search_location")
    if st.button("Search Jobs", key="job_search_query_button"):
        search_results = search_jobs(job_query, job_location)
        if search_results:
            display_search_results(search_results)
        else:
            st.error("No jobs found or an error occurred. Check logs for details.")

def search_jobs(query, location):
    api_key = "b66e4d12ccmsh7d79f97dce7fa4fp180e51jsn37b1eaf7a628"  # Replace with your actual RapidAPI key
    if query and location:
        jobs = fetch_jobs_from_indeed(api_key, query, location)
        return jobs
    else:
        st.error("Please enter both a job title and location.")
        return None

def fetch_jobs_from_indeed(api_key, query, location):
    url = "https://indeed12.p.rapidapi.com/jobs/search"
    querystring = {
        "query": query,
        "location": location,
        "page_id": "1",  # You can use this parameter for pagination
        "fromage": "3",  # Jobs posted within the last '3' days
        "radius": "50"   # Search within a '50' mile radius
    }
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "indeed12.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    if response.status_code == 200:
        return response.json()
    else:
        # For debugging: log the response status code and content
        st.error(f"Failed to search jobs: Status code {response.status_code}")
        st.error(f"Response content: {response.content}")
        return None

def display_search_results(search_results):
    # Display job search results
    for job in search_results.get('jobs', []):  # Assuming 'jobs' is the key in the JSON response
        st.subheader(job.get('title', 'No Title'))
        st.write(f"Company: {job.get('company', 'No Company')}")
        st.write(f"Location: {job.get('location', 'No Location')}")
        st.write(f"Description: {job.get('snippet', 'No Description')}")  # Assuming 'snippet' contains the job description
        st.markdown(f"[Job Link]({job.get('url', '#')})", unsafe_allow_html=True)

if __name__ == "__main__":
    main()