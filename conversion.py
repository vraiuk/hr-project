import os
from pypdf import PdfReader
import re

def sanitize_filename(filename):
    # Remove file extension and sanitize the name
    base_name = os.path.splitext(filename)[0]
    # Replace non-alphanumeric characters with underscore
    return re.sub(r'[^\w\s-]', '_', base_name)

def convert_pdf_to_markdown(input_folder, output_folder):
    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Process each PDF file in the input folder
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(input_folder, filename)
            md_filename = f"{sanitize_filename(filename)}.md"
            md_path = os.path.join(output_folder, md_filename)
            
            try:
                # Read PDF
                reader = PdfReader(pdf_path)
                
                # Extract text from each page
                with open(md_path, 'w', encoding='utf-8') as md_file:
                    md_file.write(f"# {sanitize_filename(filename)}\n\n")
                    
                    for page in reader.pages:
                        text = page.extract_text()
                        if text:
                            md_file.write(text + "\n\n")
                            
                print(f"Converted: {filename} -> {md_filename}")
                
            except Exception as e:
                print(f"Error converting {filename}: {str(e)}") 