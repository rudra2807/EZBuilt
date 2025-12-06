"use client";

import React, { useEffect, useState, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
    loadTerraformPlan,
    TerraformPlan,
    saveTerraformPlan,
} from "@/app/lib/saveTerraformPlan";

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// TODO - replace with real user id from auth
const DEMO_USER_ID = "demo-user-123";

type DeploymentStatusResponse = {
    deployment_id: string;
    status: string;
    output: string;
    started_at?: string | null;
    completed_at?: string | null;
};

type Operation = "apply" | "destroy";

export default function DeployPage() {
    const searchParams = useSearchParams();
    const router = useRouter();

    const terraformId = searchParams.get("terraformId");

    const [plan, setPlan] = useState<TerraformPlan | null>(null);
    const [planLoading, setPlanLoading] = useState(true);
    const [planError, setPlanError] = useState<string | null>(null);

    const [deploymentId, setDeploymentId] = useState<string | null>(null);
    const [deploymentStatus, setDeploymentStatus] = useState<string | null>(null);
    const [deploymentOutput, setDeploymentOutput] = useState<string>("");
    const [deploymentError, setDeploymentError] = useState<string | null>(null);
    const [startingDeployment, setStartingDeployment] = useState(false);

    const [operation, setOperation] = useState<Operation>("apply");

    const [isEditingCode, setIsEditingCode] = useState(false);
    const [editedCode, setEditedCode] = useState("");
    const [savingEdit, setSavingEdit] = useState(false);
    const [editError, setEditError] = useState<string | null>(null);
    const [editSuccess, setEditSuccess] = useState<string | null>(null);

    const [startingDestroy, setStartingDestroy] = useState(false);

    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

    // Load plan from Firestore
    useEffect(() => {
        if (!terraformId) {
            setPlanError("Missing terraformId in URL.");
            setPlanLoading(false);
            return;
        }

        let cancelled = false;

        (async () => {
            try {
                const loaded = await loadTerraformPlan(terraformId);
                if (cancelled) return;
                if (!loaded) {
                    setPlanError(
                        "Could not find Terraform plan. Try generating it again."
                    );
                } else {
                    setPlan(loaded);
                    setEditedCode(loaded.terraformCode || "");
                }
            } catch (err: any) {
                if (!cancelled) {
                    setPlanError(
                        err.message || "Failed to load Terraform plan from Firestore."
                    );
                }
            } finally {
                if (!cancelled) setPlanLoading(false);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [terraformId]);

    // Start apply
    const handleStartDeployment = async () => {
        if (!terraformId) return;
        setOperation("apply");
        setStartingDeployment(true);
        setDeploymentError(null);
        setDeploymentOutput("");
        setDeploymentStatus(null);

        try {
            const res = await fetch(`${API_BASE_URL}/api/deploy`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    user_id: DEMO_USER_ID,
                    terraform_id: terraformId,
                }),
            });

            if (!res.ok) {
                const data = await res.json().catch(() => null);
                const msg =
                    data?.detail ||
                    data?.message ||
                    "Failed to start deployment. Check connection and try again.";
                throw new Error(msg);
            }

            const data = await res.json();
            const depId = data.deployment_id as string;

            setDeploymentId(depId);
            setDeploymentStatus(data.status || "started");
        } catch (err: any) {
            setDeploymentError(
                err.message || "Unexpected error while starting deployment."
            );
        } finally {
            setStartingDeployment(false);
        }
    };

    // Start destroy
    const handleStartDestroy = async () => {
        if (!terraformId) return;
        setOperation("destroy");
        setStartingDestroy(true);
        setDeploymentError(null);
        setDeploymentOutput("");
        setDeploymentStatus(null);

        try {
            const res = await fetch(`${API_BASE_URL}/api/destroy`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    user_id: DEMO_USER_ID,
                    terraform_id: terraformId,
                }),
            });

            if (!res.ok) {
                const data = await res.json().catch(() => null);
                const msg =
                    data?.detail ||
                    data?.message ||
                    "Failed to start destroy. Check connection and try again.";
                throw new Error(msg);
            }

            const data = await res.json();
            const depId = data.deployment_id as string;

            setDeploymentId(depId);
            setDeploymentStatus(data.status || "started");
        } catch (err: any) {
            setDeploymentError(
                err.message || "Unexpected error while starting destroy."
            );
        } finally {
            setStartingDestroy(false);
        }
    };

    // Poll status for both apply and destroy
    useEffect(() => {
        if (!deploymentId) return;

        const poll = async () => {
            try {
                const res = await fetch(
                    `${API_BASE_URL}/api/deployment/${deploymentId}/status`
                );

                if (!res.ok) {
                    const data = await res.json().catch(() => null);
                    const msg =
                        data?.detail ||
                        data?.message ||
                        "Failed to fetch deployment status.";
                    throw new Error(msg);
                }

                const data = (await res.json()) as DeploymentStatusResponse;
                setDeploymentStatus(data.status);
                setDeploymentOutput(data.output || "");

                if (
                    data.status === "success" ||
                    data.status === "failed" ||
                    data.status === "destroyed" ||
                    data.status === "destroy_failed"
                ) {
                    if (pollIntervalRef.current) {
                        clearInterval(pollIntervalRef.current);
                        pollIntervalRef.current = null;
                    }
                }
            } catch (err: any) {
                setDeploymentError(
                    err.message || "Error while polling deployment status."
                );
                if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                }
            }
        };

        poll();

        const interval = setInterval(poll, 4000);
        pollIntervalRef.current = interval;

        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
        };
    }, [deploymentId]);

    const statusBadge = (() => {
        if (!deploymentId) {
            return {
                text:
                    operation === "destroy"
                        ? "Ready to destroy resources"
                        : "Ready to deploy",
                tone: "idle" as const,
            };
        }

        if (operation === "destroy") {
            if (deploymentStatus === "destroyed")
                return { text: "Destroy succeeded", tone: "success" as const };
            if (deploymentStatus === "destroy_failed")
                return { text: "Destroy failed", tone: "error" as const };
            if (deploymentStatus === "started" || deploymentStatus === "running")
                return { text: "Destroy in progress", tone: "running" as const };
            return { text: "Checking destroy status", tone: "running" as const };
        }

        if (deploymentStatus === "success")
            return { text: "Deployment succeeded", tone: "success" as const };
        if (deploymentStatus === "failed")
            return { text: "Deployment failed", tone: "error" as const };
        if (deploymentStatus === "started" || deploymentStatus === "running")
            return { text: "Deployment in progress", tone: "running" as const };
        return { text: "Checking deployment", tone: "running" as const };
    })();

    const statusClasses = (() => {
        switch (statusBadge.tone) {
            case "success":
                return "border-emerald-500/70 bg-emerald-500/10 text-emerald-100";
            case "error":
                return "border-red-500/70 bg-red-500/10 text-red-100";
            case "running":
                return "border-amber-500/70 bg-amber-500/10 text-amber-100";
            default:
                return "border-slate-700 bg-slate-900 text-slate-200";
        }
    })();

    const canDeploy =
        !!plan &&
        !!terraformId &&
        !startingDeployment &&
        !deploymentId &&
        (!plan.validation || plan.validation.valid);

    const canDestroy =
        !!plan && !!terraformId && !startingDestroy && !deploymentId;

    const handleCopyCode = async () => {
        const codeToCopy = isEditingCode ? editedCode : plan?.terraformCode;
        if (!codeToCopy) return;
        try {
            await navigator.clipboard.writeText(codeToCopy);
        } catch {
            // ignore
        }
    };

    const handleSaveEditedCode = async () => {
        if (!plan || !terraformId) return;
        setSavingEdit(true);
        setEditError(null);
        setEditSuccess(null);

        try {
            const res = await fetch(`${API_BASE_URL}/api/update-terraform`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    user_id: DEMO_USER_ID,
                    terraform_id: terraformId,
                    code: editedCode,
                }),
            });

            if (!res.ok) {
                const data = await res.json().catch(() => null);
                const msg =
                    data?.detail ||
                    data?.message ||
                    "Failed to update Terraform code.";
                throw new Error(msg);
            }

            const data = await res.json();
            const newValidation = data.validation || null;

            setPlan((prev) =>
                prev
                    ? {
                        ...prev,
                        terraformCode: editedCode,
                        validation: newValidation,
                        status: newValidation?.valid ? "validated" : "generated",
                    }
                    : prev
            );

            await saveTerraformPlan({
                userId: plan.userId,
                terraformId,
                requirements: plan.requirements,
                terraformCode: editedCode,
                validation: newValidation,
            });

            setIsEditingCode(false);
            setEditSuccess("Terraform code updated and revalidated.");
        } catch (err: any) {
            setEditError(err.message || "Error while saving edited code.");
        } finally {
            setSavingEdit(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-50">
            {/* Top bar */}
            <header className="border-b border-slate-800">
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
                        <span className="text-slate-500">Step 3 of 4</span>
                        <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 animate-pulse" />
                            <span>
                                {operation === "destroy"
                                    ? "Destroy resources from this plan"
                                    : "Apply Terraform into your AWS account"}
                            </span>
                        </span>
                    </div>
                </div>
            </header>

            {/* Main */}
            <main className="max-w-7xl mx-auto px-6 py-10 lg:py-14">
                <div className="grid lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] gap-10 items-start">
                    {/* Left - summary and controls */}
                    <section className="space-y-6">
                        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs text-indigo-200">
                            <span>Review plan, edit, and manage lifecycle</span>
                        </div>

                        <div className="space-y-3">
                            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
                                Review or fine tune your Terraform before EZBuilt applies or
                                destroys it
                            </h2>
                            <p className="text-sm md:text-base text-slate-300 max-w-xl">
                                You can tweak the generated code if you want full control.
                                EZBuilt will revalidate the edited Terraform before apply or
                                destroy, using the same state and role.
                            </p>
                        </div>

                        {/* Plan state */}
                        {planLoading && (
                            <p className="text-xs text-slate-400">
                                Loading Terraform plan from Firestore.
                            </p>
                        )}

                        {planError && (
                            <div className="rounded-2xl border border-red-500/70 bg-red-500/10 px-4 py-3 text-xs text-red-100">
                                {planError}
                            </div>
                        )}

                        {plan && (
                            <div className="space-y-4">
                                {/* Plan meta */}
                                <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5 space-y-3">
                                    <div className="flex items-center justify-between text-xs">
                                        <p className="font-medium text-slate-200">
                                            Plan id:{" "}
                                            <span className="font-mono text-slate-100">
                                                {terraformId}
                                            </span>
                                        </p>
                                        {plan.status && (
                                            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-[11px] text-slate-300">
                                                Status: {plan.status}
                                            </span>
                                        )}
                                    </div>

                                    {plan.validation && (
                                        <div
                                            className={`rounded-2xl border px-4 py-3 text-xs ${plan.validation.valid
                                                ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-100"
                                                : "border-amber-500/60 bg-amber-500/10 text-amber-100"
                                                }`}
                                        >
                                            {plan.validation.valid ? (
                                                <p>Terraform validate succeeded for this plan.</p>
                                            ) : (
                                                <>
                                                    <p className="font-medium mb-1">
                                                        Terraform validate reported errors.
                                                    </p>
                                                    <pre className="whitespace-pre-wrap break-words text-[11px]">
                                                        {plan.validation.errors ||
                                                            "Validator returned no error message."}
                                                    </pre>
                                                </>
                                            )}
                                        </div>
                                    )}

                                    <div className="space-y-2">
                                        <p className="text-xs font-medium text-slate-200">
                                            Requirements summary
                                        </p>
                                        <p className="text-xs text-slate-300 whitespace-pre-line">
                                            {plan.requirements}
                                        </p>
                                    </div>

                                    <div className="space-y-2">
                                        <div className="flex items-center justify-between text-xs">
                                            <p className="font-medium text-slate-200">
                                                Terraform for this plan
                                            </p>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        setIsEditingCode((prev) => !prev);
                                                        setEditError(null);
                                                        setEditSuccess(null);
                                                    }}
                                                    className="inline-flex items-center justify-center rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-[11px] text-slate-200 hover:border-indigo-400"
                                                >
                                                    {isEditingCode ? "Cancel edit" : "Edit Terraform"}
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={handleCopyCode}
                                                    className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-[11px] text-slate-200 hover:border-indigo-400"
                                                >
                                                    Copy
                                                </button>
                                            </div>
                                        </div>

                                        <div className="h-60 rounded-2xl border border-slate-800 bg-slate-950/80 overflow-hidden">
                                            {isEditingCode ? (
                                                <textarea
                                                    value={editedCode}
                                                    onChange={(e) => setEditedCode(e.target.value)}
                                                    className="h-full w-full resize-none bg-transparent px-4 py-3 text-[11px] leading-relaxed font-mono text-slate-100 focus:outline-none"
                                                />
                                            ) : (
                                                <pre className="h-full w-full overflow-auto px-4 py-3 text-[11px] leading-relaxed font-mono text-slate-100">
                                                    {plan.terraformCode}
                                                </pre>
                                            )}
                                        </div>

                                        {isEditingCode && (
                                            <div className="flex flex-wrap items-center gap-3 pt-2 text-xs">
                                                <button
                                                    type="button"
                                                    onClick={handleSaveEditedCode}
                                                    disabled={savingEdit}
                                                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-2 text-xs font-semibold text-white shadow hover:bg-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed"
                                                >
                                                    {savingEdit ? (
                                                        <>
                                                            <span className="h-3 w-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                                                            <span>Saving changes</span>
                                                        </>
                                                    ) : (
                                                        <span>Save and revalidate</span>
                                                    )}
                                                </button>
                                                {editError && (
                                                    <span className="text-red-200 text-[11px]">
                                                        {editError}
                                                    </span>
                                                )}
                                                {editSuccess && (
                                                    <span className="text-emerald-200 text-[11px]">
                                                        {editSuccess}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Apply and destroy controls */}
                                <div className="space-y-3">
                                    {plan.validation && !plan.validation.valid && (
                                        <p className="text-xs text-amber-200">
                                            Validation failed. You can still attempt to deploy or
                                            destroy, but Terraform will probably fail. Recommended to
                                            rework the code or go back and adjust your requirements.
                                        </p>
                                    )}

                                    {deploymentError && (
                                        <div className="rounded-2xl border border-red-500/70 bg-red-500/10 px-4 py-3 text-xs text-red-100">
                                            {deploymentError}
                                        </div>
                                    )}

                                    <div className="flex flex-wrap items-center gap-3">
                                        <button
                                            type="button"
                                            onClick={handleStartDeployment}
                                            disabled={!canDeploy}
                                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 shadow-lg hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {startingDeployment ? (
                                                <>
                                                    <span className="h-3 w-3 rounded-full border-2 border-slate-900/40 border-t-slate-900 animate-spin" />
                                                    <span>Starting deployment</span>
                                                </>
                                            ) : (
                                                <span>Deploy to AWS</span>
                                            )}
                                        </button>

                                        <button
                                            type="button"
                                            onClick={handleStartDestroy}
                                            disabled={!canDestroy}
                                            className="inline-flex items-center justify-center gap-2 rounded-xl bg-red-500 px-5 py-2.5 text-sm font-semibold text-slate-50 shadow-lg hover:bg-red-400 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {startingDestroy ? (
                                                <>
                                                    <span className="h-3 w-3 rounded-full border-2 border-slate-100/40 border-t-slate-100 animate-spin" />
                                                    <span>Starting destroy</span>
                                                </>
                                            ) : (
                                                <span>Destroy resources</span>
                                            )}
                                        </button>

                                        <button
                                            type="button"
                                            onClick={() =>
                                                router.push(
                                                    terraformId
                                                        ? `/generate?terraformId=${encodeURIComponent(
                                                            terraformId
                                                        )}`
                                                        : "/generate"
                                                )
                                            }
                                            className="inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-xs font-medium text-slate-200 hover:border-indigo-400"
                                        >
                                            Back to requirements
                                        </button>

                                        <p className="text-[11px] text-slate-500">
                                            EZBuilt runs Terraform with the same plan id and state so
                                            you can trace every apply and destroy.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </section>

                    {/* Right - logs for apply or destroy */}
                    <section>
                        <div className="relative">
                            <div className="pointer-events-none absolute inset-0 blur-3xl bg-gradient-to-br from-emerald-500/30 via-indigo-500/20 to-sky-500/20 opacity-40" />
                            <div className="relative rounded-3xl border border-slate-800 bg-slate-900/90 backdrop-blur-md shadow-2xl p-6 md:p-7 space-y-5">
                                <div
                                    className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${statusClasses}`}
                                >
                                    <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                    <span>{statusBadge.text}</span>
                                </div>

                                {deploymentId && (
                                    <p className="text-[11px] text-slate-500">
                                        {operation === "destroy" ? "Destroy id: " : "Deployment id: "}
                                        <span className="font-mono">{deploymentId}</span>
                                    </p>
                                )}

                                <div className="space-y-2">
                                    <div className="flex items-center justify-between text-xs">
                                        <p className="font-medium text-slate-200">
                                            {operation === "destroy"
                                                ? "Terraform destroy output"
                                                : "Terraform apply output"}
                                        </p>
                                        {deploymentStatus &&
                                            deploymentStatus !== "success" &&
                                            deploymentStatus !== "failed" &&
                                            deploymentStatus !== "destroyed" &&
                                            deploymentStatus !== "destroy_failed" && (
                                                <span className="text-[11px] text-slate-400">
                                                    Streaming logs every few seconds
                                                </span>
                                            )}
                                    </div>

                                    <div className="h-96 rounded-2xl border border-slate-800 bg-slate-950/80 overflow-hidden">
                                        {deploymentOutput ? (
                                            <pre className="h-full w-full overflow-auto px-4 py-3 text-[11px] leading-relaxed font-mono text-slate-100">
                                                {deploymentOutput}
                                            </pre>
                                        ) : (
                                            <div className="h-full flex flex-col items-center justify-center gap-2 px-6 text-[11px] text-slate-500 text-center">
                                                {!deploymentId && operation === "apply" && (
                                                    <p>
                                                        Click "Deploy to AWS" on the left to start Terraform
                                                        apply and stream the logs here.
                                                    </p>
                                                )}
                                                {!deploymentId && operation === "destroy" && (
                                                    <p>
                                                        Click "Destroy resources" on the left to run
                                                        Terraform destroy and stream the logs here.
                                                    </p>
                                                )}
                                                {deploymentId &&
                                                    !deploymentOutput &&
                                                    (deploymentStatus === "started" ||
                                                        deploymentStatus === "running") && (
                                                        <>
                                                            <span className="h-4 w-4 rounded-full border-2 border-slate-600 border-t-slate-200 animate-spin" />
                                                            <p>Waiting for Terraform output.</p>
                                                        </>
                                                    )}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {operation === "apply" && deploymentStatus === "success" && (
                                    <p className="text-xs text-emerald-200">
                                        Resources created successfully. You can now either move to
                                        the final step or destroy them from this same screen.
                                    </p>
                                )}
                                {operation === "destroy" &&
                                    deploymentStatus === "destroyed" && (
                                        <p className="text-xs text-emerald-200">
                                            Resources destroyed successfully. Your account is clean
                                            for this plan.
                                        </p>
                                    )}
                                {deploymentStatus === "failed" ||
                                    deploymentStatus === "destroy_failed" ? (
                                    <p className="text-xs text-amber-200">
                                        Operation failed. Check the logs for details. You can adjust
                                        the Terraform code or your AWS role and try again.
                                    </p>
                                ) : null}
                            </div>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
}
