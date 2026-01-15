import sys
import os
import torch
from transformers import AutoModel, AutoTokenizer

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from app.data.models import Item
from app.infra.vector_db import VectorDBClient

# Embedding Model Path (Same as in AIModelClient)
EMB_MODEL_PATH = "/home/yl/yl/yl/code-llm/Qwen/Qwen3-Embedding-0.6B"

def get_real_embedding(text, tokenizer, model, device):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    return embeddings[0].tolist()

def init_milvus_data():
    print("=== Initializing Milvus Data with Real Embeddings ===")
    
    # 1. Load Embedding Model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Embedding Model from: {EMB_MODEL_PATH} (Device: {device})")
    try:
        tokenizer = AutoTokenizer.from_pretrained(EMB_MODEL_PATH, trust_remote_code=True)
        model = AutoModel.from_pretrained(EMB_MODEL_PATH, trust_remote_code=True).to(device)
        print("Model loaded.")
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # 2. Define Data
    # Items for content recommendation (Scene 1)
    content_items_data = [
        ("1", "Advanced Python Guide", ["python", "programming"]),
        ("2", "Machine Learning Basics", ["ai", "ml"]),
        ("3", "Travel to Japan", ["travel", "asia"]),
        ("4", "Healthy Cooking", ["food", "health"]),
        ("5", "Docker Containerization", ["devops", "docker"]),
        ("6", "DeepSeek LLM Tutorial", ["ai", "llm", "deepseek"]),
        ("7", "FastAPI Best Practices", ["python", "web"]),
    ]
    
    # Items for query recommendation (Scene 2, id starts with query_)
    query_items_data = [
        ("query_1", "How to learn Python efficiently?", ["python", "learning"]),
        ("query_2", "Best travel destinations in Asia", ["travel", "asia"]),
        ("query_3", "What is RAG in AI?", ["ai", "rag"]),
        ("query_4", "DeepSeek vs Qwen performance", ["ai", "llm", "benchmark"]),
    ]

    all_items = []
    
    print("Generating embeddings...")
    
    # Process Content Items
    for iid, content, tags in content_items_data:
        vec = get_real_embedding(content, tokenizer, model, device)
        all_items.append(Item(item_id=iid, content=content, tags=tags, vector=vec))
        
    # Process Query Items
    for iid, content, tags in query_items_data:
        vec = get_real_embedding(content, tokenizer, model, device)
        all_items.append(Item(item_id=iid, content=content, tags=tags, vector=vec))

    # 3. Insert into Milvus
    client = VectorDBClient()
    # Ensure collection is recreated or cleared if needed. 
    # For now, we append. In a real init script, we might want to drop_collection first.
    # But VectorDBClient doesn't expose drop easily, so we just insert.
    
    client.insert_items(all_items)
    print("Done. Data initialized.")

if __name__ == "__main__":
    init_milvus_data()
