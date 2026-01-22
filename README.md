# EZBuilt

## Motivation

Setting up cloud infrastructure is still painful.

Even experienced developers waste hours translating ideas like “I need a backend with auth and a database” into Terraform, IAM policies, networking configs, and deployment pipelines. Beginners struggle even more. They either over provision insecure infrastructure or give up and click around the cloud console, which is worse.

Existing tools fail in one of two ways:

- High level platforms hide everything and lock you in
- Low level tools like Terraform are powerful but require deep cloud knowledge and boilerplate

The gap is clear. Developers know what they want, but tools force them to manually figure out how to build it.

EZBuilt exists to close that gap.

---

## What EZBuilt Does

EZBuilt converts plain English infrastructure requirements into secure, production ready cloud infrastructure, without taking control away from the developer.

You describe what you want.  
EZBuilt generates and deploys the infrastructure safely in your own cloud account.

No clicking.  
No copy pasting random Terraform.  
No black box deployments.

---

## Core Architecture

EZBuilt is designed as a multi stage infrastructure automation pipeline, not a single prompt based generator.

### Stage 1: Requirement Understanding

- Parses natural language infrastructure requirements
- Infers architecture patterns and non functional constraints
- Preserves expert level instructions without overriding intent
- Produces a structured JSON specification as the source of truth

This step prevents hallucinated or unsafe infrastructure.

---

### Stage 2: Infrastructure Provisioning (Terraform)

- Converts structured requirements into Terraform HCL
- Uses secure, production friendly defaults
- Avoids pseudo code and placeholders
- Keeps architectures simple and auditable
- Outputs real Terraform that can be reviewed and version controlled

The result is reproducible, boring infrastructure. Exactly what you want.

---

### Stage 3: Post Provision Configuration (Ansible - In Progress)

Infrastructure alone is not enough.

EZBuilt is actively integrating Ansible to handle post provisioning configuration such as:

- Server hardening and baseline security
- Application runtime setup
- Service configuration and environment bootstrapping
- Consistent configuration across environments

Terraform handles what gets created.  
Ansible handles how it is configured.

This separation keeps the system clean, flexible, and production ready.

---

### Stage 4: Controlled Deployment and Lifecycle

- Uses IAM role assumption with External IDs
- Never requires long lived cloud credentials
- Deploys directly into the user’s cloud account
- Tracks deployments and supports safe destroy operations

EZBuilt never owns your infrastructure. You do.

---

## Why This Is Different

EZBuilt is not another AI DevOps demo.

What sets it apart:

- Structured intermediate representation instead of free form prompting
- Security first design using cloud native IAM patterns
- Terraform and Ansible outputs are fully visible and reusable
- No vendor lock in or hidden abstractions
- Built for real infrastructure, not toy examples

This is a developer experience platform, not a chatbot.

---

## Who This Is For

- Developers who understand systems but hate boilerplate
- Beginners who want safe infrastructure without console chaos
- Startup engineers without dedicated DevOps teams
- Anyone tired of rewriting Terraform and configuration scripts

---

## Current Capabilities

- AWS focused infrastructure generation
- Secure IAM role based deployment
- Terraform based provisioning
- Deployment tracking and destroy workflows
- Early Ansible integration for configuration management

---

## Roadmap

- Full Ansible based configuration workflows
- Multi cloud support across AWS, GCP, and Azure
- Cost aware infrastructure suggestions
- Policy driven security and compliance checks
- Infrastructure drift detection and reconciliation

---

## Philosophy

EZBuilt follows three principles:

1. The user owns their cloud and their code
2. AI assists decisions, it does not hide them
3. Infrastructure should be boring, secure, and repeatable

If you think infrastructure automation should reduce effort without increasing risk, this project is for you.
