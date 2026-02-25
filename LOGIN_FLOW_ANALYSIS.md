# Login Flow Analysis - Gaps and Issues

## Current Authentication Flow

### 1. Frontend Login Flow (AWS Cognito)

```
User clicks "Sign in with Amazon"
  ↓
/api/auth/login (frontend route)
  ↓
Redirects to Cognito hosted UI with Amazon IdP
  ↓
User authenticates with Amazon account
  ↓
Cognito redirects to /api/auth/callback with authorization code
  ↓
/api/auth/callback exchanges code for tokens
  ↓
Stores tokens in HttpOnly cookies (id_token, access_token, refresh_token)
  ↓
Syncs user to backend via POST /api/auth/sync-user
  ↓
Redirects to /connect-aws
  ↓
AuthContext fetches user info from /api/auth/me
  ↓
User is authenticated
```

### 2. Backend Authentication Flow

```
Frontend makes API request with JWT token
  ↓
??? NO JWT VALIDATION MIDDLEWARE ???
  ↓
Backend endpoint receives request
  ↓
get_current_user_id() dependency is called
  ↓
❌ RAISES 501 NOT IMPLEMENTED ❌
```

## Critical Gaps Identified

### 🔴 GAP 1: No JWT Validation in Backend

**Location:** `backend/src/apis/routes_deployment.py`

**Issue:**

```python
async def get_current_user_id() -> str:
    """
    Extract user_id from JWT token.

    TODO: Implement JWT token validation and extraction.
    """
    raise HTTPException(
        status_code=501,
        detail="JWT authentication not yet implemented"
    )
```

**Impact:**

- ALL deployment endpoints are non-functional
- `/api/deploy` - Cannot deploy infrastructure
- `/api/destroy` - Cannot destroy infrastructure
- `/api/deployment/{id}/status` - Cannot check deployment status

**Affected Endpoints:**

- `POST /api/deploy` - Depends on `get_current_user_id()`
- `POST /api/destroy` - Depends on `get_current_user_id()`
- `GET /api/deployment/{id}/status` - Depends on `get_current_user_id()`

### 🟡 GAP 2: Frontend Sends Bearer Token, Backend Expects It

**Location:** `frontend/src/app/(app)/deploy/page.tsx`

**Frontend Code:**

```typescript
const token = getJWTToken(); // Gets id_token from cookie
const response = await fetch(`${API_BASE_URL}/api/deploy`, {
  headers: {
    Authorization: `Bearer ${token}`,
  },
});
```

**Backend Code:**

```python
# No middleware to extract Authorization header
# No code to validate Bearer token
# get_current_user_id() just raises 501
```

**Impact:**

- Frontend correctly sends JWT token
- Backend has no code to receive or validate it
- All authenticated API calls fail with 501

### 🟡 GAP 3: Token Signature Verification Not Implemented

**Location:** `frontend/src/app/api/auth/me/route.ts`

**Current Code:**

```typescript
// Decode the JWT (id_token) to get user info
// In production, you should verify the signature with Cognito's public keys
const parts = idToken.split(".");
const payload = JSON.parse(Buffer.from(parts[1], "base64").toString("utf-8"));
```

**Issue:**

- Token is decoded but NOT verified
- Anyone can forge a token and it will be accepted
- Security vulnerability in production

**Impact:**

- Authentication bypass vulnerability
- Tokens are trusted without cryptographic verification

### 🟢 GAP 4: Inconsistent Token Usage

**Frontend Token Sources:**

1. `getJWTToken()` - Reads `id_token` from cookies (client-side)
2. `/api/auth/me` - Reads `id_token` from cookies (server-side)

**Issue:**

- Frontend reads cookies client-side for API calls
- This works but is less secure than server-side only
- HttpOnly cookies should only be read server-side

**Better Approach:**

- Use Next.js middleware to add token to requests server-side
- Or create API route wrapper that adds auth headers

### 🟢 GAP 5: No Token Refresh Logic

**Current State:**

- Tokens are stored in cookies
- `refresh_token` is stored but never used
- When `id_token` expires, user must re-login

**Missing:**

- Token expiration detection
- Automatic token refresh using `refresh_token`
- Graceful re-authentication flow

## Recommended Implementation Plan

### Priority 1: Implement JWT Validation Middleware (CRITICAL)

**File:** `backend/src/middleware/auth.py` (new file)

```python
from fastapi import HTTPException, Header
from jose import jwt, JWTError
import httpx
from functools import lru_cache

# Cognito public keys endpoint
COGNITO_REGION = "us-east-1"
COGNITO_USER_POOL_ID = "us-east-1_XXXXXXX"
JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"

@lru_cache()
async def get_cognito_public_keys():
    """Fetch and cache Cognito public keys"""
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        return response.json()

async def get_current_user_id(authorization: str = Header(None)) -> str:
    """
    Extract and validate user_id from JWT token.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        str: User ID (Cognito sub)

    Raises:
        HTTPException 401: Missing or invalid token
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    try:
        # Get public keys
        jwks = await get_cognito_public_keys()

        # Decode and verify token
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=os.getenv("COGNITO_CLIENT_ID"),
            issuer=f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
        )

        # Extract user_id (sub claim)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing sub claim")

        return user_id

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
```

**Update:** `backend/src/apis/routes_deployment.py`

```python
from src.middleware.auth import get_current_user_id
# Remove the placeholder function
```

**Dependencies to Add:**

```txt
python-jose[cryptography]
httpx
```

### Priority 2: Implement Token Signature Verification in Frontend

**File:** `frontend/src/app/api/auth/me/route.ts`

```typescript
import { NextRequest, NextResponse } from "next/server";
import * as jose from "jose";

const COGNITO_REGION = process.env.COGNITO_REGION || "us-east-1";
const COGNITO_USER_POOL_ID = process.env.COGNITO_USER_POOL_ID!;
const JWKS_URL = `https://cognito-idp.${COGNITO_REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}/.well-known/jwks.json`;

export async function GET(req: NextRequest) {
  const idToken = req.cookies.get("id_token")?.value;
  if (!idToken) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  try {
    // Fetch Cognito public keys
    const JWKS = jose.createRemoteJWKSet(new URL(JWKS_URL));

    // Verify token signature
    const { payload } = await jose.jwtVerify(idToken, JWKS, {
      issuer: `https://cognito-idp.${COGNITO_REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}`,
      audience: process.env.COGNITO_CLIENT_ID,
    });

    return NextResponse.json({
      user: {
        sub: payload.sub,
        email: payload.email,
        name: payload.name || payload.email,
      },
    });
  } catch (error) {
    console.error("Token verification failed:", error);
    return NextResponse.json(
      { error: "Invalid or expired token" },
      { status: 401 },
    );
  }
}
```

**Dependencies to Add:**

```json
{
  "dependencies": {
    "jose": "^5.0.0"
  }
}
```

### Priority 3: Implement Token Refresh Logic

**File:** `frontend/src/app/api/auth/refresh/route.ts` (new file)

```typescript
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get("refresh_token")?.value;

  if (!refreshToken) {
    return NextResponse.json({ error: "No refresh token" }, { status: 401 });
  }

  const domain = process.env.COGNITO_DOMAIN!;
  const clientId = process.env.COGNITO_CLIENT_ID!;
  const clientSecret = process.env.COGNITO_CLIENT_SECRET!;

  const body = new URLSearchParams();
  body.set("grant_type", "refresh_token");
  body.set("client_id", clientId);
  body.set("refresh_token", refreshToken);

  const basicAuth = Buffer.from(`${clientId}:${clientSecret}`).toString(
    "base64",
  );

  const response = await fetch(`${domain}/oauth2/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Basic ${basicAuth}`,
    },
    body,
  });

  if (!response.ok) {
    return NextResponse.json(
      { error: "Token refresh failed" },
      { status: 401 },
    );
  }

  const data = await response.json();

  const res = NextResponse.json({ success: true });

  // Update tokens
  res.cookies.set("access_token", data.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });

  res.cookies.set("id_token", data.id_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });

  return res;
}
```

### Priority 4: Add Next.js Middleware for Auth

**File:** `frontend/middleware.ts` (new file)

```typescript
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const idToken = request.cookies.get("id_token");
  const path = request.nextUrl.pathname;

  // Public paths that don't require authentication
  const publicPaths = [
    "/auth",
    "/api/auth/login",
    "/api/auth/callback",
    "/api/auth/logout",
  ];

  if (publicPaths.some((p) => path.startsWith(p))) {
    return NextResponse.next();
  }

  // Redirect to auth if no token
  if (!idToken) {
    return NextResponse.redirect(new URL("/auth", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

## Summary of Gaps

| Gap                             | Severity    | Component | Status                 | Impact                        |
| ------------------------------- | ----------- | --------- | ---------------------- | ----------------------------- |
| No JWT validation in backend    | 🔴 CRITICAL | Backend   | Not Implemented        | All deployment endpoints fail |
| No token signature verification | 🟡 HIGH     | Frontend  | Not Implemented        | Security vulnerability        |
| No token refresh logic          | 🟢 MEDIUM   | Frontend  | Not Implemented        | Poor UX on token expiry       |
| Client-side cookie reading      | 🟢 LOW      | Frontend  | Working but suboptimal | Less secure                   |
| No auth middleware              | 🟢 LOW      | Frontend  | Not Implemented        | No route protection           |

## Testing Checklist

After implementing fixes:

- [ ] Test login flow end-to-end
- [ ] Test JWT validation with valid token
- [ ] Test JWT validation with invalid token
- [ ] Test JWT validation with expired token
- [ ] Test JWT validation with forged token
- [ ] Test deployment with authenticated user
- [ ] Test deployment without authentication
- [ ] Test token refresh flow
- [ ] Test route protection middleware
- [ ] Test logout and cookie clearing
