"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword,
    signInWithPopup,
} from "firebase/auth";
import { getFirebaseAuth, getGoogleProvider } from "@/app/lib/firebase";
import { useAuth } from "@/app/context/AuthContext";

type Mode = "signin" | "signup";

export default function AuthPage() {
    const router = useRouter();
    const { user, loading } = useAuth();

    const [mode, setMode] = useState<Mode>("signin");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    // Redirect if already signed in
    useEffect(() => {
        if (!loading && user) {
            router.replace("/connect-aws");
        }
    }, [loading, user, router]);

    const handleEmailSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!email || !password) {
            setError("Email and password are required.");
            return;
        }

        if (mode === "signup" && password !== confirm) {
            setError("Passwords do not match.");
            return;
        }

        setSubmitting(true);
        const auth = getFirebaseAuth();

        try {
            if (mode === "signup") {
                await createUserWithEmailAndPassword(auth, email, password);
            } else {
                await signInWithEmailAndPassword(auth, email, password);
            }
            router.replace("/connect-aws");
        } catch (err: any) {
            setError(err.message || "Authentication failed.");
        } finally {
            setSubmitting(false);
        }
    };

    const handleGoogleSignIn = async () => {
        setError(null);
        setSubmitting(true);
        const auth = getFirebaseAuth();
        const provider = getGoogleProvider();
        try {
            await signInWithPopup(auth, provider);
            router.replace("/connect-aws");
        } catch (err: any) {
            setError(err.message || "Google sign in failed.");
        } finally {
            setSubmitting(false);
        }
    };

    // Optional: loading state while auth listener initializes
    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
                <p className="text-xs text-slate-400">Checking authentication.</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center px-4">
            <div className="max-w-md w-full relative">
                <div className="pointer-events-none absolute inset-0 blur-3xl bg-gradient-to-br from-indigo-500/40 via-fuchsia-500/20 to-sky-500/20 opacity-40" />
                <div className="relative rounded-3xl border border-slate-800 bg-slate-900/90 backdrop-blur-md shadow-2xl p-8 space-y-6">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="h-9 w-9 rounded-2xl bg-gradient-to-br from-indigo-400 to-fuchsia-500 flex items-center justify-center shadow-lg">
                            <span className="text-xl">🚀</span>
                        </div>
                        <div>
                            <h1 className="text-xl font-semibold tracking-tight">
                                EZBuilt Platform
                            </h1>
                            <p className="text-xs text-slate-400">
                                Sign in to manage your infrastructure
                            </p>
                        </div>
                    </div>

                    {/* Mode toggle */}
                    <div className="inline-flex items-center rounded-full bg-slate-900 border border-slate-700 p-1 text-xs">
                        <button
                            type="button"
                            onClick={() => {
                                setMode("signin");
                                setError(null);
                            }}
                            className={`px-4 py-1 rounded-full ${mode === "signin"
                                ? "bg-slate-800 text-slate-50"
                                : "text-slate-400"
                                }`}
                        >
                            Sign in
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                setMode("signup");
                                setError(null);
                            }}
                            className={`px-4 py-1 rounded-full ${mode === "signup"
                                ? "bg-slate-800 text-slate-50"
                                : "text-slate-400"
                                }`}
                        >
                            Sign up
                        </button>
                    </div>

                    <form className="space-y-4" onSubmit={handleEmailSubmit}>
                        <div className="space-y-1 text-xs">
                            <label
                                htmlFor="email"
                                className="block font-medium text-slate-200"
                            >
                                Email
                            </label>
                            <input
                                id="email"
                                type="email"
                                autoComplete="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                placeholder="you@example.com"
                            />
                        </div>

                        <div className="space-y-1 text-xs">
                            <label
                                htmlFor="password"
                                className="block font-medium text-slate-200"
                            >
                                Password
                            </label>
                            <input
                                id="password"
                                type="password"
                                autoComplete={
                                    mode === "signup" ? "new-password" : "current-password"
                                }
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                placeholder="At least 6 characters"
                            />
                        </div>

                        {mode === "signup" && (
                            <div className="space-y-1 text-xs">
                                <label
                                    htmlFor="confirm"
                                    className="block font-medium text-slate-200"
                                >
                                    Confirm password
                                </label>
                                <input
                                    id="confirm"
                                    type="password"
                                    autoComplete="new-password"
                                    value={confirm}
                                    onChange={(e) => setConfirm(e.target.value)}
                                    className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-50 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                    placeholder="Repeat your password"
                                />
                            </div>
                        )}

                        {error && (
                            <div className="rounded-xl border border-red-500/70 bg-red-500/10 px-3 py-2 text-[11px] text-red-100">
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg hover:bg-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                            {submitting ? (
                                <>
                                    <span className="h-3 w-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                                    <span>
                                        {mode === "signup" ? "Creating account" : "Signing in"}
                                    </span>
                                </>
                            ) : (
                                <span>{mode === "signup" ? "Create account" : "Sign in"}</span>
                            )}
                        </button>
                    </form>

                    <div className="flex items-center gap-2 text-[11px] text-slate-500">
                        <div className="flex-1 h-px bg-slate-800" />
                        <span>or sign in with</span>
                        <div className="flex-1 h-px bg-slate-800" />
                    </div>

                    <button
                        type="button"
                        onClick={handleGoogleSignIn}
                        disabled={submitting}
                        className="w-full inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-4 py-2 text-xs font-medium text-slate-100 hover:border-indigo-400 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                        <span className="text-lg">🟢</span>
                        <span>Continue with Google</span>
                    </button>

                    <p className="text-[11px] text-slate-500 pt-1">
                        By continuing you confirm you understand that EZBuilt will create
                        and destroy resources inside your AWS account using the role you
                        configure.
                    </p>
                </div>
            </div>
        </div>
    );
}
