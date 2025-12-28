import sys
import os

# Ensure app can be imported
sys.path.append(os.getcwd())

from app.core.database import engine, Base
from app.models.document import Document
from app.models.chunk import Chunk

def reset_schema():
    print("🔄 Resetting database schema...")
    
    # 1. Drop all tables
    # We can use Base.metadata.drop_all(bind=engine) but it might miss tables if imports are wrong.
    # But since we imported Document and Chunk, it should be fine.
    print("🗑️  Dropping tables...")
    Base.metadata.drop_all(bind=engine)
    
    # 2. Create all tables
    print("✨ Creating tables with new schema...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database schema reset successfully!")

if __name__ == "__main__":
    reset_schema()
