"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";

// Type definition for Terraform validation result (matches backend ValidationResult)
interface TerraformValidation {
    valid: boolean;
    errors?: string | null;
}


const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type GenerationState =
    | "idle"
    | "generating"
    | "generated"
    | "error";

export default function GenerateTerraformPage() {
    const router = useRouter();

    const [requirements, setRequirements] = useState("");
    const [generationState, setGenerationState] =
        useState<GenerationState>("idle");
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    const [validation, setValidation] = useState<TerraformValidation | null>(null);
    const [terraformId, setTerraformId] = useState<string | null>(null);

    const { user, loading: authLoading } = useAuth();
    const userId = user?.sub || null;

    const examples = [
        {
            label: "Simple web app on EC2",
            text:
                "Provision a VPC with 2 public subnets in us-east-1, a security group that allows HTTP and SSH from my IP, and a single t3.micro EC2 instance running Ubuntu in one subnet. Attach an internet gateway and route table so the instance has internet access. Tag everything with project = ezbuilt-demo.",
        },
        {
            label: "Static website on S3 and CloudFront",
            text:
                "Create an S3 bucket for a static website, with public read access only through CloudFront. Add a CloudFront distribution with HTTPS enabled using the default certificate, caching static assets. Block direct S3 access and log requests to a separate logs bucket.",
        },
        {
            label: "Managed Postgres on RDS",
            text:
                "Create a new VPC with private subnets and security groups for an AWS RDS Postgres instance. Use a db.t3.micro instance with 20 GB storage, automatic backups for 7 days, and disallow public access. Output the endpoint as a Terraform output.",
        },
    ];

    useEffect(() => {
        console.log("Auth loading:", authLoading, "User ID:", userId);
        console.log(terraformId)
    }, [authLoading, userId]);

    const handleUseExample = (text: string) => {
        setRequirements(text);
        setErrorMsg(null);
        setGenerationState("idle");
        setValidation(null);
        setTerraformId(null);
    };

    const handleGenerate = async () => {
        if (!requirements.trim()) {
            setErrorMsg("Write at least one clear requirement first.");
            return;
        }

        setGenerationState("generating");
        setErrorMsg(null);
        setValidation(null);
        setTerraformId(null);

        try {
            const res = await fetch(`${API_BASE_URL}/api/structure-requirements`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    user_id: userId,
                    requirements: requirements,
                }),
            });

            if (!res.ok) {
                const data = await res.json().catch(() => null);
                const msg =
                    data?.detail ||
                    "Terraform generation failed. Check the requirements and try again.";
                throw new Error(msg);
            }

            const data = await res.json();

            if (data.status !== "success") {
                setGenerationState("error");
                setErrorMsg(
                    data.message ||
                    "Generation returned an error. Review your requirements."
                );
                setValidation(data.validation || null);
                return;
            }

            const tfId = data.terraform_id as string | undefined;
            const tfValidation = (data.validation || null) as TerraformValidation | null;

            // Note: Terraform code is now stored in S3, not returned directly
            // We'll fetch it on the deploy page when needed
            setValidation(tfValidation);
            setTerraformId(tfId || null);
            setGenerationState("generated");

        } catch (err: any) {
            setGenerationState("error");
            setErrorMsg(err.message || "Unexpected error while generating Terraform.");
        }
    };

    const handleContinueToDeploy = () => {
        if (!terraformId) return;
        router.push(`/deploy?terraformId=${encodeURIComponent(terraformId)}`);
    };

    const charCount = requirements.length;
    const wordCount = requirements.trim()
        ? requirements.trim().split(/\s+/).length
        : 0;

    const isValid = validation?.valid;

    return (
        <div className="min-h-screen bg-slate-950 text-slate-50">
            {/* Top bar */}
            {/* <header className="border-b border-slate-800">
                <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4">
                    <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-2xl bg-gradient-to-br from-indigo-400 to-fuchsia-500 flex items-center justify-center shadow-lg">
                            <span className="text-xl">🚀</span>
                        </div>
                        <div>
                            <h1 className="text-xl font-semibold tracking-tight">
                                EZBuilt Platform
                            </h1>
                            <p className="text-xs text-slate-400">
                                Infrastructure as a conversation, deployed on your cloud
                            </p>
                        </div>
                    </div>

                    <div className="hidden md:flex items-center gap-4 text-xs text-slate-400">
                        <span className="text-slate-500">Step 2 of 4</span>
                        <span className="inline-flex items-center gap-1 rounded-full border border-indigo-500/40 bg-indigo-500/10 px-3 py-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-indigo-300 animate-pulse" />
                            <span>Terraform generated in your browser</span>
                        </span>
                    </div>
                </div>
            </header> */}

            {/* Main content */}
            <main className="max-w-7xl mx-auto px-6 py-10 lg:py-14">
                <div className="grid lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] gap-10 items-start">
                    {/* Left: requirement input */}
                    <section className="space-y-6">
                        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs text-indigo-200">
                            <span>Describe what you want to provision</span>
                        </div>

                        <div className="space-y-3">
                            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
                                Tell EZBuilt what to create in your AWS account
                            </h2>
                            <p className="text-sm md:text-base text-slate-300 max-w-xl">
                                Write requirements in plain English. Include regions, services,
                                sizing, security constraints, and any naming or tagging rules
                                you care about.
                            </p>
                        </div>

                        {/* Example chips */}
                        <div className="space-y-2">
                            <p className="text-xs text-slate-400">
                                Start from a template, then tweak it.
                            </p>
                            <div className="flex flex-wrap gap-2">
                                {examples.map((ex) => (
                                    <button
                                        key={ex.label}
                                        type="button"
                                        onClick={() => handleUseExample(ex.text)}
                                        className="text-xs rounded-full border border-slate-700 bg-slate-900/60 px-3 py-1 text-slate-200 hover:border-indigo-400 hover:text-indigo-100"
                                    >
                                        {ex.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Textarea */}
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs">
                                <span className="font-medium text-slate-200">
                                    Infrastructure requirements
                                </span>
                                <span className="text-slate-500">
                                    {wordCount} words • {charCount} characters
                                </span>
                            </div>

                            <div className="relative">
                                <textarea
                                    value={requirements}
                                    onChange={(e) => setRequirements(e.target.value)}
                                    rows={10}
                                    className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-y"
                                    placeholder="Example: Create a highly available web tier with an Application Load Balancer, two private subnets with EC2 instances, and an RDS Postgres instance in a separate subnet group. All resources in us-east-1 with tags environment = staging and project = ezbuilt."
                                />

                                {/* subtle gradient border when there is text */}
                                {requirements.trim() && (
                                    <div className="pointer-events-none absolute inset-0 rounded-2xl border border-indigo-500/40 ring-1 ring-indigo-500/20" />
                                )}
                            </div>

                            {errorMsg && (
                                <div className="mt-2 rounded-xl border border-red-500/70 bg-red-500/10 px-3 py-2 text-xs text-red-100">
                                    {errorMsg}
                                </div>
                            )}

                            <div className="flex flex-wrap items-center gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={handleGenerate}
                                    disabled={generationState === "generating"}
                                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed"
                                >
                                    {generationState === "generating" ? (
                                        <>
                                            <span className="h-3 w-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                                            <span>Generating Terraform</span>
                                        </>
                                    ) : (
                                        <>
                                            <span>Generate Terraform</span>
                                        </>
                                    )}
                                </button>

                                <p className="text-[11px] text-slate-500">
                                    We run Terraform validate server side before you deploy.
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* Right: generated code and validation */}
                    <section>
                        <div className="relative">
                            <div className="pointer-events-none absolute inset-0 blur-3xl bg-gradient-to-br from-indigo-500/40 via-fuchsia-500/20 to-sky-500/20 opacity-40" />
                            <div className="relative rounded-3xl border border-slate-800 bg-slate-900/90 backdrop-blur-md shadow-2xl p-6 md:p-7 space-y-5">
                                {/* Status header */}
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`h-2.5 w-2.5 rounded-full ${generationState === "generated" && isValid
                                                ? "bg-emerald-400"
                                                : generationState === "generating"
                                                    ? "bg-amber-300"
                                                    : "bg-slate-500"
                                                }`}
                                        />
                                        <p className="text-xs font-medium text-slate-200">
                                            {generationState === "idle" && "Waiting for input"}
                                            {generationState === "generating" &&
                                                "Generating and validating Terraform"}
                                            {generationState === "generated" && isValid &&
                                                "Terraform generated and validated"}
                                            {generationState === "generated" && !isValid &&
                                                "Generated but validation failed"}
                                            {generationState === "error" && "Error while generating"}
                                        </p>
                                    </div>
                                    {terraformId && (
                                        <p className="text-[11px] text-slate-500">
                                            Plan id: <span className="font-mono">{terraformId}</span>
                                        </p>
                                    )}
                                </div>

                                {/* Validation summary */}
                                {validation && (
                                    <div
                                        className={`rounded-2xl border px-4 py-3 text-xs ${validation.valid
                                            ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-100"
                                            : "border-amber-500/60 bg-amber-500/10 text-amber-100"
                                            }`}
                                    >
                                        {validation.valid ? (
                                            <p>Terraform validate succeeded for this plan.</p>
                                        ) : (
                                            <>
                                                <p className="font-medium mb-1">
                                                    Terraform validate reported errors.
                                                </p>
                                                <pre className="whitespace-pre-wrap break-words text-[11px]">
                                                    {validation.errors ||
                                                        "No error message returned from validator."}
                                                </pre>
                                            </>
                                        )}
                                    </div>
                                )}

                                {/* Status message - code is stored in S3 */}
                                {generationState === "generated" && validation?.valid && (
                                    <div className="rounded-2xl border border-slate-700 bg-slate-900/60 px-4 py-3 text-xs text-slate-300">
                                        <p>
                                            Terraform code has been generated and stored securely.
                                            You'll be able to review and edit it on the deployment page.
                                        </p>
                                    </div>
                                )}

                                {/* Continue button */}
                                <div className="flex flex-wrap items-center gap-3 pt-1">
                                    <button
                                        type="button"
                                        onClick={handleContinueToDeploy}
                                        disabled={!terraformId || !validation?.valid}
                                        className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 shadow hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        Continue to deploy
                                    </button>
                                    <p className="text-[11px] text-slate-500">
                                        Review and edit the Terraform code before deployment.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
}
