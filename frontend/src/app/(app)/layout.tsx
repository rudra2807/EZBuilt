// app/(app)/layout.tsx
"use client";

import { useAuth } from "@/app/(app)/context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import LogoutButton from "@/app//components/LogoutButton";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
    const { user, loading } = useAuth();
    const router = useRouter();

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
            <header className="border-b border-slate-800">
                <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4">
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
            </header>

            <main>{children}</main>
        </div>
    );
}
