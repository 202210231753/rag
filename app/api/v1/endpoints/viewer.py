# ✅【你的地盘】：数据查看接口
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
# from app.schemas.document_schema import DocumentResponse # 导入你定义的Schema
# from app.services.viewer_service import ViewerService    # 导入你写的业务类

router = APIRouter()

@router.get("/list", response_model=list)
def list_documents(
    skip: int = 0, 
    limit: int = 10, 
    db: Session = Depends(deps.get_db)
):
    """
    获取文件列表
    """
    # service = ViewerService(db)
    print("test")
    # return service.get_all(skip=skip, limit=limit)
    return ["test1","test2"]