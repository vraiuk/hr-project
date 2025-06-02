import os
import json
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_openai_client():
    """Initialize the OpenAI client"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)

def get_json_template(path):
    """Return the template for CV JSON structure"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def convert_all_cvs(input_folder, output_folder):
    """Convert all CVs in the input folder to JSON format"""
    # Initialize OpenAI client
    client = init_openai_client()
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all markdown files
    markdown_files = [f for f in os.listdir(input_folder) if f.endswith(".md")]
    
    # Process all markdown files
    success_count = 0
    total_count = len(markdown_files)
    
    for index, filename in enumerate(markdown_files, start=1):
        input_path = os.path.join(input_folder, filename)
        try:
            # Generate JSON
            result_json = convert_cv_to_json(input_path, client)
            # print(result_json)

            # Update ID to use index
            # result_json["id"] = str(index)
            
            # Save to output folder
            output_path = os.path.join(output_folder, f"{index}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result_json, f, ensure_ascii=False, indent=2)
            
            success_count += 1
            print(f"Successfully converted {filename} to {index}.json")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    return success_count, total_count

def convert_cv_to_json(markdown_path, client):
    """Convert a single CV from markdown to JSON"""
    # Create prompt template
    json_structure_str = json.dumps(get_json_template("./tests/cv_scored_example.json"), ensure_ascii=False, indent=2)
    # json_position_str = json.dumps(get_json_template("./tests/position_info.json"), ensure_ascii=False, indent=2)
    prompt_template = (
        "Оцени резюме, которое приходит на вход и верни его оценку релевантности для переданной вакансии ниже, оцени каждый аспект резюме в диапозоне от 0.00 до 1.00, как-будто ты являешься опытным hr специалистом, используй следующую структуру для оценки, проверь что в ответе один объект строго в формате json\n"
        f"{json_structure_str}\n\n"
    )


    with open("./tests/position_info.md", "r", encoding="utf-8") as f:
        position_str = f.read()


    # Read markdown content
    with open(markdown_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    # Combine prompt and markdown
    prompt = ('оцени резюме\n' + markdown_content + "\n") #+ "для вакансии ниже\n" + position_str + "\n\n")
    print("prompt_template", prompt_template)
    print("prompt", prompt)

    # Generate response using OpenAI
    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",
    #     messages=[
    #         # {"role": "system", "content": prompt_template},
    #         {"role": "user", "content": prompt_template + prompt}
    #     ],
    #     max_completion_tokens=300
    # )

    # Extract the generated text
    # generated_text = response.choices[0].message.content.strip()
    generated_text = "```json\n{\n  \"id\": \"1\",\n  \"fullName\": \"Канин Юрий\",\n  \"location\": 0.8,\n  \"jobPreferences\": 0.9,\n  \"experience\": {\n    \"totalYears\": 0.75,\n    \"relevance\": 0.85\n  },\n  \"education\": 0.7,\n  \"courses\": 0.0,\n  \"skills\": 0.95,\n  \"languages\": 0.8,\n  \"additionalInfo\": 0.6\n}\n```"

    print("generated_text: " + generated_text + 'end')
    
    try:
        # Parse the generated text as JSON
        # Remove markdown code block markers if present
        generated_text = generated_text.strip()
        if generated_text.startswith("```json"):
            generated_text = generated_text[7:]
        if generated_text.endswith("```"):
            generated_text = generated_text[:-3]
        generated_text = generated_text.strip()
        
        result_json = json.loads(generated_text)
        return result_json
    except json.JSONDecodeError as e:
        raise Exception(f"Error parsing JSON: {e}") 