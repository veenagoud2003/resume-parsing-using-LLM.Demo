import sqlite3
import json
import os

def load_job_description_keywords(job_description_file):
    """
    Load job-specific keywords from a file.
    """
    try:
        with open(job_description_file, "r", encoding="utf-8") as file:
            keywords = file.read().splitlines()  # One keyword per line
        return [keyword.strip().lower() for keyword in keywords if keyword.strip()]
    except FileNotFoundError:
        print(f"Error: Job description file not found at {job_description_file}")
        return []

def fetch_all_resumes(DATABASE_PATH):
    """
    Fetch all resume IDs from the database.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM resumes")
        resumes = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching resumes: {e}")
        resumes = []
    finally:
        conn.close()

    return [resume[0] for resume in resumes]  # Extract IDs as a list

def fetch_resume_data(resume_id, DATABASE_PATH):
    """
    Fetch all relevant data for a resume from the database.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Fetch basic resume details
        cursor.execute("SELECT resume_name, structured_data FROM resumes WHERE id = ?", (resume_id,))
        resume = cursor.fetchone()

        # Fetch skills
        cursor.execute("SELECT skill_type, skill_name FROM skills WHERE resume_id = ?", (resume_id,))
        skills = cursor.fetchall()

        # Organize data
        skill_dict = {}
        for skill_type, skill_name in skills:
            if skill_type not in skill_dict:
                skill_dict[skill_type] = []
            skill_dict[skill_type].append(skill_name)

        return {
            "resume_name": resume[0],
            "structured_data": resume[1],
            "skills": skill_dict
        }
    except sqlite3.Error as e:
        print(f"Error fetching data for Resume ID {resume_id}: {e}")
        return {}
    finally:
        conn.close()

def generate_feedback(resume_id, job_keywords, DATABASE_PATH):
    """
    Generate actionable feedback for improving the resume.
    """
    resume_data = fetch_resume_data(resume_id, DATABASE_PATH)
    if not resume_data:
        return ["Error fetching resume data."], 0

    feedback = []
    ranking = 0

    # Extract skills from the database
    skills_dict = resume_data.get("skills", {})
    extracted_skills = []
    for skill_type, skills in skills_dict.items():
        extracted_skills.extend(skills)

    # Check if skills are present
    if not extracted_skills:
        feedback.append("No skills listed. Consider adding technical and soft skills relevant to the job.")
    else:
        feedback.append(f"Skills extracted: {', '.join(extracted_skills)}")

    # Match extracted skills to job keywords
    matched_skills = [skill for skill in extracted_skills if skill.lower() in job_keywords]
    missing_keywords = [keyword for keyword in job_keywords if keyword not in map(str.lower, extracted_skills)]

    if matched_skills:
        feedback.append(f"Matched skills: {', '.join(matched_skills)}")
    if missing_keywords:
        feedback.append(f"Missing critical skills: {', '.join(missing_keywords)}. Consider adding them if relevant.")

    # Add ranking of resume based on matched skills
    if job_keywords:
        ranking = len(matched_skills) / len(job_keywords) * 100
        feedback.append(f"Resume ranking based on skills match: {ranking:.2f}%")
    else:
        feedback.append("No job keywords provided for ranking.")

    return feedback, ranking

def provide_feedback_for_all_resumes(job_desc_file, output_folder, database_path):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        # Get all resumes with their skills
        cursor.execute("""
            SELECT r.id, r.resume_name, r.structured_data,
                   GROUP_CONCAT(s.skill_name) as skills
            FROM resumes r
            LEFT JOIN skills s ON r.id = s.resume_id
            GROUP BY r.id
        """)
        
        resumes = cursor.fetchall()
        job_keywords = load_job_description_keywords(job_desc_file)
        rankings = []
        
        for resume_id, name, structured_data, skills_str in resumes:
            base_name = os.path.splitext(name)[0]
            
            try:
                # Parse skills from both structured data and skills table
                skills = []
                if skills_str:
                    skills = [s.strip() for s in skills_str.split(',')]
                
                # Match skills with keywords (case-insensitive)
                matched_skills = []
                for skill in skills:
                    for keyword in job_keywords:
                        if keyword.lower() in skill.lower():
                            matched_skills.append(skill)
                            break
                
                missing_skills = [k for k in job_keywords 
                                if not any(k.lower() in s.lower() for s in skills)]
                
                # Calculate ranking
                ranking = (len(matched_skills) / len(job_keywords)) * 100 if job_keywords else 0
                
                # Generate detailed feedback file
                feedback_path = os.path.join(output_folder, f"{base_name}_feedback.txt")
                with open(feedback_path, 'w', encoding='utf-8') as f:
                    f.write(f"Resume Feedback for {base_name}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    f.write("Skills Analysis\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Total skills found: {len(skills)}\n")
                    f.write(f"Skills: {', '.join(skills)}\n\n")
                    
                    f.write("Job Match Analysis\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Matched job skills ({len(matched_skills)}):\n")
                    f.write(f"{', '.join(matched_skills) if matched_skills else 'None'}\n\n")
                    
                    f.write("Missing Critical Skills:\n")
                    f.write(f"{', '.join(missing_skills) if missing_skills else 'None'}\n\n")
                    
                    f.write("Recommendations:\n")
                    f.write("-" * 20 + "\n")
                    if missing_skills:
                        f.write("1. Consider adding these relevant skills if you have experience with them:\n")
                        f.write("   " + ", ".join(missing_skills) + "\n")
                    f.write("2. Make sure your skills are clearly stated in your resume\n")
                    f.write("3. Use industry-standard terminology for technical skills\n\n")
                    
                    f.write(f"Overall Match Score: {ranking:.2f}%\n")
                
                rankings.append((base_name, ranking))
                print(f"Generated feedback for {base_name}")
                
            except Exception as e:
                print(f"Error processing {name}: {e}")
                rankings.append((base_name, 0))
        
        # Write rankings summary
        with open(os.path.join(output_folder, 'summary_rankings.txt'), 'w', encoding='utf-8') as f:
            f.write("Resume Rankings:\n")
            f.write("-" * 50 + "\n")
            # Sort by ranking in descending order
            for name, rank in sorted(rankings, key=lambda x: x[1], reverse=True):
                f.write(f"{name}: {rank:.2f}%\n")
        
    except Exception as e:
        print(f"Error generating feedback: {e}")
    finally:
        conn.close()