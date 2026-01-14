from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import StreamingResponse
from app.services.storage_service import storage_service
import mimetypes

router = APIRouter()

@router.get("/{file_path:path}", summary="获取文件")
async def get_file(file_path: str = Path(..., description="文件在存储中的路径")):
    """
    通过代理方式从 MinIO 获取文件。
    """
    try:
        # 从 MinIO 获取文件流
        # MinIO 的 get_object 返回的是 urllib3.response.HTTPResponse，它是一个流
        file_response = storage_service.get_file(file_path)
        
        # 猜测 MIME 类型
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = "application/octet-stream"
            
        return StreamingResponse(
            file_response, 
            media_type=content_type
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
