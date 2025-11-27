import base64
import os
from google import genai
from google.genai import types
import json

data_sources = []
resources = []

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

    model = "gemini-2.5-flash"
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
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=structured_requirements),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(text=f"""You are an expert in generating Terraform code for AWS infrastructure based on structured requirements.

            Given the following structured requirements in JSON format, generate the corresponding Terraform code to provision the specified AWS resources.

            Requirements to implement: {json.dumps(structured_requirements, indent=2)}

            1. Use data sources mentioned below to reference existing resources (AMIs, default VPC if not specified)
            {data_sources}
            2. Only use resources mentioned below to create new resources
            {resources}
            3. Only use valid AWS resource types and arguments from the schemas provided
            4. Use realistic, valid values:
            - Instance types from the valid list
            - CIDR blocks in RFC1918 ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
            - Valid port numbers (1-65535)
            - Proper AWS region names
            5. Include all required arguments for each resource
            6. Use proper dependencies between resources
            7. Add appropriate tags (Name, Environment, ManagedBy: "EZBuilt")
            8. Follow Terraform best practices and naming conventions
            9. Output ONLY valid HCL code, no markdown formatting
            10. If a web server is mentioned, assume at least a t2.micro instance in us-east-1 with an associated security group allowing HTTP/HTTPS traffic.
            11. Always create a .pem file for SSH access to instances.
            12. Always create a security group for compute resources.
            13. Use default VPC and subnets if none are specified.
            14. Use default configurations for services unless otherwise specified.
            15. Do not add/remove resources beyond what is specified in the requirements.
            
            Terraform Code:
            """),
            ],
    )
    tf_code = ""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        tf_code += chunk.text
    return tf_code

if __name__ == "__main__":
    
    # data_schema = read_source_schema("data_sources_list")
    # available_data_sources = data_schema["available_data_sources"]

    # resources_schema = read_source_schema("resources_schema")
    # available_resources = resources_schema["available_resources"]

    user_requirements = input("What do you want to build today? \n")
    requirements = structure_requirements(user_requirements)
    print("Structured Requirements:")
    print(requirements)
    # print("\nGenerating Terraform code...\n")
    # tf_code = generate_terraform_code(requirements)
    # print("Generated Terraform Code:")
    # print(tf_code)
