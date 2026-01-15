import os
import requests
from typing import Dict, Any
from app.rag.parsers.base import BaseParser
from app.core.config import settings
from app.services.storage_service import storage_service

class PdfParser(BaseParser):
    """
    PDF 解析器 (通过 MinerU API)
    """
    
    def parse(self, file_path: str, **kwargs) -> Dict[str, Any]:
        # file_path 现在是 MinIO 中的 object_name
        # if not os.path.exists(file_path):
        #    raise FileNotFoundError(f"File not found: {file_path}")
            
        url = settings.MINERU_API_URL
        
        try:
            # 从 MinIO 获取文件流
            file_response = storage_service.get_file(file_path)
            
            # MinerU API requires the field name to be 'files'
            # file_response 是一个流，可以直接传给 requests
            # 我们需要给它一个文件名，requests 才能正确设置 Content-Type
            filename = os.path.basename(file_path)
            files = {'files': (filename, file_response)}
            
            # 假设 MinerU API 不需要额外的 headers 或 auth，如果有需要可以在这里添加
            response = requests.post(url, files=files, timeout=300) # 设置较长的超时时间，PDF解析可能很慢
            
            # 关闭流
            file_response.close()
            file_response.release_conn()
                
            response.raise_for_status()
            result = response.json()
            
            # MinerU API response structure:
            # {"backend":"pipeline","version":"...","results":{"filename_without_ext":{"md_content":"..."}}}
            # 注意：这里 filename 是我们传给 API 的文件名
            filename_no_ext = os.path.splitext(filename)[0]
            
            if "results" in result and filename_no_ext in result["results"]:
                markdown_content = result["results"][filename_no_ext].get("md_content", "")
                return {"content": markdown_content, "metadata": {"source": file_path, "parser": "MinerU"}}
            else:
                # Fallback or error handling if structure doesn't match
                print(f"Unexpected MinerU response structure: {result}")
                return {"content": "", "metadata": {"source": file_path, "error": "Parse failed or unexpected response"}}

            content = result.get("result", {}).get("markdown", "")
            if not content:
                 content = result.get("markdown", "")
            
            # 如果还是拿不到，尝试 dump 整个 result (调试用)
            if not content:
                content = str(result)

            return {
                "content": content,
                "images": [], # 暂时忽略图片，如果 API 返回图片 URL 可以加进来
                "meta": {"source": "mineru_api"}
            }
            
        except requests.RequestException as e:
            raise RuntimeError(f"MinerU API request failed: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"PDF parsing failed: {str(e)}")
