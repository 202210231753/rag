import sys
import os
import random

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from chatbot.rag.app.infra.vector_db import VectorDBClient
from chatbot.rag.app.data.models import Item

def init_milvus_data():
    print("=== Initializing Milvus Data ===")
    
    # 1. 模拟一些带向量的数据 (Qwen Embedding 维度通常是 1024 或 1536，这里用 1024 模拟)
    # 注意：真实场景中应该调用 AIModelClient.get_embedding 来生成向量
    dim = 1024
    
    # 模拟数据
    mock_items = [
        Item(item_id="1", content="Advanced Python Guide", tags=["python", "programming"], vector=[random.random() for _ in range(dim)]),
        Item(item_id="2", content="Machine Learning Basics", tags=["ai", "ml"], vector=[random.random() for _ in range(dim)]),
        Item(item_id="3", content="Travel to Japan", tags=["travel", "asia"], vector=[random.random() for _ in range(dim)]),
        Item(item_id="4", content="Healthy Cooking", tags=["food", "health"], vector=[random.random() for _ in range(dim)]),
        Item(item_id="5", content="Docker Containerization", tags=["devops", "docker"], vector=[random.random() for _ in range(dim)]),
        Item(item_id="6", content="DeepSeek LLM Tutorial", tags=["ai", "llm", "deepseek"], vector=[random.random() for _ in range(dim)]),
        Item(item_id="7", content="FastAPI Best Practices", tags=["python", "web"], vector=[random.random() for _ in range(dim)]),
    ]
    
    client = VectorDBClient()
    
    # 插入数据
    client.insert_items(mock_items)
    print("Done.")

if __name__ == "__main__":
    init_milvus_data()

