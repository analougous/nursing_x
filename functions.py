import json
import os
import openai
import docx
import re

def load_docx(file_path):
    doc = docx.Document(file_path)
    return [para.text for para in doc.paragraphs]

def parse_document_sections(resume_text):
    sections = {}
    patterns = {
        'Education': [r'Education', r'Academic Background', r'Degrees'],
        'Experience': [r'Experience', r'Work History', r'Professional Experience', r'Employment History'],
        'Skills': [r'Skills', r'Abilities', r'Competencies'],
        # Add more sections as needed
    }

    for section, regex_patterns in patterns.items():
        for pattern in regex_patterns:
            # Search for the section using regex
            matches = re.finditer(pattern, resume_text, re.IGNORECASE)
            for match in matches:
                start_index = match.end()
                # Find the end of the section, assumed to be the start of the next section or end of document
                end_index = len(resume_text)
                for other_pattern in regex_patterns:
                    next_section = re.search(other_pattern, resume_text[start_index:], re.IGNORECASE)
                    if next_section:
                        end_index = min(end_index, next_section.start() + start_index)
                # Extract and store the section content
                sections[section] = resume_text[start_index:end_index].strip()
                break  # Stop after the first match for each section

    return sections

def find_relevant_section(sections, query):
    # Simple keyword matching - can be replaced with more complex NLP techniques
    for section, content in sections.items():
        if any(keyword.lower() in query.lower() for keyword in section.split()):
            return content
    return "Sorry, I couldn't find relevant information."

# Load and parse the documents
knowledge_base_hv2 = load_docx('/Users/hishamjamil/_nursing_x/Nursing_Knowledge_HV2.docx')
chatbot_data_hv3 = load_docx('/Users/hishamjamil/_nursing_x/Nursing_Knowledge_HV3.docx')

# Join the list into a single string for each document
knowledge_base_hv2_text = '\n'.join(knowledge_base_hv2)
chatbot_data_hv3_text = '\n'.join(chatbot_data_hv3)  # Make sure this line is correct

# Now pass these single strings to the parse_document_sections function
sections_hv2 = parse_document_sections(knowledge_base_hv2_text)
sections_hv3 = parse_document_sections(chatbot_data_hv3_text)  # Ensure this is using the joined string

# Example usage
query = "Tell me about nursing classifications in Canada"
response = find_relevant_section(sections_hv2, query)  # For HV2
# response = find_relevant_section(sections_hv3, query)  # For HV3

print(response)


def create_assistant(client, name, description, sections_hv2, sections_hv3, model='gpt-3.5-turbo'):
    assistant_file_path = 'assistant.json'
    assistant_id = None

    # Convert sections to JSON strings
    training_data_hv2 = json.dumps(sections_hv2)
    training_data_hv3 = json.dumps(sections_hv3)


    try:
        if os.path.exists(assistant_file_path):
            with open(assistant_file_path, 'r') as file:
                assistant_data = json.load(file)
                assistant_id = assistant_data.get('assistant_id', None)
                print("Loaded existing assistant ID.")
        else:
            # Create the file object in the OpenAI system for HV2 and HV3
            file_object_hv2 = client.files.create(file=training_data_hv2, purpose='assistants')
            file_object_hv3 = client.files.create(file=training_data_hv3, purpose='assistants')

            # Detailed instructions for the assistant, now including the description
            instructions = (
                f"{description} "
                "Welcome to the Nursing Resume Assistant, powered by ChatGPT and specialized for international nurses. "
                "This assistant is designed to guide you through customizing your resume to meet Canadian healthcare standards, "
                "as outlined in Nursing Knowledge HV3. We recommend following these steps for optimal assistance: "
                "1. Upload Your Resume: Start by uploading your current resume for analysis. "
                "2. Upload a Job Description: Next, upload a job description for a role you are interested in. "
                "3. Interactive Queries: Ask specific questions about adapting your resume to the job description and Canadian standards. "
                "4. Skill Gap Analysis: The assistant will help identify any skill gaps compared to Canadian nursing requirements. "
                "5. Resume Enhancement: Receive suggestions for improving your resume, including keyword optimization and alignment with Canadian standards. "
                "6. Tailored Advice: Get personalized advice for customizing your resume, based on your professional experience and the job you're targeting. "
                "Feel free to navigate these steps in any order, and use the provided Nursing Knowledge HV3 document for detailed guidance."
            )

            # Create the assistant
            assistant = openai.Assistant.create(
                name=name,
                description=description,
                instructions=instructions,
                model=model,
                tools=[{"type": "retrieval"}],
                file_ids=[file_object_hv2.id, file_object_hv3.id]  # Use the IDs of the file objects
            )

            # Save the assistant ID
            with open(assistant_file_path, 'w') as file:
                json.dump({'assistant_id': assistant.id}, file)
                print("Created a new assistant and saved the ID.")

            assistant_id = assistant.id

    except Exception as e:
        print(f"Error in creating assistant: {e}")

    return assistant_id


def improved_parse_document_sections(resume_text):
    sections = {}
    patterns = {
        'Objective': r'Objective',
        'Education': r'Education',
        'Experience': r'Experience',
        'Skills': r'Skills',
        'Certifications': r'Certifications',
        'Awards': r'Awards',
        'Volunteering': r'Volunteering'
    }

    for section, pattern in patterns.items():
        match = re.search(pattern, resume_text, re.IGNORECASE)
        if match:
            start = match.end()
            end = len(resume_text)
            for other_section, other_pattern in patterns.items():
                if other_section != section:
                    other_match = re.search(other_pattern, resume_text, re.IGNORECASE)
                    if other_match and other_match.start() > start:
                        end = min(end, other_match.start())
            sections[section] = resume_text[start:end].strip()

    return sections



def analyze_and_suggest_improvements(resume_sections):
    suggestions = {}
    for section, content in resume_sections.items():
        if section == 'Objective':
            # Analyze and suggest improvements for the Objective section
            suggestions[section] = 'Consider making your objective more concise and focused.'
        # Add more analysis for other sections as needed
    return suggestions

