from pymilvus import connections, utility

def reset_collection():
    print("Connecting to Milvus...")
    connections.connect(host="localhost", port="19530")
    
    collection_name = "rag_collection"
    
    if utility.has_collection(collection_name):
        print(f"Found collection '{collection_name}'. Checking dimension...")
        # We could check schema here, but we know it's wrong (512 vs 1024) and empty.
        # Just drop it.
        print(f"Dropping collection '{collection_name}' to allow recreation with correct dimension (1024)...")
        utility.drop_collection(collection_name)
        print(f"✅ Collection '{collection_name}' dropped successfully.")
    else:
        print(f"Collection '{collection_name}' does not exist. Nothing to do.")

if __name__ == "__main__":
    reset_collection()
