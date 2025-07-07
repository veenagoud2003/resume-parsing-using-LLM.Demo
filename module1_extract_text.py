import os
import fitz  # PyMuPDF for PDF text extraction
from PIL import Image
import pytesseract
import io

# Specify the path to the Tesseract executable (adjust this for your OS)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Adjust path as needed

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using PyMuPDF (fitz).
    Handles both textual and image-based PDFs by using OCR for images.
    """
    doc = fitz.open(pdf_path)  # Open the PDF document
    text = ""

    for page_num in range(len(doc)):  # Iterate through each page
        page = doc[page_num]
        
        # Extract text directly from the page
        text += page.get_text("text")  # "text" is the default method for extracting text
        
        # Handle image-based PDFs via OCR
        for img_index, img in enumerate(page.get_images(full=True)):  # Check for images on the page
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))  # Convert image bytes into a PIL Image object
            
            # Use pytesseract to extract text from the image
            text += pytesseract.image_to_string(image)
    
    return text

def batch_process_pdfs(input_folder, output_folder):
    """Process PDFs to text and return list of generated text files"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    processed_files = []
    
    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(input_folder, filename)
            print(f"Processing: {filename}")
            
            # Extract text from PDF
            text = extract_text_from_pdf(pdf_path)
            
            # Save text file
            txt_filename = f"{os.path.splitext(filename)[0]}.txt"
            output_path = os.path.join(output_folder, txt_filename)
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(text)
            
            processed_files.append(txt_filename)
            print(f"Processed: {filename}, saved to {output_path}")
    
    return processed_files