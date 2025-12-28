from app.services.storage_service import storage_service
import traceback

try:
    print("Checking bucket existence...")
    storage_service.ensure_bucket_exists()
    print("Bucket check passed.")
    
    print("Testing upload...")
    storage_service.upload_file(b"test content", "test_file.txt")
    print("Upload passed.")
    
    print("Testing download...")
    data = storage_service.get_file("test_file.txt")
    print(f"Download passed. Content: {data.read()}")
    data.close()
    data.release_conn()
    
    print("✅ MinIO connection is working perfectly.")
except Exception as e:
    print("❌ MinIO connection failed!")
    traceback.print_exc()
