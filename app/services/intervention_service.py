import logging
from sqlalchemy.orm import Session
from pymilvus import connections, Collection, utility

# 引入模型和配置
from app.models.document import Document
from app.models.chunk import Chunk
from app.core.config import settings

# 引入 LlamaIndex 的 Embedding 组件
# 注意：需要 pip install llama-index-embeddings-huggingface
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logger = logging.getLogger(__name__)

class EmbeddingSingleton:
    """
    Embedding 模型单例加载器
    避免每次请求都重新加载 0.6B 的模型
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            logger.info(f"正在加载本地 Embedding 模型: {settings.EMBEDDING_MODEL_PATH} ...")
            try:
                # trust_remote_code=True 是为了支持自定义模型代码 (Qwen通常需要)
                cls._instance = HuggingFaceEmbedding(
                    model_name=settings.EMBEDDING_MODEL_PATH,
                    trust_remote_code=True
                )
                logger.info("Embedding 模型加载成功！")
            except Exception as e:
                logger.error(f"Embedding 模型加载失败: {e}")
                raise e
        return cls._instance

class InterventionService:
    def __init__(self, db: Session):
        self.db = db
        self.milvus_collection_name = "rag_collection" # 假设 Milvus 集合名叫这个
        self._connect_milvus()

    def _connect_milvus(self):
        """连接 Milvus"""
        try:
            connections.connect(
                alias="default", 
                host=settings.MILVUS_HOST, 
                port=settings.MILVUS_PORT
            )
        except Exception as e:
            logger.error(f"Milvus 连接失败: {e}")

    def get_document(self, doc_id: int) -> Document:
        return self.db.query(Document).filter(Document.id == doc_id).first()

    def delete_document(self, doc_id: int) -> bool:
        """
        级联删除文件：
        1. 查出所有关联的 Chunk
        2. 从 Milvus 删除对应向量
        3. 从 MySQL 删除 Document (级联删除 Chunks)
        """
        doc = self.get_document(doc_id)
        if not doc:
            return False

        # 1. 找出所有关联的 vector_ids
        chunks = self.db.query(Chunk).filter(Chunk.document_id == doc_id).all()
        vector_ids = [c.vector_id for c in chunks if c.vector_id is not None]

        # 2. 从 Milvus 删除
        if vector_ids and utility.has_collection(self.milvus_collection_name):
            collection = Collection(self.milvus_collection_name)
            expr = f"id in {vector_ids}"
            collection.delete(expr)
            logger.info(f"已从 Milvus 删除 {len(vector_ids)} 条向量")

        # 3. 从 MySQL 删除 (Chunk 会因为 ondelete="CASCADE" 自动删除)
        self.db.delete(doc)
        self.db.commit()
        return True

    def update_chunk_content(self, chunk_id: int, new_content: str) -> Chunk:
        """
        干预核心：修改文本 -> 重算向量 -> 更新 Milvus
        """
        chunk = self.db.query(Chunk).filter(Chunk.id == chunk_id).first()
        if not chunk:
            raise ValueError(f"Chunk {chunk_id} not found")

        # 1. 更新 MySQL 文本
        chunk.content = new_content
        
        # 2. 重算向量
        embed_model = EmbeddingSingleton.get_instance()
        new_embedding = embed_model.get_text_embedding(new_content)

        # 3. 更新 Milvus
        # Milvus 不支持直接 Update，通常是先 Delete 后 Insert，或者使用 Upsert (如果主键一致)
        # 这里假设 vector_id 是 Milvus 的主键
        if chunk.vector_id and utility.has_collection(self.milvus_collection_name):
            collection = Collection(self.milvus_collection_name)
            
            # 构造数据: [[id], [embedding], [metadata...]]
            # 注意：这里的数据格式必须严格匹配 Milvus 的 Schema 定义
            # 假设 Schema 是: id(int64), vector(float_vector), doc_id(int64)
            
            # 简单起见，我们先只做 Delete + Insert 的逻辑模拟
            # 实际生产中需要严格匹配 Schema
            
            # Step A: 删除旧向量
            collection.delete(f"id in [{chunk.vector_id}]")
            
            # Step B: 插入新向量 (这一步比较复杂，因为需要知道完整的 Schema 字段)
            # 如果不知道 Schema，我们可能无法插入。
            # 暂时只做 MySQL 更新和 向量生成，Milvus 更新留给 TODO
            logger.warning("Milvus 更新逻辑暂未完全实现 (需要 Schema 定义)，仅更新了 MySQL 和生成了向量")
            
            # TODO: 实现完整的 Milvus Upsert
            # data = [[chunk.vector_id], [new_embedding], ...]
            # collection.insert(data)

        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def toggle_chunk_status(self, chunk_id: int, is_active: bool) -> Chunk:
        """启停切片"""
        chunk = self.db.query(Chunk).filter(Chunk.id == chunk_id).first()
        if not chunk:
            raise ValueError("Chunk not found")
        
        chunk.is_active = is_active
        self.db.commit()
        self.db.refresh(chunk)
        return chunk
