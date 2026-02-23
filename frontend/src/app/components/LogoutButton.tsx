"use client";

import { useAuth } from "@/app/(app)/context/AuthContext";

export default function LogoutButton() {
    const { logout } = useAuth();

    return (
        <button
            onClick={logout}
            className="text-xs rounded-xl border border-slate-700 px-3 py-1 text-slate-300 hover:bg-slate-800 hover:text-white transition"
        >
            Logout
        </button>
    );
}
