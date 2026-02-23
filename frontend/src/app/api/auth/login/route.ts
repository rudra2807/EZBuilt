import { NextResponse } from "next/server";

export async function GET() {
  const domain = process.env.COGNITO_DOMAIN!;
  const clientId = process.env.COGNITO_CLIENT_ID!;
  const redirectUri = process.env.COGNITO_REDIRECT_URI!;

  const url = new URL(`${domain}/oauth2/authorize`);
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", "openid profile");
  url.searchParams.set("redirect_uri", redirectUri);

  console.log("Redirecting to:", url.toString());

  return NextResponse.redirect(url.toString());
}
