"""
Full integration test script
Tests: Health check → Create user → Get user → Create AWS integration
Run: python scripts/test_full_flow.py
"""
import asyncio
import httpx
import sys

async def test_flow():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing EZBuilt Backend Integration\n")
    print("=" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test 1: Health Check
            print("\n1️⃣  Testing health check...")
            try:
                resp = await client.get(f"{base_url}/")
                assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
                data = resp.json()
                print(f"   ✅ Health check passed: {data['service']} v{data['version']}")
            except httpx.ConnectError:
                print("   ❌ Cannot connect to backend. Is it running?")
                print("      Start with: cd backend && python main.py")
                sys.exit(1)
            
            # Test 2: Create User
            print("\n2️⃣  Creating test user...")
            test_user = {
                "sub": "test-integration-123",
                "email": "integration-test@example.com",
                "name": "Integration Test User"
            }
            resp = await client.post(
                f"{base_url}/api/auth/sync-user",
                json=test_user
            )
            
            if resp.status_code != 200:
                print(f"   ❌ Failed to create user: {resp.status_code}")
                print(f"      Response: {resp.text}")
                sys.exit(1)
            
            user = resp.json()
            print(f"   ✅ User created:")
            print(f"      - ID: {user['user_id']}")
            print(f"      - Email: {user['email']}")
            print(f"      - Created: {user['created_at']}")
            
            # Test 3: Get User
            print("\n3️⃣  Retrieving user...")
            resp = await client.get(f"{base_url}/api/auth/user/{user['user_id']}")
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            retrieved_user = resp.json()
            assert retrieved_user['email'] == test_user['email']
            print(f"   ✅ User retrieved successfully")
            print(f"      - Last login: {retrieved_user['last_login']}")
            
            # Test 4: Create AWS Integration
            print("\n4️⃣  Creating AWS integration...")
            resp = await client.post(
                f"{base_url}/api/generate-cfn-link",
                json={"user_id": user['user_id']}
            )
            
            if resp.status_code != 200:
                print(f"   ❌ Failed to create integration: {resp.status_code}")
                print(f"      Response: {resp.text}")
                sys.exit(1)
            
            integration = resp.json()
            print(f"   ✅ AWS integration created:")
            print(f"      - External ID: {integration['external_id']}")
            print(f"      - CFN Link: {integration['cfn_link'][:80]}...")
            
            # Test 5: Check Connection Status
            print("\n5️⃣  Checking connection status...")
            resp = await client.get(
                f"{base_url}/api/connection-status/{integration['external_id']}"
            )
            assert resp.status_code == 200
            status = resp.json()
            print(f"   ✅ Connection status retrieved:")
            print(f"      - Status: {status['status']}")
            print(f"      - Connected: {status['connected']}")
            
    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("\n📊 Next steps:")
    print("   1. View data: python scripts/view_database.py")
    print("   2. Test login: http://localhost:3000")
    print("   3. Check API docs: http://localhost:8000/docs")

if __name__ == "__main__":
    asyncio.run(test_flow())
