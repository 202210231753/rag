import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from chatbot.rag.app.infra.vector_db import VectorDBClient

print("=== Debugging Milvus Initialization ===")
print("Attempting to initialize VectorDBClient (this will connect and ensure collection)...")

try:
    # This will trigger _connect and _ensure_collection
    client = VectorDBClient(collection_name="rag_items")
    print("VectorDBClient initialized successfully!")
    
    # Try a simple insert
    print("Attempting dry-run insert check...")
    # (We won't actually insert unless we have data, but getting here means __init__ passed)
    
except Exception as e:
    print(f"FAILED during initialization: {e}")
    import traceback
    traceback.print_exc()

print("=== Debugging Complete ===")

