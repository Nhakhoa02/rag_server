#!/usr/bin/env python3
"""
Test script for RAG Server Multi-Index functionality
"""

import asyncio
import aiohttp
import json
import os
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_FILES = {
    "pdf": "test_document.pdf",
    "txt": "test_document.txt", 
    "csv": "test_data.csv"
}

async def create_test_files():
    """Create test files for different types"""
    test_dir = Path("test_files")
    test_dir.mkdir(exist_ok=True)
    
    # Create test PDF content (simplified)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(This is a test PDF document) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF"
    
    # Create test text file
    txt_content = "This is a test text document. It contains information about various topics including technology, science, and business."
    
    # Create test CSV file
    csv_content = "Name,Age,Department\nJohn Doe,30,Engineering\nJane Smith,25,Marketing\nBob Johnson,35,Sales"
    
    # Write test files
    with open(test_dir / "test_document.pdf", "wb") as f:
        f.write(pdf_content)
    
    with open(test_dir / "test_document.txt", "w") as f:
        f.write(txt_content)
    
    with open(test_dir / "test_data.csv", "w") as f:
        f.write(csv_content)
    
    return test_dir

async def test_health_check(session):
    """Test health endpoints"""
    print("🔍 Testing health endpoints...")
    
    # Basic health check
    async with session.get(f"{BASE_URL}/health") as response:
        if response.status == 200:
            data = await response.json()
            print(f"✅ Basic health check: {data['status']}")
        else:
            print(f"❌ Basic health check failed: {response.status}")
    
    # Detailed health check
    async with session.get(f"{BASE_URL}/health/detailed") as response:
        if response.status == 200:
            data = await response.json()
            print(f"✅ Detailed health check: {data['status']}")
            for service, status in data.get('services', {}).items():
                print(f"   - {service}: {status}")
        else:
            print(f"❌ Detailed health check failed: {response.status}")

async def upload_test_file(session, file_path, file_type):
    """Upload a test file"""
    print(f"📤 Uploading {file_type} file: {file_path.name}")
    
    with open(file_path, 'rb') as f:
        data = aiohttp.FormData()
        data.add_field('file', f, filename=file_path.name)
        data.add_field('user_id', 'test_user')
        
        async with session.post(f"{BASE_URL}/api/v1/documents/upload", data=data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ {file_type} uploaded successfully: {result['file_id']}")
                return result['file_id']
            else:
                print(f"❌ {file_type} upload failed: {response.status}")
                return None

async def wait_for_processing(session, file_id, max_wait=30):
    """Wait for document processing to complete"""
    print(f"⏳ Waiting for processing of {file_id}...")
    
    for i in range(max_wait):
        async with session.get(f"{BASE_URL}/api/v1/documents/{file_id}") as response:
            if response.status == 200:
                doc = await response.json()
                status = doc.get('status')
                if status == 'completed':
                    print(f"✅ Processing completed for {file_id}")
                    return True
                elif status == 'failed':
                    print(f"❌ Processing failed for {file_id}: {doc.get('error')}")
                    return False
                else:
                    print(f"⏳ Still processing... ({i+1}/{max_wait})")
                    await asyncio.sleep(1)
            else:
                print(f"❌ Failed to check status: {response.status}")
                return False
    
    print(f"⏰ Processing timeout for {file_id}")
    return False

async def test_query(session, query, search_mode="all", filter_metadata=None):
    """Test a query with different search modes"""
    print(f"🔍 Testing query: '{query}' (mode: {search_mode})")
    
    payload = {
        "query": query,
        "user_id": "test_user",
        "search_mode": search_mode
    }
    
    if filter_metadata:
        payload["filter_metadata"] = filter_metadata
    
    async with session.post(f"{BASE_URL}/api/v1/queries/ask", json=payload) as response:
        if response.status == 200:
            result = await response.json()
            print(f"✅ Query successful")
            print(f"   Answer: {result['answer'][:100]}...")
            print(f"   Sources: {len(result['sources'])} found")
            for i, source in enumerate(result['sources'][:3]):
                print(f"   Source {i+1}: {source.get('metadata', {}).get('file_type', 'unknown')} (score: {source.get('distance', 0):.3f})")
            return result
        else:
            print(f"❌ Query failed: {response.status}")
            return None

async def test_multi_index_search(session):
    """Test multi-index search functionality"""
    print("\n🚀 Testing Multi-Index Search Functionality")
    print("=" * 50)
    
    # Create test files
    test_dir = await create_test_files()
    
    # Upload different file types
    file_ids = {}
    for file_type, filename in TEST_FILES.items():
        file_path = test_dir / filename
        if file_path.exists():
            file_id = await upload_test_file(session, file_path, file_type)
            if file_id:
                file_ids[file_type] = file_id
                # Wait for processing
                await wait_for_processing(session, file_id)
    
    if not file_ids:
        print("❌ No files were uploaded successfully")
        return
    
    print(f"\n📁 Uploaded files: {list(file_ids.keys())}")
    
    # Test 1: Search all collections
    print("\n1️⃣ Testing search across all collections...")
    await test_query(session, "What information is available in the documents?")
    
    # Test 2: Search specific file type (PDF)
    if 'pdf' in file_ids:
        print("\n2️⃣ Testing PDF-specific search...")
        await test_query(
            session, 
            "What is in the PDF document?", 
            search_mode="file_type",
            filter_metadata={"file_type": "pdf"}
        )
    
    # Test 3: Search specific file type (CSV)
    if 'csv' in file_ids:
        print("\n3️⃣ Testing CSV-specific search...")
        await test_query(
            session, 
            "What data is in the spreadsheet?", 
            search_mode="file_type",
            filter_metadata={"file_type": "csv"}
        )
    
    # Test 4: Search specific collection
    print("\n4️⃣ Testing collection-specific search...")
    await test_query(
        session, 
        "What documents are in the PDF collection?", 
        search_mode="collection",
        filter_metadata={"collection": "rag_pdf_documents"}
    )
    
    # Test 5: Check vector store metrics
    print("\n5️⃣ Testing vector store metrics...")
    async with session.get(f"{BASE_URL}/health/metrics") as response:
        if response.status == 200:
            metrics = await response.json()
            vector_metrics = metrics.get('vector_store', {})
            print(f"✅ Vector store status: {vector_metrics.get('status', 'unknown')}")
            print(f"   Collections: {vector_metrics.get('collections_count', 0)}")
            print(f"   Total points: {vector_metrics.get('total_points', 0)}")
        else:
            print(f"❌ Failed to get metrics: {response.status}")

async def main():
    """Main test function"""
    print("🧪 RAG Server Multi-Index Test Suite")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test health
        await test_health_check(session)
        
        # Test multi-index functionality
        await test_multi_index_search(session)
    
    print("\n🎉 Test suite completed!")

if __name__ == "__main__":
    asyncio.run(main()) 