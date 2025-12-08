"use client";

import { useAuth } from "@/app/(app)/context/AuthContext";
import { useRouter } from "next/navigation";

export default function LogoutButton() {
    const { logout } = useAuth();
    const router = useRouter();

    const handleLogout = async () => {
        await logout();
        router.push("/auth");
    };

    return (
        <button
            onClick={handleLogout}
            className="text-xs rounded-xl border border-slate-700 px-3 py-1 text-slate-300 hover:bg-slate-800 hover:text-white transition"
        >
            Logout
        </button>
    );
}
