import sys
import os

# Ensure app can be imported
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings
from pymilvus import connections, utility

def clean_all_data():
    print("🚀 Starting data cleanup...")

    # 1. Clean MySQL
    try:
        print("\n[1/2] Cleaning MySQL (Metadata)...")
        with engine.connect() as conn:
            # Disable foreign key checks to delete in any order
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            conn.execute(text("TRUNCATE TABLE chunks"))
            conn.execute(text("TRUNCATE TABLE documents"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
        print("✅ MySQL tables 'documents' and 'chunks' cleared.")
    except Exception as e:
        print(f"❌ MySQL cleanup failed: {e}")

    # 2. Clean Milvus
    try:
        print("\n[2/2] Cleaning Milvus (Vectors)...")
        # Connect to Milvus
        print(f"Connecting to Milvus at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}...")
        connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
        
        collection_name = "rag_collection"
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
            print(f"✅ Milvus collection '{collection_name}' dropped.")
        else:
            print(f"ℹ️  Milvus collection '{collection_name}' does not exist.")
            
    except Exception as e:
        print(f"❌ Milvus cleanup failed: {e}")

    print("\n✨ Cleanup finished!")

if __name__ == "__main__":
    # Ask for confirmation
    confirm = input("⚠️  This will DELETE ALL DATA in MySQL and Milvus. Are you sure? (y/n): ")
    if confirm.lower() == 'y':
        clean_all_data()
    else:
        print("Operation cancelled.")
