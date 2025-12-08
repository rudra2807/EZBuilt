"use client";

import React, { useState, useEffect } from "react";
import { saveAwsConnection, getAwsConnectionForUser } from "@/app/(app)/lib/saveConnection";
import { useRouter } from "next/navigation";
import { useAuth } from "@/app/(app)/context/AuthContext";

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type WizardPhase = "idle" | "linkRequested" | "waitingStack" | "connected";

export default function ConnectAwsPage() {
    const [phase, setPhase] = useState<WizardPhase>("idle");
    const [loading, setLoading] = useState(false);

    const [externalId, setExternalId] = useState<string | null>(null);
    const [cfnLink, setCfnLink] = useState<string | null>(null);
    const [roleArn, setRoleArn] = useState("");

    const [generateError, setGenerateError] = useState<string | null>(null);
    const [connectError, setConnectError] = useState<string | null>(null);
    const [successMsg, setSuccessMsg] = useState<string | null>(null);

    const [checkingExistingConnection, setCheckingExistingConnection] =
        useState(true);

    const hasGeneratedLink = !!externalId && !!cfnLink;

    const router = useRouter();
    const { user, loading: authLoading } = useAuth();
    const userId = user?.uid || null;

    // 1 - Auth gate and existing connection check
    useEffect(() => {
        if (authLoading) return;

        if (!user) {
            router.push("/auth");
            return;
        }

        let cancelled = false;

        (async () => {
            try {
                const existing = await getAwsConnectionForUser(user.uid);
                if (cancelled) return;

                if (existing) {
                    // User already connected - skip this screen
                    router.push("/generate");
                } else {
                    setCheckingExistingConnection(false);
                }
            } catch (err) {
                // If check fails, still allow user to try the wizard
                setCheckingExistingConnection(false);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [authLoading, user, router]);

    const handleGenerateLink = async () => {
        if (!userId) {
            setGenerateError("You must be signed in to connect an AWS account.");
            return;
        }

        setLoading(true);
        setGenerateError(null);
        setConnectError(null);
        setSuccessMsg(null);

        try {
            const res = await fetch(`${API_BASE_URL}/api/generate-cfn-link`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId }),
            });

            if (!res.ok) {
                const txt = await res.text();
                throw new Error(txt || "Failed to generate CloudFormation link");
            }

            const data = await res.json();
            setExternalId(data.external_id);
            setCfnLink(data.cfn_link);
            setPhase("linkRequested");
        } catch (err: any) {
            setGenerateError(err.message || "Something went wrong");
            setPhase("idle");
        } finally {
            setLoading(false);
        }
    };

    const handleOpenCfnConsole = () => {
        if (!cfnLink) return;
        window.open(cfnLink, "_blank", "noopener,noreferrer");
        setPhase("waitingStack");
    };

    const handleConnectAccount = async () => {
        if (!externalId || !roleArn || !userId) return;

        setLoading(true);
        setConnectError(null);
        setSuccessMsg(null);

        try {
            const url = new URL(`${API_BASE_URL}/api/connect-account-manual`);
            url.searchParams.set("user_id", userId);
            url.searchParams.set("role_arn", roleArn);
            url.searchParams.set("external_id", externalId);

            const res = await fetch(url.toString(), { method: "POST" });

            if (!res.ok) {
                const data = await res.json().catch(() => null);
                const msg =
                    data?.detail ||
                    data?.message ||
                    "Failed to connect AWS account. Check the Role ARN.";
                throw new Error(msg);
            }

            const data = await res.json();

            await saveAwsConnection({
                userId,
                externalId,
                roleArn: data.role_arn ?? roleArn,
            });

            setSuccessMsg(data.message || "AWS account connected successfully.");
            setPhase("connected");
            router.push("/generate");
        } catch (err: any) {
            setConnectError(err.message || "Something went wrong");
        } finally {
            setLoading(false);
        }
    };

    const statusLabel = (() => {
        switch (phase) {
            case "idle":
                return "Waiting to start";
            case "linkRequested":
                return "External ID generated";
            case "waitingStack":
                return "Stack running in your AWS account";
            case "connected":
                return "Account connected";
            default:
                return "";
        }
    })();

    const statusTone = (() => {
        switch (phase) {
            case "connected":
                return "bg-emerald-50 text-emerald-700 border-emerald-200";
            case "waitingStack":
            case "linkRequested":
                return "bg-indigo-50 text-indigo-700 border-indigo-200";
            default:
                return "bg-slate-50 text-slate-600 border-slate-200";
        }
    })();

    const stepHighlight = (index: number) => {
        if (phase === "idle") return index === 1;
        if (phase === "linkRequested") return index <= 2;
        if (phase === "waitingStack") return index <= 3;
        return true;
    };

    // While we are checking auth and existing connection, show a simple loader
    if (authLoading || checkingExistingConnection) {
        return (
            <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
                <p className="text-xs text-slate-400">
                    Preparing your EZBuilt workspace.
                </p>
            </div>
        );
    }

    // From here down, same UI as you already had
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

                    <div className="hidden md:flex items-center gap-2 text-xs text-slate-400">
                        <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            <span>Secure cross account access</span>
                        </span>
                        <span className="text-slate-500">AWS only for now</span>
                    </div>
                </div>
            </header> */}

            {/* Main content */}
            <main className="max-w-7xl mx-auto px-6 py-10 lg:py-14">
                <div className="grid lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] gap-10 items-start">
                    {/* Left side: marketing and context */}
                    <section className="space-y-6">
                        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs text-indigo-200">
                            <span className="h-1.5 w-1.5 rounded-full bg-indigo-300 animate-ping" />
                            <span>Step 1 of 4 • Connect your cloud</span>
                        </div>

                        <div className="space-y-3">
                            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
                                Bring your AWS account under EZBuilt control in a few clicks
                            </h2>
                            <p className="text-sm md:text-base text-slate-300 max-w-xl">
                                We create a least privilege role in your account with an
                                External ID, then EZBuilt assumes that role only when it needs
                                to provision or update your infrastructure.
                            </p>
                        </div>

                        <div className="grid sm:grid-cols-3 gap-4 text-sm">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-3">
                                <p className="text-xs text-slate-400">Trust boundary</p>
                                <p className="mt-1 text-lg font-semibold text-slate-50">
                                    Your AWS account
                                </p>
                                <p className="mt-1 text-xs text-slate-400">
                                    Stack runs inside your account. No long lived keys stored.
                                </p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-3">
                                <p className="text-xs text-slate-400">Access model</p>
                                <p className="mt-1 text-lg font-semibold text-slate-50">
                                    Role plus External ID
                                </p>
                                <p className="mt-1 text-xs text-slate-400">
                                    Standard cross account trust with a random External ID bound
                                    to your user.
                                </p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-3">
                                <p className="text-xs text-slate-400">Expected duration</p>
                                <p className="mt-1 text-lg font-semibold text-slate-50">
                                    2 to 3 minutes
                                </p>
                                <p className="mt-1 text-xs text-slate-400">
                                    Most of that time is CloudFormation deploying on your side.
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* Right side: wizard card */}
                    <section>
                        <div className="relative">
                            {/* glow */}
                            <div className="pointer-events-none absolute inset-0 blur-3xl bg-gradient-to-br from-indigo-500/40 via-fuchsia-500/20 to-sky-500/20 opacity-40" />
                            <div className="relative rounded-3xl border border-slate-800 bg-slate-900/90 backdrop-blur-md shadow-2xl p-6 md:p-7">
                                {/* Status bar */}
                                <div
                                    className={`mb-5 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${statusTone}`}
                                >
                                    <span className="h-1.5 w-1.5 rounded-full bg-current" />
                                    <span>{statusLabel}</span>
                                </div>

                                <div className="flex gap-5">
                                    {/* mini vertical steps */}
                                    <ol className="flex flex-col items-start gap-6 text-xs mt-1">
                                        {[
                                            "Generate External ID",
                                            "Launch CloudFormation",
                                            "Wait for stack to complete",
                                            "Connect role to EZBuilt",
                                        ].map((label, idx) => {
                                            const index = idx + 1;
                                            const active = stepHighlight(index);
                                            return (
                                                <li key={label} className="flex items-start gap-3">
                                                    <div className="flex flex-col items-center">
                                                        <div
                                                            className={`h-6 w-6 rounded-full flex items-center justify-center text-[10px] font-semibold ${active
                                                                ? "bg-indigo-500 text-white shadow-md"
                                                                : "bg-slate-800 text-slate-500"
                                                                }`}
                                                        >
                                                            {index}
                                                        </div>
                                                        {index < 4 && (
                                                            <div className="flex-1 w-px bg-slate-800 mt-1 mb-1" />
                                                        )}
                                                    </div>
                                                    <span
                                                        className={`mt-0.5 ${active ? "text-slate-100" : "text-slate-500"
                                                            }`}
                                                    >
                                                        {label}
                                                    </span>
                                                </li>
                                            );
                                        })}
                                    </ol>

                                    {/* main body */}
                                    <div className="flex-1 space-y-4">
                                        <h3 className="text-xl font-semibold text-slate-50">
                                            Connect your AWS account
                                        </h3>

                                        {!hasGeneratedLink && (
                                            <>
                                                <p className="text-xs text-slate-300">
                                                    EZBuilt will generate a one time CloudFormation link
                                                    bound to your user. The stack sets up a deployment
                                                    role in your account.
                                                </p>

                                                {generateError && (
                                                    <div className="rounded-xl border border-red-500/60 bg-red-500/10 px-3 py-2 text-xs text-red-100">
                                                        {generateError}
                                                    </div>
                                                )}

                                                <button
                                                    type="button"
                                                    onClick={handleGenerateLink}
                                                    disabled={loading}
                                                    className="mt-1 inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-fuchsia-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg hover:from-indigo-400 hover:to-fuchsia-400 disabled:opacity-60 disabled:cursor-not-allowed transition"
                                                >
                                                    {loading ? (
                                                        <>
                                                            <span className="h-3 w-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                                                            <span>Generating link</span>
                                                        </>
                                                    ) : (
                                                        <span>Generate CloudFormation link</span>
                                                    )}
                                                </button>

                                                <p className="text-[11px] text-slate-500 pt-1">
                                                    You only do this once per AWS account. Later
                                                    deployments reuse the same role.
                                                </p>
                                            </>
                                        )}

                                        {hasGeneratedLink && (
                                            <>
                                                {/* External ID box */}
                                                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
                                                    <p className="text-[11px] text-slate-400 mb-1">
                                                        External ID for this connection
                                                    </p>
                                                    <div className="flex items-center gap-3">
                                                        <p className="font-mono text-xs text-slate-50 break-all">
                                                            {externalId}
                                                        </p>
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                externalId &&
                                                                navigator.clipboard.writeText(externalId)
                                                            }
                                                            className="text-[11px] rounded-full border border-slate-700 px-2 py-1 text-slate-300 hover:bg-slate-800"
                                                        >
                                                            Copy
                                                        </button>
                                                    </div>
                                                    <p className="mt-1 text-[11px] text-slate-500">
                                                        Only this External ID is allowed to assume the
                                                        deployment role.
                                                    </p>
                                                </div>

                                                {/* Instructions */}
                                                <div className="space-y-3 text-xs text-slate-300">
                                                    <p className="font-medium text-slate-200">
                                                        Follow these steps in AWS
                                                    </p>
                                                    <ol className="list-decimal list-inside space-y-1">
                                                        <li>Open the CloudFormation console with the link.</li>
                                                        <li>Review the template and create the stack.</li>
                                                        <li>
                                                            Wait for the stack to reach the CREATE_COMPLETE
                                                            state.
                                                        </li>
                                                        <li>
                                                            In the Outputs tab, copy the Role ARN value and
                                                            paste it below.
                                                        </li>
                                                    </ol>

                                                    <button
                                                        type="button"
                                                        onClick={handleOpenCfnConsole}
                                                        className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/60 bg-emerald-500/10 px-4 py-2 text-xs font-semibold text-emerald-100 hover:bg-emerald-500/20"
                                                    >
                                                        Open CloudFormation console
                                                    </button>
                                                </div>

                                                {/* Role ARN input */}
                                                <div className="space-y-2 pt-2">
                                                    <label
                                                        htmlFor="roleArn"
                                                        className="block text-xs font-medium text-slate-200"
                                                    >
                                                        Role ARN from CloudFormation Outputs
                                                    </label>
                                                    <input
                                                        id="roleArn"
                                                        type="text"
                                                        value={roleArn}
                                                        onChange={(e) => setRoleArn(e.target.value)}
                                                        placeholder="arn:aws:iam::123456789012:role/EZBuiltDeploymentRole..."
                                                        className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                                    />

                                                    {connectError && (
                                                        <div className="rounded-xl border border-red-500/70 bg-red-500/10 px-3 py-2 text-xs text-red-100">
                                                            {connectError}
                                                        </div>
                                                    )}
                                                    {successMsg && (
                                                        <div className="rounded-xl border border-emerald-500/70 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-100">
                                                            {successMsg}
                                                        </div>
                                                    )}

                                                    <button
                                                        type="button"
                                                        onClick={handleConnectAccount}
                                                        disabled={!roleArn || loading}
                                                        className="mt-1 inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-2 text-xs font-semibold text-white shadow hover:bg-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed"
                                                    >
                                                        {loading ? (
                                                            <>
                                                                <span className="h-3 w-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                                                                <span>Connecting</span>
                                                            </>
                                                        ) : (
                                                            <span>Connect account</span>
                                                        )}
                                                    </button>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
}
