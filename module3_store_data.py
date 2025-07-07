import os
import sqlite3
import json

# Function to initialize the database and create the required tables
def initialize_database(db_file):
    try:
        print("Initializing database...")
        # Ensure the directory for the database exists
        if not os.path.exists(os.path.dirname(db_file)):
            os.makedirs(os.path.dirname(db_file))

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Create the 'resumes' table if it doesn't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS resumes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            resume_name TEXT NOT NULL,
                            structured_data TEXT NOT NULL,
                            feedback TEXT NOT NULL
                        )''')

        # Create the 'skills' table if it doesn't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS skills (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            resume_id INTEGER NOT NULL,
                            skill_type TEXT NOT NULL,
                            skill_name TEXT NOT NULL,
                            FOREIGN KEY(resume_id) REFERENCES resumes(id)
                        )''')

        conn.commit()
        conn.close()
        print("Database initialized and tables created (if not already present).")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Function to insert resume data into the database
def insert_resume_data(resume_file, structured_data_dir, feedback_dir, db_file):
    try:
        resume_name = os.path.basename(resume_file)
        json_file_path = os.path.join(feedback_dir, f"{os.path.splitext(resume_name)[0]}.json")

        if os.path.exists(json_file_path):
            # Load and verify the JSON structured data
            with open(json_file_path, 'r', encoding="utf-8") as f:
                structured_data = json.load(f)
                
            # Debug print
            print(f"\nProcessing resume: {resume_name}")
            print(f"Structured data: {json.dumps(structured_data, indent=2)}")

            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # Store the structured JSON data
            cursor.execute('''INSERT INTO resumes (resume_name, structured_data, feedback)
                            VALUES (?, ?, ?)''', 
                            (resume_name, 
                             json.dumps(structured_data),
                             json.dumps({})))
            
            resume_id = cursor.lastrowid

            # Insert skills with better error handling
            if 'skills' in structured_data and structured_data['skills']:
                for skill in structured_data['skills']:
                    try:
                        if isinstance(skill, dict) and 'type' in skill and 'name' in skill:
                            cursor.execute('''INSERT INTO skills (resume_id, skill_type, skill_name)
                                           VALUES (?, ?, ?)''', 
                                           (resume_id, 
                                            skill['type'],
                                            skill['name']))
                        else:
                            print(f"Skipping invalid skill format: {skill}")
                    except Exception as e:
                        print(f"Error inserting skill {skill}: {e}")

            conn.commit()
            conn.close()
            print(f"Successfully processed and stored data for {resume_name}")
        else:
            print(f"Missing structured data file: {json_file_path}")
    except Exception as e:
        print(f"Error processing {resume_name}: {e}")

# Function to insert skills into the 'skills' table
def insert_skills(resume_id, skills, conn, cursor):
    try:
        for skill in skills:
            skill_type = skill.get("type", "Unknown")  # Adjust if structure is different
            skill_name = skill.get("name", "Unknown")
            cursor.execute('''INSERT INTO skills (resume_id, skill_type, skill_name)
                             VALUES (?, ?, ?)''', (resume_id, skill_type, skill_name))
    except Exception as e:
        print(f"Error inserting skills for resume ID {resume_id}: {e}")

# Function to process all resumes in the resumes directory
def process_resumes(resume_dir, structured_data_dir, feedback_dir, db_file):
    """Process all resumes in the resumes directory"""
    print("Processing resumes...")
    
    # Initialize database if not exists
    initialize_database(db_file)
    
    processed_count = 0
    error_count = 0
    
    try:
        # Get all PDF files
        resume_files = [f for f in os.listdir(resume_dir) if f.endswith('.pdf')]
        
        for resume_file in resume_files:
            resume_path = os.path.join(resume_dir, resume_file)
            try:
                insert_resume_data(resume_path, structured_data_dir, feedback_dir, db_file)
                processed_count += 1
            except Exception as e:
                print(f"Error processing {resume_file}: {e}")
                error_count += 1
                
        print(f"\nProcessing complete:")
        print(f"Successfully processed: {processed_count}")
        print(f"Errors encountered: {error_count}")
        
    except Exception as e:
        print(f"Error during resume processing: {e}")
        
    return processed_count, error_count