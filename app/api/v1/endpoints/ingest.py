from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
import shutil
import tempfile
import os
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.rag.parsers.office_parser import WordParser, ExcelParser
from app.rag.parsers.pdf_parser import PdfParser
from app.services.storage_service import storage_service
from app.services.rag_service import rag_service
from app.core.database import get_db
from app.models.document import Document, DocStatus

router = APIRouter()

@router.post("/upload", summary="上传并解析文件")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    上传文件并解析为 Markdown。
    支持格式: .pdf, .docx, .xlsx, .csv, .png, .jpg, .jpeg
    """
    filename = file.filename
    extension = os.path.splitext(filename)[1].lower()
    
    parser = None
    if extension in [".pdf", ".png", ".jpg", ".jpeg"]:
        parser = PdfParser()
    elif extension == ".docx":
        parser = WordParser()
    elif extension in [".xlsx", ".xls", ".csv"]:
        parser = ExcelParser()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")
    
    # 1. 上传到 MinIO
    try:
        file_content = await file.read()
        
        # 计算 Hash 防重 (可选，这里简单做)
        file_hash = hashlib.md5(file_content).hexdigest()
        
        # 生成唯一的对象名: raw/YYYYMMDD/uuid_filename
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())
        object_name = f"raw/{date_str}/{unique_id}_{filename}"
        
        storage_service.upload_file(file_content, object_name, content_type=file.content_type)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload to storage failed: {str(e)}")
        
    try:
        # 2. 创建 Document 记录 (Pending 状态)
        new_doc = Document(
            filename=filename,
            file_path=object_name,
            file_hash=file_hash,
            status=DocStatus.PENDING
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        
        # 3. 调用对应的解析器
        if isinstance(parser, PdfParser):
            result = parser.parse(object_name)
        else:
            # 兼容旧逻辑
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            try:
                result = parser.parse(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        parsed_content = result["content"]
        
        # 4. 触发后台入库任务 (切分 + 向量化)
        # 注意：这里我们将解析后的文本直接传给后台任务
        # 如果文本非常大，也可以先存 MinIO 再传路径，但一般 Markdown 文本还好
        if parsed_content:
            background_tasks.add_task(rag_service.ingest_document, new_doc.id, parsed_content)
        else:
            # 如果解析为空，标记为失败或完成但无内容
            new_doc.status = DocStatus.COMPLETED
            new_doc.error_msg = "Parsed content is empty"
            db.commit()
        
        return {
            "document_id": new_doc.id,
            "filename": filename,
            "status": "processing", # 告诉前端正在处理中
            "storage_path": object_name,
            "parsed_content_preview": parsed_content[:200] + "..." if parsed_content else "",
            "meta": result.get("meta", {})
        }
    except Exception as e:
        # 如果出错，更新数据库状态
        if 'new_doc' in locals() and new_doc.id:
            new_doc.status = DocStatus.FAILED
            new_doc.error_msg = str(e)
            db.commit()
            
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

