import os
from google import genai
from google.genai import types
import json
from model_instructions.generate_terraform_instruction import instruction_set
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()

def _get_gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment variables")
    return genai.Client(api_key=api_key)

def _load_text_file(file_name: str) -> str:
    """Load a text file from model_instructions (path relative to backend root)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(base_dir, "model_instructions", file_name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    
def _load_json_file(file_name: str) -> dict:
    base_dir = os.path.dirname(__file__)
    utilities_dir = os.path.join(base_dir, "..", "utilities")
    path = os.path.join(utilities_dir, f"{file_name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def structure_requirements_instructions():
    return _load_text_file("structure_requirements_instructions")

def structure_requirements(requirements: str) -> str:
    """Structure natural language requirements into JSON using Gemini"""
    print(f"[structure_requirements] Starting to structure requirements (length: {len(requirements)} chars)")
    
    try:
        client = _get_gemini_client()
        model = "gemini-2.5-flash"
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=requirements),
                ],
            ),
        ]

        model_instructions = structure_requirements_instructions()
        print(f"[structure_requirements] Loaded instructions (length: {len(model_instructions)} chars)")

        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            system_instruction=[
                types.Part.from_text(text=model_instructions),
            ],
        )
        
        print("[structure_requirements] Calling Gemini API...")
        reqs = ""
        chunk_count = 0
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            chunk_count += 1
            reqs += chunk.text
            if chunk_count % 5 == 0:
                print(f"[structure_requirements] Received {chunk_count} chunks, total length: {len(reqs)}")
        
        print(f"[structure_requirements] Completed! Total chunks: {chunk_count}, final length: {len(reqs)}")
        return reqs
    
    except Exception as e:
        print(f"[structure_requirements] ERROR: {str(e)}")
        raise Exception(f"Error structuring requirements: {str(e)}")

def generate_terraform_code(structured_requirements: str) -> str:
    """Generate Terraform code from structured requirements using Gemini"""
    print(f"[generate_terraform_code] Starting generation (input length: {len(structured_requirements)} chars)")
    
    try:
        data_schema = _load_json_file("data_sources_list")
        available_data_sources = data_schema["available_data_sources"]
        print(f"[generate_terraform_code] Loaded {len(available_data_sources)} data sources")

        resources_schema = _load_json_file("resources_schema")
        available_resources = resources_schema["available_resources"]
        print(f"[generate_terraform_code] Loaded {len(available_resources)} resources")

        client = _get_gemini_client()
        model = "gemini-2.5-flash"

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=structured_requirements),
                ],
            ),
        ]

        instructions = instruction_set(
            structured_requirements, 
            available_data_sources,
            available_resources,
        )
        print(f"[generate_terraform_code] Generated instructions (length: {len(instructions)} chars)")
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction=[
                types.Part.from_text(text=instructions),
            ],
        )

        print("[generate_terraform_code] Calling Gemini API...")
        tf_code = ""
        chunk_count = 0
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            chunk_count += 1
            tf_code += chunk.text
            if chunk_count % 10 == 0:
                print(f"[generate_terraform_code] Received {chunk_count} chunks, total length: {len(tf_code)}")
        
        print(f"[generate_terraform_code] Completed! Total chunks: {chunk_count}, final length: {len(tf_code)}")
        return tf_code
    
    except Exception as e:
        print(f"[generate_terraform_code] ERROR: {str(e)}")
        raise Exception(f"Error generating Terraform code: {str(e)}")

if __name__ == "__main__":
    user_requirements = input("What do you want to build today? \n")
    structured = structure_requirements(user_requirements)
    print("Structured Requirements:")
    print(structured)

    print("\nGenerating Terraform code...\n")
    code = generate_terraform_code(structured)
    print("Generated Terraform Code:")
    print(code)
