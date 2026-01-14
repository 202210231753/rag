from pymilvus import connections, Collection, utility

def check_milvus():
    print("Connecting to Milvus...")
    try:
        # 连接 Milvus
        connections.connect(alias="default", host="localhost", port="19530")
        print("✅ Connected to Milvus!")
        
        # 列出所有集合
        collections = utility.list_collections()
        print(f"\nCollections found: {collections}")
        
        if "rag_collection" in collections:
            # 获取集合详情
            collection = Collection("rag_collection")
            
            # Flush data to ensure it's persisted and visible
            collection.flush()
            
            # 加载集合到内存才能查询
            collection.load()
            
            # 获取行数
            count = collection.num_entities
            print(f"\nCollection 'rag_collection' has {count} entities.")
            
            # 获取 Schema
            print("\nSchema:")
            for field in collection.schema.fields:
                print(f" - {field.name}: {field.dtype} (dim={field.params.get('dim') if field.params else ''})")
            
            if count > 0:
                # 尝试查询前 3 条数据
                print("\nSample Data (Top 3):")
                results = collection.query(
                    expr="", 
                    output_fields=["chunk_id", "document_id", "is_active"], # 只查元数据，不查向量
                    limit=3
                )
                for res in results:
                    print(res)
            else:
                print("\n⚠️ Collection is empty.")
                
        else:
            print("\n❌ Collection 'rag_collection' NOT found.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    check_milvus()
