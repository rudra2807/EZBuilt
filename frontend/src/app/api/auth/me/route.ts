import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const idToken = req.cookies.get("id_token")?.value;
  if (!idToken) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  try {
    // Decode the JWT (id_token) to get user info
    // In production, you should verify the signature with Cognito's public keys
    const parts = idToken.split(".");
    if (parts.length !== 3) {
      return NextResponse.json({ error: "Invalid token" }, { status: 401 });
    }

    const payload = JSON.parse(
      Buffer.from(parts[1], "base64").toString("utf-8"),
    );

    return NextResponse.json({
      user: {
        sub: payload.sub,
        email: payload.email,
        name: payload.name || payload.email,
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to decode token" },
      { status: 401 },
    );
  }
}
