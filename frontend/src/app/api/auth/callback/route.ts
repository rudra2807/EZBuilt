import { NextRequest, NextResponse } from "next/server";

function basicAuth(clientId: string, clientSecret: string) {
  const raw = `${clientId}:${clientSecret}`;
  return Buffer.from(raw).toString("base64");
}

export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get("code");
  if (!code)
    return NextResponse.redirect(new URL("/auth?error=missing_code", req.url));

  const domain = process.env.COGNITO_DOMAIN!;
  const clientId = process.env.COGNITO_CLIENT_ID!;
  const clientSecret = process.env.COGNITO_CLIENT_SECRET!;
  const redirectUri = process.env.COGNITO_REDIRECT_URI!;

  const tokenUrl = `${domain}/oauth2/token`;

  const body = new URLSearchParams();
  body.set("grant_type", "authorization_code");
  body.set("client_id", clientId);
  body.set("code", code);
  body.set("redirect_uri", redirectUri);

  const resp = await fetch(tokenUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Basic ${basicAuth(clientId, clientSecret)}`,
    },
    body,
  });

  if (!resp.ok) {
    const txt = await resp.text();
    return NextResponse.redirect(
      new URL(
        `/auth?error=token_exchange_failed&detail=${encodeURIComponent(txt)}`,
        req.url,
      ),
    );
  }

  const data = await resp.json();

  // Decode id_token to get user info
  try {
    const idTokenParts = data.id_token.split(".");
    const payload = JSON.parse(
      Buffer.from(idTokenParts[1], "base64").toString("utf-8"),
    );

    // Sync user to backend database
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    await fetch(`${backendUrl}/api/auth/sync-user`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        sub: payload.sub,
        email: payload.email,
        name: payload.name || payload.email,
      }),
    });
  } catch (error) {
    console.error("Failed to sync user to backend:", error);
    // Continue anyway - user can still use the app
  }

  const res = NextResponse.redirect(new URL("/connect-aws", req.url));

  // Store tokens in HttpOnly cookies (server-readable, not JS-readable)
  // Keep it simple for now.
  res.cookies.set("access_token", data.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: false, // set true in production https
    path: "/",
  });
  res.cookies.set("id_token", data.id_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: false,
    path: "/",
  });
  if (data.refresh_token) {
    res.cookies.set("refresh_token", data.refresh_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: false,
      path: "/",
    });
  }

  return res;
}
