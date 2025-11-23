#!/usr/bin/env bash
# Usage: run in a directory initialized with the AWS provider
terraform init -input=false
terraform providers schema -json \
  | jq -r '.provider_schemas["registry.terraform.io/hashicorp/aws"].data_source_schemas | keys[]' \
  | sort > aws-data-sources-full-list.txt
echo "List saved to aws-data-sources-full-list.txt"

