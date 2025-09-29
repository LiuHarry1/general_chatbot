"""
图片服务API
提供图片文件的访问接口
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from utils.logger import app_logger

router = APIRouter()

@router.get("/{file_path:path}")
async def get_image(file_path: str):
    """获取图片文件"""
    try:
        # 构建图片文件路径
        images_dir = os.path.join(os.path.dirname(__file__), "..", "..", "images")
        image_file = os.path.join(images_dir, file_path)
        
        # 安全检查：确保文件在images目录内
        images_dir = os.path.abspath(images_dir)
        image_file = os.path.abspath(image_file)
        
        if not image_file.startswith(images_dir):
            raise HTTPException(status_code=403, detail="访问被拒绝")
        
        # 检查文件是否存在
        if not os.path.exists(image_file):
            raise HTTPException(status_code=404, detail="图片不存在")
        
        # 检查是否为图片文件
        if not file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        app_logger.info(f"提供图片文件: {file_path}")
        
        # 返回文件
        return FileResponse(
            path=image_file,
            media_type="image/png" if file_path.lower().endswith('.png') else "image/jpeg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取图片失败: {e}")
        raise HTTPException(status_code=500, detail="获取图片失败")
