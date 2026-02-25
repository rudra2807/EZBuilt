# Testing Guide - Database Integration

## Prerequisites

1. **Update DATABASE_URL** in `backend/.env.local`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:your-password@your-aurora-endpoint.region.rds.amazonaws.com:5432/ezbuilt
```

2. **Install dependencies**:

```bash
cd backend
pip install -r requirements.txt
```

3. **Run migrations**:

```bash
# Generate initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

---

## Step 1: Test Database Connection

```bash
cd backend
python scripts/view_database.py
```

**Expected output:**

```
🔌 Connecting to your-aurora-endpoint...
✅ Connected successfully!

📊 Tables:
   - users
   - aws_integrations

👥 Users (0):
   No users yet

🔗 AWS Integrations (0):
   No integrations yet

✅ Done!
```

---

## Step 2: Test Backend API

### Start Backend Server

```bash
cd backend
python main.py
```

**Expected output:**

```
🚀 Starting EZBuilt API Server...
📍 Server running at: http://localhost:8000
📖 API docs at: http://localhost:8000/docs
```

### Test Endpoints

#### A. Health Check

```bash
curl http://localhost:8000/
```

**Expected:**

```json
{
  "status": "running",
  "service": "EZBuilt API",
  "version": "1.0.0"
}
```

#### B. Sync User (Manual Test)

```bash
curl -X POST http://localhost:8000/api/auth/sync-user \
  -H "Content-Type: application/json" \
  -d '{
    "sub": "test-user-123",
    "email": "test@example.com",
    "name": "Test User"
  }'
```

**Expected:**

```json
{
  "user_id": "test-user-123",
  "email": "test@example.com",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T00:00:00Z"
}
```

#### C. Get User

```bash
curl http://localhost:8000/api/auth/user/test-user-123
```

**Expected:**

```json
{
  "user_id": "test-user-123",
  "email": "test@example.com",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T00:00:00Z"
}
```

#### D. View in Database

```bash
python scripts/view_database.py
```

**Expected:**

```
👥 Users (1):
   - test@example.com (ID: test-use...)
     Created: 2024-01-01 00:00:00+00:00
     Last login: 2024-01-01 00:00:00+00:00
```

---

## Step 3: Test Full Login Flow

### Start Both Servers

**Terminal 1 - Backend:**

```bash
cd backend
python main.py
```

**Terminal 2 - Frontend:**

```bash
cd frontend
npm run dev
```

### Test Login

1. **Open browser:** http://localhost:3000
2. **Click login** → Redirects to Cognito
3. **Login with Amazon** → Authenticate
4. **Callback happens** → Should redirect to `/connect-aws`

### Verify User Created

**Check backend logs** (Terminal 1):

```
POST /api/auth/sync-user
Status: 200
```

**Check database:**

```bash
cd backend
python scripts/view_database.py
```

**Expected:**

```
👥 Users (1):
   - your-amazon-email@example.com (ID: cognito-sub-id...)
     Created: 2024-01-01 00:00:00+00:00
     Last login: 2024-01-01 00:00:00+00:00
```

---

## Step 4: Test API Documentation

Visit: http://localhost:8000/docs

You should see:

- **Authentication** section with:
  - `POST /api/auth/sync-user`
  - `GET /api/auth/user/{user_id}`
- **Connections** section with AWS endpoints

Try the interactive API:

1. Click `POST /api/auth/sync-user`
2. Click "Try it out"
3. Enter test data
4. Click "Execute"
5. See response

---

## Step 5: Test AWS Integration Flow

### Generate CFN Link

```bash
curl -X POST http://localhost:8000/api/generate-cfn-link \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123"
  }'
```

**Expected:**

```json
{
  "cfn_link": "https://console.aws.amazon.com/cloudformation/...",
  "external_id": "generated-external-id",
  "instructions": "Click the link, review permissions, and create the CloudFormation stack"
}
```

### Check Integration Created

```bash
python scripts/view_database.py
```

**Expected:**

```
🔗 AWS Integrations (1):
   - test@example.com
     Status: pending
     External ID: generated-external-id
     Role ARN: Not set
     Created: 2024-01-01 00:00:00+00:00
```

---

## Troubleshooting

### Database Connection Failed

```
❌ Error: could not connect to server
```

**Solutions:**

1. Check Aurora endpoint is correct
2. Verify security group allows your IP:
   - Go to RDS Console → Security Groups
   - Add inbound rule: PostgreSQL (5432) from My IP
3. Test with psql:
   ```bash
   psql -h your-endpoint -U postgres -d ezbuilt
   ```

### Migration Failed

```
❌ Error: relation "users" already exists
```

**Solution:**

```bash
# Drop and recreate (DEV ONLY!)
alembic downgrade base
alembic upgrade head
```

### Backend Won't Start

```
❌ Error: No module named 'sqlalchemy'
```

**Solution:**

```bash
cd backend
pip install -r requirements.txt
```

### Frontend Can't Reach Backend

```
❌ Failed to sync user to backend
```

**Solutions:**

1. Check backend is running: http://localhost:8000
2. Check CORS settings in `backend/main.py`
3. Verify `BACKEND_URL` in `frontend/.env.local`

### User Not Created After Login

```
No users in database after login
```

**Debug:**

1. Check browser console for errors
2. Check backend logs for `/api/auth/sync-user` request
3. Verify callback route is calling sync endpoint:
   ```bash
   # Check frontend logs
   npm run dev
   # Look for "Failed to sync user to backend" message
   ```

---

## Quick Test Script

Create `backend/test_full_flow.py`:

```python
import asyncio
import httpx

async def test_flow():
    base_url = "http://localhost:8000"

    print("1. Testing health check...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}/")
        assert resp.status_code == 200
        print("   ✅ Health check passed")

        print("\n2. Creating test user...")
        resp = await client.post(
            f"{base_url}/api/auth/sync-user",
            json={
                "sub": "test-123",
                "email": "test@example.com",
                "name": "Test User"
            }
        )
        assert resp.status_code == 200
        user = resp.json()
        print(f"   ✅ User created: {user['email']}")

        print("\n3. Getting user...")
        resp = await client.get(f"{base_url}/api/auth/user/{user['user_id']}")
        assert resp.status_code == 200
        print(f"   ✅ User retrieved: {resp.json()['email']}")

        print("\n4. Creating AWS integration...")
        resp = await client.post(
            f"{base_url}/api/generate-cfn-link",
            json={"user_id": user['user_id']}
        )
        assert resp.status_code == 200
        print(f"   ✅ Integration created: {resp.json()['external_id']}")

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_flow())
```

Run:

```bash
cd backend
python test_full_flow.py
```

---

## Success Checklist

- [ ] Database connection works
- [ ] Migrations applied successfully
- [ ] Backend server starts without errors
- [ ] Health check endpoint responds
- [ ] Can create user via API
- [ ] Can retrieve user via API
- [ ] User appears in database
- [ ] Frontend login redirects to Cognito
- [ ] After login, user synced to database
- [ ] AWS integration can be created
- [ ] Integration appears in database

---

## Next Steps

Once all tests pass:

1. Test with real Cognito login
2. Complete AWS account connection flow
3. Test terraform generation with connected account
4. Set up production database
5. Update environment variables for production
