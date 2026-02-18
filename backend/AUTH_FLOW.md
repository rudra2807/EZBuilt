# Authentication Flow

## Overview

User authentication using AWS Cognito with automatic database sync.

## Flow

1. **User clicks login** → Frontend redirects to Cognito OAuth
2. **User authenticates** → Cognito redirects back with authorization code
3. **Frontend exchanges code** → Gets access_token, id_token, refresh_token
4. **Frontend syncs user** → Calls backend `/api/auth/sync-user` with Cognito sub & email
5. **Backend stores user** → Creates/updates user in PostgreSQL with Cognito sub as user_id
6. **Frontend stores tokens** → Sets HttpOnly cookies and redirects to app

## Endpoints

### POST `/api/auth/sync-user`

Sync Cognito user to database after login.

**Request:**

```json
{
  "sub": "cognito-user-sub-id",
  "email": "user@example.com",
  "name": "User Name"
}
```

**Response:**

```json
{
  "user_id": "cognito-user-sub-id",
  "email": "user@example.com",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T00:00:00Z"
}
```

### GET `/api/auth/user/{user_id}`

Get user information by user_id (Cognito sub).

**Response:**

```json
{
  "user_id": "cognito-user-sub-id",
  "email": "user@example.com",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T00:00:00Z"
}
```

## Frontend Integration

The auth callback automatically syncs users:

```typescript
// frontend/src/app/api/auth/callback/route.ts
// After token exchange, decodes id_token and calls:
await fetch(`${backendUrl}/api/auth/sync-user`, {
  method: "POST",
  body: JSON.stringify({
    sub: payload.sub,
    email: payload.email,
    name: payload.name,
  }),
});
```

## Database Schema

```sql
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,  -- Cognito sub
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);
```

## Key Points

- `user_id` = Cognito `sub` attribute (unique identifier)
- User is created on first login, updated on subsequent logins
- `last_login` is updated every time user authenticates
- Sync happens automatically in the background
- If sync fails, user can still access the app (logged to console)
