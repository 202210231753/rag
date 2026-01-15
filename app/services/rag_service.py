from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.chunk import Chunk
from app.models.document import DocStatus, Document
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.abtest_service import ABTestService

logger = logging.getLogger(__name__)

DEFAULT_RAG_EXPERIMENT_ID = "rag_chat_prompt_v1"


class RagService:
    def __init__(self) -> None:
        model_path = (settings.EMBEDDING_MODEL_PATH or "").strip()
        if not model_path:
            model_path = "/home/yl/yl/yl/code-llm/Qwen/Qwen3-Embedding-0.6B"
            logger.info("EMBEDDING_MODEL_PATH 未配置，使用项目默认：%s", model_path)

        logger.info("Loading Embedding model: %s ...", model_path)
        self.embed_model = HuggingFaceEmbedding(model_name=model_path, trust_remote_code=True)

        self.vector_dim = 1024
        self.vector_store = MilvusVectorStore(
            uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}",
            collection_name="rag_collection",
            dim=self.vector_dim,
            overwrite=False,
        )

        self.text_splitter = SentenceSplitter(chunk_size=500, chunk_overlap=50)

    def ingest_document(self, document_id: int, content: str) -> None:
        db = SessionLocal()
        doc: Document | None = None
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                logger.error("Document %s not found", document_id)
                return

            doc.status = DocStatus.PARSING.value
            db.commit()

            text_chunks = self.text_splitter.split_text(content or "")
            logger.info("Document %s split into %s chunks.", document_id, len(text_chunks))

            nodes_for_milvus: list[TextNode] = []
            for i, text in enumerate(text_chunks):
                db_chunk = Chunk(
                    document_id=document_id,
                    content=text,
                    index=i,
                    is_active=True,
                    data_type="text",
                )
                db.add(db_chunk)
                db.flush()

                embedding = self.embed_model.get_text_embedding(text)
                nodes_for_milvus.append(
                    TextNode(
                        text=text,
                        id_=str(db_chunk.id),
                        embedding=embedding,
                        metadata={
                            "document_id": document_id,
                            "chunk_id": db_chunk.id,
                            "is_active": True,
                        },
                    )
                )
                db_chunk.vector_id = db_chunk.id

            if nodes_for_milvus:
                self.vector_store.add(nodes_for_milvus)

            doc.status = DocStatus.COMPLETED.value
            doc.chunk_count = len(text_chunks)
            db.commit()
        except Exception as exc:
            logger.error("Ingestion failed for doc %s: %s", document_id, exc)
            if doc is not None:
                doc.status = DocStatus.FAILED.value
                doc.error_msg = str(exc)
                db.commit()
            raise
        finally:
            db.close()

    def toggle_doc_status(self, document_id: int, is_active: bool) -> None:
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            doc.is_active = bool(is_active)
            chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
            for chunk in chunks:
                chunk.is_active = bool(is_active)
            db.commit()

            if not is_active:
                chunk_ids = [str(c.id) for c in chunks]
                if chunk_ids:
                    self.vector_store.delete_nodes(chunk_ids)
                return

            nodes_for_milvus: list[TextNode] = []
            for chunk in chunks:
                embedding = self.embed_model.get_text_embedding(chunk.content)
                nodes_for_milvus.append(
                    TextNode(
                        text=chunk.content,
                        id_=str(chunk.id),
                        embedding=embedding,
                        metadata={
                            "document_id": document_id,
                            "chunk_id": chunk.id,
                            "is_active": True,
                        },
                    )
                )
            if nodes_for_milvus:
                self.vector_store.add(nodes_for_milvus)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def update_doc_permission(self, document_id: int, visibility: str, group_ids: list[int] | None = None) -> None:
        """
        更新文档的可见性/用户组权限配置（当前仅更新 MySQL，Milvus 元数据同步暂未实现）。
        """
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            doc.visibility = visibility
            doc.authorized_group_ids = group_ids
            db.commit()

            logger.info(
                "Updated permission for document %s: visibility=%s groups=%s",
                document_id,
                visibility,
                group_ids,
            )
        except Exception as exc:
            db.rollback()
            logger.error("Error updating permission for doc %s: %s", document_id, exc)
            raise
        finally:
            db.close()


class RAGService:
    """RAG 对话服务（已接入 AB 实验）。

    当前版本主要做两件事：
    1. 调用 AB 实验路由，为每次对话分配版本（A/B/...）。
    2. 预留 RAG pipeline 的入口，后续可按版本切换不同配置。

    这里先用占位实现：不真正连向量库和大模型，只返回一个带有版本信息的答复，
    方便验证“RAG + AB 实验”的调用链是否跑通。
    """

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db
        self.ab_service = ABTestService(db)

    def _build_routing_vars_str(self, req: ChatRequest) -> str:
        """把和 RAG 相关的维度编码成 AB 路由变量串。

        示例结果："tenant_id=t1&scene=qa&kb_id=kb1&query_category=product_faq"
        """

        parts = []
        if req.tenant_id:
            parts.append(f"tenant_id={req.tenant_id}")
        if req.scene:
            parts.append(f"scene={req.scene}")
        if req.kb_id:
            parts.append(f"kb_id={req.kb_id}")
        if req.query_category:
            parts.append(f"query_category={req.query_category}")
        return "&".join(parts)

    def chat(self, req: ChatRequest) -> ChatResponse:
        """执行一次 RAG 对话，并接入 AB 实验分流。"""

        experiment_id = req.experiment_id or DEFAULT_RAG_EXPERIMENT_ID
        user_id = req.user_id or "anonymous"

        vars_str = self._build_routing_vars_str(req)

        route_res: Dict[str, Any] = self.ab_service.route(
            experiment_id=experiment_id,
            user_id=user_id,
            vars_str=vars_str,
        )
        version = route_res.get("version", "control")

        rag_config_key = f"{experiment_id}:{version}"
        answer = (
            f"【占位回复】已命中 AB 实验 {experiment_id} 的版本 {version}。"
            f"（config={rag_config_key}）\n\n你问的是：{req.query}"
        )

        try:
            self.ab_service.collect_metric(
                experiment_id=experiment_id,
                version=version,
                metric_name="REQUEST",
                metric_value=1.0,
                user_id=user_id,
            )
        except Exception:
            pass

        debug_info: Dict[str, Any] = {
            "routingVars": vars_str,
            "ragConfigKey": rag_config_key,
        }

        return ChatResponse(
            answer=answer,
            experiment_id=experiment_id,
            version=version,
            debug_info=debug_info,
        )


rag_service = RagService()
