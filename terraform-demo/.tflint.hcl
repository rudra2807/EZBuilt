plugin "aws" {
  enabled = true
  version = "0.32.0" # check for latest: https://github.com/terraform-linters/tflint-ruleset-aws/releases
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

# Enable all default AWS rules
config {
  call_module_type = "all"
}

rule "aws_instance_invalid_ami" {
  enabled = true
}