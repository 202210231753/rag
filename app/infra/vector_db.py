from typing import List, Dict, Optional
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from chatbot.rag.app.data.models import Item
import random
import os
from dotenv import load_dotenv

load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

class VectorDBClient:
    def __init__(self, collection_name="rag_items"):
        self.collection_name = collection_name
        self._connect()
        self._ensure_collection()

    def _connect(self):
        try:
            connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
            print(f"Connected to Milvus at {MILVUS_HOST}:{MILVUS_PORT}")
        except Exception as e:
            print(f"Failed to connect to Milvus: {e}")
            raise e

    def _ensure_collection(self):
        print(f"Checking if collection {self.collection_name} exists...")
        if not utility.has_collection(self.collection_name):
            print(f"Collection {self.collection_name} does not exist. Creating...")
            fields = [
                FieldSchema(name="item_id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="source_id", dtype=DataType.VARCHAR, max_length=100), # 原始ID
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
                FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=500), # JSON string
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024) # 假设 Qwen Embedding 是 1024 维
            ]
            schema = CollectionSchema(fields, "RAG Knowledge Base")
            collection = Collection(self.collection_name, schema)
            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index(field_name="vector", index_params=index_params)
            collection.load()
            print(f"Collection {self.collection_name} created and loaded.")
        else:
            collection = Collection(self.collection_name)
            collection.load()
            print(f"Collection {self.collection_name} loaded.")
        
        self.collection = Collection(self.collection_name)

    def insert_items(self, items: List[Item]):
        import json
        data = [
            [item.item_id for item in items], # source_id
            [item.content for item in items],
            [json.dumps(item.tags) for item in items],
            [item.vector for item in items]
        ]
        self.collection.insert(data)
        self.collection.flush()
        print(f"Inserted {len(items)} items into Milvus.")

    def search_ann(self, vector: List[float], topk: int, filter_type: str = "all") -> List[Item]:
        """
        filter_type: 
          - "all": 不过滤
          - "content": 只搜内容 (source_id 不以 query_ 开头)
          - "query": 只搜查询建议 (source_id 以 query_ 开头)
        """
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        
        # 策略：为了避免 Milvus expr 解析报错，这里我们先把 limit 放大，然后在 Python 内存中进行过滤
        # 这种方式兼容性最好，适合 Demo 级数据量
        expanded_limit = topk * 3 

        results = self.collection.search(
            data=[vector], 
            anns_field="vector", 
            param=search_params, 
            limit=expanded_limit, 
            # expr=expr, # 暂时禁用 expr 以避免 MilvusException
            output_fields=["source_id", "content", "tags"]
        )
        
        items = []
        import json
        for hits in results:
            for hit in hits:
                source_id = hit.entity.get("source_id")
                
                # --- Python 端过滤逻辑 ---
                if filter_type == "content":
                    if str(source_id).startswith("query_"):
                        continue
                elif filter_type == "query":
                    if not str(source_id).startswith("query_"):
                        continue
                # -----------------------

                items.append(Item(
                    item_id=source_id,
                    content=hit.entity.get("content"),
                    tags=json.loads(hit.entity.get("tags")),
                    score=hit.score
                ))
                
                # 够数了就停
                if len(items) >= topk:
                    break
                    
        return items

    def search_standard_tags(self, vector: List[float]) -> str:
        # 这里暂时保留 Mock 或后续实现专门的 Tag 集合
        tags = ["technology", "lifestyle", "finance", "education"]
        return random.choice(tags)
