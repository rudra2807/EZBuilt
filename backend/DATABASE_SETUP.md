# Database Setup Guide

## 1. Update Environment Variables

Add to `backend/.env.local`:

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:your-password@your-aurora-endpoint.region.rds.amazonaws.com:5432/ezbuilt

# AWS Configuration
AWS_REGION=us-east-1

# S3 Terraform Storage (Required for S3-based Terraform file storage)
EZBUILT_TERRAFORM_SOURCE_BUCKET=ezbuilt-terraform-source
```

Replace `your-aurora-endpoint.region.rds.amazonaws.com` with your actual Aurora endpoint.

### Environment Variable Details

- `DATABASE_URL`: PostgreSQL connection string for RDS Aurora
- `AWS_REGION`: AWS region for S3 and other AWS services (default: us-east-1)
- `EZBUILT_TERRAFORM_SOURCE_BUCKET`: S3 bucket name for storing Terraform source files

## 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## 3. Initialize Alembic (First Time Only)

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

## 4. Future Migrations

When you modify models in `src/database/models.py`:

```bash
# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Apply migration
alembic upgrade head
```

## 5. Database Connection Test

Create a test script `test_db.py`:

```python
import asyncio
from src.database import AsyncSessionLocal, UserRepository

async def test_connection():
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user = await user_repo.create(email="test@example.com")
        print(f"Created user: {user.user_id}")

asyncio.run(test_connection())
```

Run: `python test_db.py`

## Schema Overview

### Users Table

- `user_id` (UUID, PK)
- `email` (VARCHAR, unique)
- `created_at` (TIMESTAMP)
- `last_login` (TIMESTAMP, nullable)

### AWS Integrations Table

- `id` (UUID, PK)
- `user_id` (UUID, FK → users)
- `aws_account_id` (VARCHAR, nullable)
- `external_id` (VARCHAR, unique)
- `role_arn` (VARCHAR, nullable)
- `status` (ENUM: pending, connected, failed)
- `created_at` (TIMESTAMP)
- `verified_at` (TIMESTAMP, nullable)

## Notes

- Using async SQLAlchemy with asyncpg driver
- Alembic handles schema migrations
- Repository pattern for clean data access
- All timestamps are timezone-aware (UTC)
