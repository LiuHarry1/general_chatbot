"""
健康检查API路由
包含服务状态和健康检查功能
"""
from datetime import datetime
from fastapi import APIRouter

from models import HealthResponse, StatusResponse, ServiceStatus
from utils.logger import app_logger

# 创建路由器
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="OK",
        timestamp=datetime.now().isoformat(),
        uptime="运行中"
    )


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """获取服务状态"""
    return StatusResponse(
        status="OK",
        timestamp=datetime.now().isoformat(),
        services=ServiceStatus(
            tongyi="Available",
            tavily="Available", 
            fileProcessing="Available",
            webAnalysis="Available"
        ),
        version="1.0.0"
    )
