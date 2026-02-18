export interface UserData {
  sub: string;
  email: string;
  name?: string;
}

export interface SyncedUser {
  user_id: string;
  email: string;
  created_at: string;
  last_login: string | null;
}

export async function syncUserToBackend(
  userData: UserData,
): Promise<SyncedUser> {
  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  const response = await fetch(`${backendUrl}/api/auth/sync-user`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to sync user");
  }

  return response.json();
}
