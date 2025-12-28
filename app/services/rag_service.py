from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document, DocStatus
from app.models.chunk import Chunk
import logging

logger = logging.getLogger(__name__)

class RagService:
    def __init__(self):
        # 1. 初始化 Embedding 模型
        # 优先使用配置，如果没有配置则使用项目指定的 Qwen3-Embedding-0.6B
        model_path = settings.EMBEDDING_MODEL_PATH
        if not model_path:
            model_path = "/home/yl/yl/yl/code-llm/Qwen/Qwen3-Embedding-0.6B"
            logger.info(f"EMBEDDING_MODEL_PATH not set, using project default: {model_path}")
        
        logger.info(f"Loading Embedding model: {model_path}...")
        # trust_remote_code=True 是因为 Qwen 模型通常需要执行远程代码
        self.embed_model = HuggingFaceEmbedding(model_name=model_path, trust_remote_code=True)
        
        # 2. 初始化 Milvus 向量库
        # Qwen3-Embedding-0.6B 的维度是 1024
        self.vector_dim = 1024
        
        self.vector_store = MilvusVectorStore(
            uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}",
            collection_name="rag_collection",
            dim=self.vector_dim,
            overwrite=False # 不覆盖，保留历史数据
        )
        
        # 3. 初始化切分器
        self.text_splitter = SentenceSplitter(chunk_size=500, chunk_overlap=50)

    def ingest_document(self, document_id: int, content: str):
        """
        将文档内容切分、向量化并存入数据库和 Milvus
        """
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.error(f"Document {document_id} not found")
                return

            # 更新状态为解析/索引中
            doc.status = DocStatus.PARSING 
            db.commit()

            # 1. 切分文本
            text_chunks = self.text_splitter.split_text(content)
            logger.info(f"Document {document_id} split into {len(text_chunks)} chunks.")
            
            nodes_for_milvus = []

            for i, text in enumerate(text_chunks):
                # 2. 创建 MySQL Chunk 记录
                db_chunk = Chunk(
                    document_id=document_id,
                    content=text,
                    index=i,
                    is_active=True,
                    data_type="text"
                )
                db.add(db_chunk)
                db.flush() # 获取自增 ID
                
                # 3. 生成向量
                # 注意：这里是同步调用，如果量大可能会慢，生产环境建议异步或批处理
                embedding = self.embed_model.get_text_embedding(text)
                
                # 4. 准备 Milvus 节点
                # 我们将 MySQL 的 Chunk ID 放入 metadata，方便反查
                node = TextNode(
                    text=text,
                    id_=str(db_chunk.id), # 使用 DB ID 作为 Node ID (String)
                    embedding=embedding,
                    metadata={
                        "document_id": document_id,
                        "chunk_id": db_chunk.id,
                        "is_active": True # 将状态也存入 Milvus，方便混合检索
                    }
                )
                nodes_for_milvus.append(node)
                
                # 更新 vector_id (这里简单地存一下 chunk_id，或者如果 Milvus 返回了内部 ID 再更新)
                # LlamaIndex 的 MilvusVectorStore 默认使用传入的 id_ 作为主键 (如果配置允许)
                # 这里我们暂且认为 vector_id 就是 chunk_id
                db_chunk.vector_id = db_chunk.id

            # 5. 批量写入 Milvus
            if nodes_for_milvus:
                self.vector_store.add(nodes_for_milvus)
            
            # 更新文档状态
            doc.status = DocStatus.COMPLETED
            doc.chunk_count = len(text_chunks)
            db.commit()
            logger.info(f"Document {document_id} ingestion completed.")
            
        except Exception as e:
            logger.error(f"Ingestion failed for doc {document_id}: {e}")
            doc.status = DocStatus.FAILED
            doc.error_msg = str(e)
            db.commit()
            # 重新抛出异常以便上层感知
            raise e
        finally:
            db.close()

    def toggle_doc_status(self, document_id: int, is_active: bool):
        """
        切换文档的上下线状态
        - 下线 (False): 更新 DB 状态，从 Milvus 删除向量
        - 上线 (True): 更新 DB 状态，重新生成向量入库
        """
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            # 1. 更新 Document 状态
            doc.is_active = is_active
            
            # 2. 更新关联 Chunk 状态
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
            for chunk in chunks:
                chunk.is_active = is_active
            
            db.commit()
            
            # 3. 处理 Milvus 数据
            if not is_active:
                # 下线：物理删除向量
                logger.info(f"Disabling document {document_id}: Deleting vectors from Milvus...")
                # MilvusVectorStore 的 delete 方法通常接受 node_id (即我们的 chunk_id)
                # 但 LlamaIndex 的 delete 接口比较简单，我们直接用 pymilvus 的 delete 表达式更灵活
                # 这里我们利用 vector_store 内部的 client
                
                # 构造删除表达式: document_id == {document_id}
                # 注意：我们在 ingest 时存了 metadata["document_id"]
                # Milvus 删除语法: delete(expr="document_id == 123")
                
                # 获取 pymilvus Collection 对象
                # LlamaIndex 封装得比较深，我们直接用 pymilvus 库操作最稳妥
                # 或者使用 vector_store.client.delete(collection_name, expr)
                
                # 暂时用一种通用的方式：查出所有 chunk_id 然后删除
                chunk_ids = [str(c.id) for c in chunks]
                if chunk_ids:
                    self.vector_store.delete_nodes(chunk_ids)
                    logger.info(f"Deleted {len(chunk_ids)} vectors for document {document_id}")
                
            else:
                # 上线：重新向量化入库
                logger.info(f"Enabling document {document_id}: Re-indexing vectors...")
                
                nodes_for_milvus = []
                for chunk in chunks:
                    # 重新生成向量 (因为之前没存向量在 MySQL，只存了文本)
                    # 这一步可能会比较耗时，如果文档很大，建议异步处理
                    embedding = self.embed_model.get_text_embedding(chunk.content)
                    
                    node = TextNode(
                        text=chunk.content,
                        id_=str(chunk.id),
                        embedding=embedding,
                        metadata={
                            "document_id": document_id,
                            "chunk_id": chunk.id,
                            "is_active": True
                        }
                    )
                    nodes_for_milvus.append(node)
                
                if nodes_for_milvus:
                    self.vector_store.add(nodes_for_milvus)
                    logger.info(f"Re-indexed {len(nodes_for_milvus)} vectors for document {document_id}")

        except Exception as e:
            logger.error(f"Failed to toggle status for doc {document_id}: {e}")
            db.rollback()
            raise e
        finally:
            db.close()

rag_service = RagService()
