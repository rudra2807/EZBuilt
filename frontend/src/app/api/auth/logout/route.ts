import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const domain = process.env.COGNITO_DOMAIN!;
  const clientId = process.env.COGNITO_CLIENT_ID!;
  const logoutRedirect = process.env.COGNITO_LOGOUT_REDIRECT_URI!;

  const res = NextResponse.redirect(
    `${domain}/logout?client_id=${encodeURIComponent(clientId)}&logout_uri=${encodeURIComponent(logoutRedirect)}`,
  );

  res.cookies.set("access_token", "", { path: "/", maxAge: 0 });
  res.cookies.set("id_token", "", { path: "/", maxAge: 0 });
  res.cookies.set("refresh_token", "", { path: "/", maxAge: 0 });

  return res;
}
