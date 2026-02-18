"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/app/(app)/context/AuthContext";

export default function AuthPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { user, loading } = useAuth();
    const [error, setError] = useState<string | null>(null);

    // Redirect if already signed in
    useEffect(() => {
        if (!loading && user) {
            router.replace("/connect-aws");
        }
    }, [loading, user, router]);

    // Check for error in URL params
    useEffect(() => {
        const errorParam = searchParams.get("error");
        const detailParam = searchParams.get("detail");
        if (errorParam) {
            setError(detailParam || errorParam);
        }
    }, [searchParams]);

    const handleAmazonLogin = () => {
        window.location.href = "/api/auth/login";
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

                    {error && (
                        <div className="rounded-xl border border-red-500/70 bg-red-500/10 px-3 py-2 text-[11px] text-red-100">
                            {error}
                        </div>
                    )}

                    <button
                        type="button"
                        onClick={handleAmazonLogin}
                        className="w-full inline-flex items-center justify-center gap-3 rounded-xl bg-gradient-to-r from-orange-500 to-yellow-500 px-4 py-3 text-sm font-semibold text-white shadow-lg hover:from-orange-400 hover:to-yellow-400 transition-all"
                    >
                        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M.045 18.02c.072-.116.187-.124.348-.022 3.636 2.11 7.594 3.166 11.87 3.166 2.852 0 5.668-.533 8.447-1.595l.315-.14c.138-.06.234-.1.293-.13.226-.088.39-.046.525.13.12.174.09.336-.12.48-.256.19-.6.41-1.006.654-1.244.743-2.64 1.316-4.185 1.726-1.544.406-3.045.61-4.502.61-3.16 0-6.123-.636-8.886-1.906l-1.048-.507-.617-.34c-.226-.16-.344-.3-.348-.42zM23.85 15.705c-.267-.37-.55-.556-.848-.556-.096 0-.192.024-.288.073l-.24.12c-2.16 1.064-4.554 1.597-7.184 1.597-2.632 0-5.02-.533-7.16-1.597l-.24-.12c-.096-.05-.192-.074-.288-.074-.3 0-.583.186-.848.556-.13.178-.18.334-.15.465.03.134.14.26.33.38 2.4 1.51 5.064 2.264 7.992 2.264 2.928 0 5.592-.754 7.992-2.264.19-.12.3-.246.33-.38.03-.13-.02-.287-.15-.465z" />
                        </svg>
                        <span>Sign in with Amazon</span>
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
