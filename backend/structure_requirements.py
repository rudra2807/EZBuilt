import base64
import os
import uuid
from google import genai
from google.genai import types
import json
from main import ValidationResult
from generate_terraform_instruction import instruction_set

# data_sources = []
# resources = []

def structure_requirements_instructions():
    schema_path = os.path.join(
        os.path.dirname(__file__),
        f"structure_requirements_instructions",
    )
    with open(schema_path, "r") as f:
        instructions = f.read()
    return instructions

def structure_requirements(requirements):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-pro"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=requirements),
            ],
        ),
    ]
    # tools = [
    #     types.Tool(googleSearch=types.GoogleSearch(
    #     )),
    # ]

    model_instructions = structure_requirements_instructions()
    generate_content_config = types.GenerateContentConfig(
        # thinkingConfig={
        #     "thinkingLevel": "HIGH"
        # },
        # tools=tools,
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text=f"""{model_instructions}"""),
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

def read_source_schema(file_name):
    schema_path = os.path.join(
        os.path.dirname(__file__),
        f"{file_name}.json",
    )
    print(f"Reading schema from: {schema_path}")
    with open(schema_path, "r") as f:
        schema = json.load(f)
    return schema

def generate_terraform_code(structured_requirements):

    print("Generating Terraform code for structured requirements:")
    print(structured_requirements)
    data_schema = read_source_schema("data_sources_list")
    available_data_sources = data_schema["available_data_sources"]

    resources_schema = read_source_schema("resources_schema")
    available_resources = resources_schema["available_resources"]

    try:
        client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
        )

        model = "gemini-2.5-pro"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=structured_requirements),
                ],
            ),
        ]
        generate_code_instrusction = instruction_set(structured_requirements, available_data_sources, available_resources)        
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction=[
                types.Part.from_text(text=f"""{generate_code_instrusction}"""),
                ],
        )
        tf_code = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            tf_code += chunk.text
        # print("Terraform code generation completed.")
        # print(tf_code)
        tf_id = str(uuid.uuid4())
        # return tf_code
        return {
            "terraform_id": tf_id,
            "status": "success",
            "validation": ValidationResult(valid=True, errors=None),
            "code": tf_code
        }
    except Exception as e:
        print(f"Error generating Terraform code: {str(e)}")
        return {
            "status": "error",
            "message": f"Error generating Terraform code: {str(e)}"
        }

if __name__ == "__main__":
    
    # data_schema = read_source_schema("data_sources_list")
    # available_data_sources = data_schema["available_data_sources"]

    # resources_schema = read_source_schema("resources_schema")
    # available_resources = resources_schema["available_resources"]

    user_requirements = input("What do you want to build today? \n")
    requirements = structure_requirements(user_requirements)
    print("Structured Requirements:")
    print(requirements)
    print("\nGenerating Terraform code...\n")
    tf_code = generate_terraform_code(requirements)
    print("Generated Terraform Code:")
    print(tf_code)
