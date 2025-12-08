import os
from google import genai
from google.genai import types
import json
from model_instructions.generate_terraform_instruction import instruction_set

def _get_gemini_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Be explicit, fail early
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)

def _load_text_file(file_name: str) -> str:
    path = os.path.join("model_instructions", file_name)
    with open(path, "r") as f:
        return f.read()
    
def _load_json_file(file_name: str) -> dict:
    base_dir = os.path.dirname(__file__)
    utilities_dir = os.path.join(base_dir, "..", "utilities")
    path = os.path.join(utilities_dir, f"{file_name}.json")
    with open(path, "r") as f:
        return json.load(f)

def structure_requirements_instructions():
    return _load_text_file("structure_requirements_instructions")

def structure_requirements(requirements):
    client = _get_gemini_client()

    model = "gemini-2.5-pro"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=requirements),
            ],
        ),
    ]

    model_instructions = structure_requirements_instructions()

    generate_content_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text=model_instructions),
        ],
    )
    
    reqs = ""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        reqs += chunk.text
    return reqs

def generate_terraform_code(structured_requirements):

    print("Generating Terraform code for structured requirements:")
    print(structured_requirements)
    data_schema = _load_json_file("data_sources_list")
    available_data_sources = data_schema["available_data_sources"]

    resources_schema = _load_json_file("resources_schema")
    available_resources = resources_schema["available_resources"]

    client = _get_gemini_client()
    model = "gemini-2.5-pro"

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=structured_requirements),
            ],
        ),
    ]

    instrusctions = instruction_set(
        structured_requirements, 
        available_data_sources,
        available_resources,
    )        
    
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(text=instrusctions),
        ],
    )

    try:
        tf_code = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            tf_code += chunk.text
    except Exception as e:
        raise Exception(f"Error generating Terraform code: {str(e)}")
    
    return tf_code

if __name__ == "__main__":

    user_requirements = input("What do you want to build today? \n")
    structured = structure_requirements(user_requirements)
    print("Structured Requirements:")
    print(structured)

    print("\nGenerating Terraform code...\n")
    code = generate_terraform_code(structured)
    print("Generated Terraform Code:")
    print(code)
