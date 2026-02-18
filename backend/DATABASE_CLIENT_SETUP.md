# Database Client Setup for Aurora PostgreSQL

## Option 1: pgAdmin (Recommended - Free & Feature-Rich)

### Installation

1. Download from: https://www.pgadmin.org/download/
2. Install for Windows

### Setup

1. Open pgAdmin
2. Right-click "Servers" → "Register" → "Server"
3. **General Tab:**
   - Name: `EZBuilt Aurora`
4. **Connection Tab:**
   - Host: `your-aurora-endpoint.region.rds.amazonaws.com`
   - Port: `5432`
   - Maintenance database: `postgres`
   - Username: `postgres`
   - Password: `ezbuilt-master`
   - Save password: ✓
5. Click "Save"

### Usage

- Browse tables: Servers → EZBuilt Aurora → Databases → ezbuilt → Schemas → public → Tables
- Run queries: Right-click database → "Query Tool"
- View data: Right-click table → "View/Edit Data" → "All Rows"

---

## Option 2: DBeaver (Free & Cross-Platform)

### Installation

1. Download from: https://dbeaver.io/download/
2. Install Community Edition

### Setup

1. Open DBeaver
2. Click "New Database Connection" (plug icon)
3. Select "PostgreSQL" → Next
4. **Connection Settings:**
   - Host: `your-aurora-endpoint.region.rds.amazonaws.com`
   - Port: `5432`
   - Database: `ezbuilt`
   - Username: `postgres`
   - Password: `ezbuilt-master`
5. Click "Test Connection" (downloads driver if needed)
6. Click "Finish"

### Usage

- Browse tables: Database Navigator → ezbuilt → Schemas → public → Tables
- View data: Double-click table
- Run queries: Right-click connection → "SQL Editor" → "New SQL Script"

---

## Option 3: VS Code Extension (Quick & Lightweight)

### Installation

1. Open VS Code
2. Install extension: "PostgreSQL" by Chris Kolkman
3. Reload VS Code

### Setup

1. Click PostgreSQL icon in sidebar
2. Click "+" to add connection
3. Enter connection details:
   - Host: `your-aurora-endpoint.region.rds.amazonaws.com`
   - User: `postgres`
   - Password: `ezbuilt-master`
   - Port: `5432`
   - Database: `ezbuilt`
   - Connection name: `EZBuilt Aurora`

### Usage

- Browse tables: Click connection → expand schemas → public → Tables
- Run queries: Right-click connection → "New Query"
- View data: Right-click table → "Select Top 1000"

---

## Option 4: Command Line (psql)

### Installation

Download PostgreSQL client tools:

- Windows: https://www.postgresql.org/download/windows/
- Or use: `winget install PostgreSQL.PostgreSQL`

### Connect

```bash
psql -h your-aurora-endpoint.region.rds.amazonaws.com -U postgres -d ezbuilt
# Enter password: ezbuilt-master
```

### Common Commands

```sql
-- List tables
\dt

-- Describe table
\d users
\d aws_integrations

-- View data
SELECT * FROM users;
SELECT * FROM aws_integrations;

-- Exit
\q
```

---

## Getting Your Aurora Endpoint

### From AWS Console:

1. Go to RDS Console: https://console.aws.amazon.com/rds/
2. Click "Databases"
3. Click your Aurora cluster
4. Copy "Endpoint" under "Connectivity & security"
5. Format: `your-cluster.cluster-xxxxx.region.rds.amazonaws.com`

### From AWS CLI:

```bash
aws rds describe-db-clusters --query "DBClusters[*].[DBClusterIdentifier,Endpoint]" --output table
```

---

## Security Note

Make sure your Aurora instance security group allows connections from your IP:

1. Go to RDS Console → Your cluster → "Connectivity & security"
2. Click the security group
3. Add inbound rule:
   - Type: PostgreSQL
   - Port: 5432
   - Source: My IP (or your specific IP)

---

## Quick Test Connection

Once you have your endpoint, test with Python:

```python
# test_connection.py
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect(
        host='your-aurora-endpoint.region.rds.amazonaws.com',
        port=5432,
        user='postgres',
        password='ezbuilt-master',
        database='ezbuilt'
    )
    version = await conn.fetchval('SELECT version()')
    print(f"Connected! PostgreSQL version: {version}")
    await conn.close()

asyncio.run(test())
```

Run: `python test_connection.py`

---

## Recommended: pgAdmin

For most users, I recommend **pgAdmin** because:

- Free and open source
- Full-featured GUI
- Easy table browsing and editing
- Built-in query tool with syntax highlighting
- Visual query builder
- Data export/import tools
