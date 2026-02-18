# Migration from Firebase Auth to AWS Cognito

## Summary

Successfully migrated authentication from Firebase to AWS Cognito with Amazon Login.

## Changes Made

### 1. AuthContext (`frontend/src/app/(app)/context/AuthContext.tsx`)

- Removed Firebase dependencies (`onAuthStateChanged`, `signOut`, `User`)
- Replaced with Cognito token-based authentication using cookies
- User info is now fetched from `/api/auth/me` endpoint
- User type changed from Firebase `User` to custom `CognitoUser` with `email`, `sub`, and `name`

### 2. Auth Page (`frontend/src/app/auth/page.tsx`)

- Removed email/password and Google sign-in forms
- Replaced with single "Sign in with Amazon" button
- Redirects to `/api/auth/login` which initiates Cognito OAuth flow
- Displays error messages from URL params (if OAuth fails)

### 3. Logout Button (`frontend/src/app/components/LogoutButton.tsx`)

- Simplified to redirect to `/api/auth/logout`
- Cognito logout endpoint handles cookie clearing and redirect

### 4. Auth API Routes (already configured)

- `/api/auth/login` - Redirects to Cognito with Amazon IdP
- `/api/auth/callback` - Exchanges code for tokens, stores in HttpOnly cookies
- `/api/auth/logout` - Clears cookies and redirects to Cognito logout
- `/api/auth/me` - Decodes JWT from cookie and returns user info

## Environment Variables Required

```
COGNITO_DOMAIN=https://your-domain.auth.region.amazoncognito.com
COGNITO_CLIENT_ID=your_client_id
COGNITO_CLIENT_SECRET=your_client_secret
COGNITO_REDIRECT_URI=http://localhost:3000/api/auth/callback
COGNITO_LOGOUT_REDIRECT_URI=http://localhost:3000/
```

## Authentication Flow

1. User clicks "Sign in with Amazon" on `/auth` page
2. Redirected to Cognito hosted UI with Amazon as identity provider
3. User authenticates with Amazon account
4. Cognito redirects back to `/api/auth/callback` with authorization code
5. Backend exchanges code for tokens (access_token, id_token, refresh_token)
6. Tokens stored in HttpOnly cookies
7. User redirected to `/connect-aws`
8. AuthContext fetches user info from `/api/auth/me` using id_token cookie

## Security Notes

- Tokens are stored in HttpOnly cookies (not accessible via JavaScript)
- In production, set `secure: true` in cookie options for HTTPS
- Consider implementing JWT signature verification in `/api/auth/me`
- Use Cognito's public keys to verify token authenticity

## Files to Remove (Optional)

- `frontend/src/app/(app)/lib/firebase.ts` - No longer needed
- Firebase environment variables can be removed from `.env.local`
