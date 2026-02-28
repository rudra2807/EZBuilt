// app/(app)/layout.tsx
"use client";

import { useAuth } from "@/app/(app)/context/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";
import LogoutButton from "@/app//components/LogoutButton";
import Link from "next/link";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
    const { user, loading } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        if (!loading && !user) {
            router.push("/auth");
        }
    }, [loading, user, router]);

    if (loading || !user) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-50">
                <p className="text-xs text-slate-400">Checking authentication…</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-50">
            <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className="h-9 w-9 rounded-2xl bg-gradient-to-br from-indigo-400 to-fuchsia-500 flex items-center justify-center shadow-lg">
                                <span className="text-xl">🚀</span>
                            </div>
                            <div>
                                <h1 className="text-xl font-semibold tracking-tight">EZBuilt Platform</h1>
                                <p className="text-xs text-slate-400">Infrastructure as a conversation, deployed on your cloud</p>
                            </div>
                        </div>

                        {/* Logout + email here once, applies to all pages */}
                        <div className="flex items-center gap-4 text-xs text-slate-400">
                            <span>{user.email}</span>
                            <LogoutButton />
                        </div>
                    </div>

                    {/* Navigation Menu */}
                    <nav className="flex items-center gap-2">
                        <Link
                            href="/generate"
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${pathname === '/generate'
                                ? 'bg-indigo-500 text-white shadow-lg'
                                : 'text-slate-300 hover:bg-slate-800/50 hover:text-slate-100'
                                }`}
                        >
                            <span className="inline-block mr-1.5">✨</span>
                            Generate
                        </Link>
                        <Link
                            href="/history"
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${pathname === '/history'
                                ? 'bg-indigo-500 text-white shadow-lg'
                                : 'text-slate-300 hover:bg-slate-800/50 hover:text-slate-100'
                                }`}
                        >
                            <span className="inline-block mr-1.5">📋</span>
                            History
                        </Link>
                    </nav>
                </div>
            </header>

            <main>{children}</main>
        </div>
    );
}
