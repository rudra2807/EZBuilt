# EZBuilt Documentation Index

Quick reference to all project documentation.

## 📋 Core Documentation

### Project Overview

- **[README.md](./README.md)** - Project vision, architecture, and philosophy
- **[CURRENT_STATUS.md](./CURRENT_STATUS.md)** - Detailed current status, gaps, and roadmap

### Infrastructure & State

- **[TERRAFORM_STATE_MANAGEMENT.md](./TERRAFORM_STATE_MANAGEMENT.md)** - How Terraform state is managed in S3

## 🔧 Backend Documentation

### Setup & Configuration

- **[backend/DATABASE_SETUP.md](./backend/DATABASE_SETUP.md)** - PostgreSQL database setup with Alembic
- **[backend/DATABASE_CLIENT_SETUP.md](./backend/DATABASE_CLIENT_SETUP.md)** - Database client tools (pgAdmin, DBeaver, etc.)
- **[backend/TESTING_GUIDE.md](./backend/TESTING_GUIDE.md)** - Testing instructions and verification

### Architecture

- **[backend/AUTH_FLOW.md](./backend/AUTH_FLOW.md)** - Cognito authentication flow and endpoints

## 🎨 Frontend Documentation

### 🚀 Quick Start

1. **Setup Database:** Follow [backend/DATABASE_SETUP.md](./backend/DATABASE_SETUP.md)
2. **Configure Environment:** Set up `.env.local` files for backend and frontend
3. **Run Migrations:** `alembic upgrade head`
4. **Start Backend:** `python main.py`
5. **Start Frontend:** `npm run dev`
6. **Test:** Follow [backend/TESTING_GUIDE.md](./backend/TESTING_GUIDE.md)

## 📊 Current Status Summary

### ✅ Working

- Authentication (Cognito)
- AWS account connection
- Infrastructure generation
- Deployment history

### ⚠️ Known Issues

- JWT authentication (backend returns 501)
- Token signature verification
- Token refresh logic

See [CURRENT_STATUS.md](./CURRENT_STATUS.md) for complete details.

## 🗂️ File Organization

```
EZBuilt/
├── README.md                          # Project overview
├── CURRENT_STATUS.md                  # Detailed status & roadmap
├── TERRAFORM_STATE_MANAGEMENT.md      # State management docs
├── DOCUMENTATION_INDEX.md             # This file
│
├── backend/
│   ├── AUTH_FLOW.md                   # Authentication flow
│   ├── DATABASE_SETUP.md              # Database setup
│   ├── DATABASE_CLIENT_SETUP.md       # Client tools
│   ├── TESTING_GUIDE.md               # Testing guide
│   ├── main.py                        # FastAPI application
│   └── src/
│       ├── apis/                      # API routes
│       ├── database/                  # Models & repositories
│       ├── services/                  # Business logic
│       └── utilities/                 # Shared utilities
│
└── frontend/
    └── src/
        ├── app/                       # Next.js pages
        ├── components/                # React components
        └── lib/                       # Utilities

```

## 🔗 External Resources

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [Terraform Documentation](https://www.terraform.io/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

---

**Last Updated:** February 28, 2026
