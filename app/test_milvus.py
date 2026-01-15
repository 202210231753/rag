from pymilvus import connections, utility
import sys

print("Testing Milvus connection...")
try:
    connections.connect("default", host="localhost", port="19530")
    print("Connected to Milvus.")
except Exception as e:
    print(f"Failed to connect: {e}")
    sys.exit(1)

print("Checking collection existence (this actually sends a request)...")
try:
    res = utility.has_collection("test_collection_probe")
    print(f"Check result: {res}")
except Exception as e:
    print(f"Failed to check collection: {e}")

