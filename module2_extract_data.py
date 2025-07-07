import os
import requests
import json
import re
import sqlite3

API_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

# Function to extract skills from content
def extract_skills_from_content(content):
    """
    Enhanced skill extraction from text content.
    """
    skill_headers = [
        "SKILLS", "Technical Skills", "Core Competencies",
        "Technologies", "Technical Expertise", "Competencies",
        "Programming", "Languages", "Tools", "Software"
    ]
    
    # Common technical skills to look for (add more as needed)
    common_skills = [
        "python", "java", "javascript", "html", "css", "sql",
        "react", "angular", "node", "docker", "aws", "azure",
        "git", "linux", "agile", "scrum", "ci/cd"
    ]
    
    skills = set()
    lines = content.lower().split('\n')
    
    in_skills_section = False
    for line in lines:
        line = line.strip()
        
        # Check for skill section headers
        if any(header.lower() in line.lower() for header in skill_headers):
            in_skills_section = True
            continue
            
        # Exit skills section if new section found
        if in_skills_section and line and line[0].isupper() and line.endswith(':'):
            in_skills_section = False
            
        # Extract skills from lines
        if in_skills_section or any(skill in line.lower() for skill in common_skills):
            # Split on common separators
            found_skills = re.split(r'[,|•|\t|/|;|\s+]', line)
            skills.update(skill.strip() for skill in found_skills if skill.strip() and len(skill.strip()) > 1)
    
    return list(skills)

def insert_resume_data(resume_file, structured_data, db_file):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Insert resume data
        cursor.execute("""
            INSERT INTO resumes (resume_name, structured_data)
            VALUES (?, ?)
        """, (resume_file, json.dumps(structured_data)))
        
        resume_id = cursor.lastrowid
        
        # Insert skills
        if "skills" in structured_data:
            for skill in structured_data["skills"]:
                cursor.execute("""
                    INSERT INTO skills (resume_id, skill_type, skill_name)
                    VALUES (?, ?, ?)
                """, (resume_id, skill["type"], skill["name"]))
        
        conn.commit()
        print(f"Stored data for {resume_file}")
        return True
        
    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def extract_skills_from_feedback(feedback_text):
    """
    Extracts skills from the feedback text based on the format.
    Returns a list of extracted skills.
    """
    try:
        # Extract the "Skills Extracted" section from the feedback
        skills_extracted_match = re.search(r"Skills extracted: (.+?)Missing critical skills:", feedback_text, re.DOTALL)
        if skills_extracted_match:
            skills_extracted = skills_extracted_match.group(1)
            extracted_skills = [skill.strip().lstrip("+") for skill in skills_extracted.split(",") if skill.strip()]
            return extracted_skills
        else:
            print("No skills extracted section found in feedback.")
            return []
    except Exception as e:
        print(f"Error extracting skills from feedback: {e}")
        return []

# Function to process a single text file and send it to the API
def process_text_file(file_path, api_key):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text_content = f.read()

        print(f"\nProcessing file: {file_path}")

        # Simplified prompt to avoid the text prefix in response
        prompt = """Extract technical and soft skills from the resume. Return ONLY a JSON object with no additional text, exactly like this:
        {
            "skills": [
                {"type": "technical", "name": "Python"},
                {"type": "technical", "name": "JavaScript"},
                {"type": "soft", "name": "Leadership"}
            ]
        }"""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text_content}
            ],
            "temperature": 0.1
        }

        response = requests.post(API_ENDPOINT, headers=headers, json=payload)
        
        if response.status_code == 200:
            response_data = response.json()
            try:
                message_content = response_data['choices'][0]['message']['content'].strip()
                
                # Remove any text before the first '{'
                json_start = message_content.find('{')
                if json_start != -1:
                    message_content = message_content[json_start:]
                
                # Clean up any text after the last '}'
                json_end = message_content.rfind('}')
                if json_end != -1:
                    message_content = message_content[:json_end + 1]
                
                print(f"Cleaned JSON content: {message_content}")
                
                # Parse the cleaned JSON
                content = json.loads(message_content)
                
                if not content.get('skills'):
                    print("Warning: No skills found in response")
                    return {"skills": []}
                
                print(f"Extracted skills: {json.dumps(content, indent=2)}")
                return content

            except Exception as e:
                print(f"Error parsing API response: {str(e)}")
                print(f"Raw content causing error: {message_content}")
                return {"skills": []}
        else:
            print(f"API error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return None

# Function to save JSON output
def save_json_output(resume_name, data, JSONS_DIR):
    try:
        output_path = os.path.join(JSONS_DIR, f"{resume_name}.json")
        with open(output_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4)
        print(f"Saved output to {output_path}")
    except Exception as e:
        print(f"Error saving JSON output for {resume_name}: {str(e)}")

# Main logic to process all text files
def process_all_files(TEXTS_DIR, JSONS_DIR, api_key):  # Changed parameter from db_file to api_key
    if not os.path.exists(JSONS_DIR):
        os.makedirs(JSONS_DIR)

    text_files = [f for f in os.listdir(TEXTS_DIR) if f.endswith(".txt")]
    print(f"Found {len(text_files)} text files to process")
    
    for text_file in text_files:
        file_path = os.path.join(TEXTS_DIR, text_file)
        print(f"\nProcessing: {text_file}")
        processed_data = process_text_file(file_path, api_key)  # Use api_key here
        if processed_data:
            save_json_output(os.path.splitext(text_file)[0], processed_data, JSONS_DIR)
            print(f"Saved skills data: {json.dumps(processed_data, indent=2)}")