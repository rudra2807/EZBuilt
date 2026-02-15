import os
import json
import boto3
from botocore.exceptions import ClientError
from model_instructions.generate_terraform_instruction import instruction_set
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv(".env.local")

# Bedrock config: region and model from env, with defaults
BEDROCK_REGION = os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID") or "anthropic.claude-3-5-sonnet-v2:0"
print(BEDROCK_MODEL_ID)


def _get_bedrock_client():
    """Return a Bedrock Runtime client using configured region and default credential chain."""
    return boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def _invoke_bedrock_stream(system_text: str, user_text: str) -> str:
    """
    Call Bedrock Converse streaming API with system + user message; return accumulated text.
    """
    client = _get_bedrock_client()
    response = client.converse_stream(
        modelId=BEDROCK_MODEL_ID,
        inferenceConfig={
            "temperature":0.1
        },
        messages=[
            {
                "role": "user",
                "content": [{"text": user_text}],
            }
        ],
        system=[{"text": system_text}],
    )
    out = []
    for chunk in response.get("stream", []):
        if "contentBlockDelta" in chunk:
            delta = chunk["contentBlockDelta"].get("delta", {})
            text = delta.get("text") or ""
            if text:
                out.append(text)
    return "".join(out)


def _load_text_file(file_name: str) -> str:
    """Load a text file from model_instructions (path relative to backend root via __file__)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    """Structure natural language requirements into JSON using Bedrock"""
    print(f"[structure_requirements] Starting to structure requirements (length: {len(requirements)} chars)")

    try:
        model_instructions = structure_requirements_instructions()
        print(f"[structure_requirements] Loaded instructions (length: {len(model_instructions)} chars)")

        print("[structure_requirements] Calling Bedrock API...")
        reqs = _invoke_bedrock_stream(model_instructions, requirements)
        
        # structured_json = json.loads(reqs)
        
        assert 'project_metadata' in reqs
        assert 'components' in reqs
        
        print(f"[structure_requirements] Completed! Response length: {len(reqs)}")
        return reqs

    except ClientError as e:
        print(f"[structure_requirements] ERROR: {str(e)}")
        raise Exception(f"Error structuring requirements: {str(e)}")
    except Exception as e:
        print(f"[structure_requirements] ERROR: {str(e)}")
        raise Exception(f"Error structuring requirements: {str(e)}")

def generate_terraform_code(structured_requirements: str) -> str:
    """Generate Terraform code from structured requirements using Bedrock"""
    print(f"[generate_terraform_code] Starting generation (input length: {len(structured_requirements)} chars)")

    try:
        # data_schema = _load_json_file("data_sources_list")
        # available_data_sources = data_schema["available_data_sources"]
        # print(f"[generate_terraform_code] Loaded {len(available_data_sources)} data sources")

        # resources_schema = _load_json_file("resources_schema")
        # available_resources = resources_schema["available_resources"]
        # print(f"[generate_terraform_code] Loaded {len(available_resources)} resources")

        instructions = instruction_set(
            json.dumps(structured_requirements, indent=2)
        )
        print(f"[generate_terraform_code] Generated instructions (length: {len(instructions)} chars)")

        print("[generate_terraform_code] Calling Bedrock API...")
        tf_code_str = _invoke_bedrock_stream(instructions, structured_requirements)

        cleaned = tf_code_str.strip()

        # Remove markdown fences if present
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]  # remove first fence
            cleaned = cleaned.replace("json", "", 1).strip()

        terraform_output = json.loads(cleaned)
        # terraform_output = json.loads(tf_code_str)

        assert 'files' in terraform_output
        assert 'main.tf' in terraform_output['files']
        assert 'variables.tf' in terraform_output['files']
        assert 'outputs.tf' in terraform_output['files']
        
        print(f"[generate_terraform_code] Completed! Response length: {len(terraform_output)}")
        return terraform_output

    except ClientError as e:
        print(f"[generate_terraform_code] ERROR: {str(e)}")
        raise Exception(f"Error generating Terraform code: {str(e)}")
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
