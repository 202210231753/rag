from app.core.database import SessionLocal
from app.models.document import Document
import sys

def check_status():
    db = SessionLocal()
    try:
        # Get the latest document
        doc = db.query(Document).order_by(Document.id.desc()).first()
        if not doc:
            print("No documents found in database.")
            return

        print(f"Latest Document ID: {doc.id}")
        print(f"Filename: {doc.filename}")
        print(f"Status: {doc.status}")
        print(f"Error Message: {doc.error_msg}")
        print("-" * 20)
        
        # List all documents
        docs = db.query(Document).all()
        print(f"Total documents: {len(docs)}")
        for d in docs:
             print(f"ID: {d.id}, Status: {d.status}, File: {d.filename}")

    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_status()
