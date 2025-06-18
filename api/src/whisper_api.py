from multiprocessing import set_start_method
try:
    set_start_method("spawn", force=True)
except RuntimeError:
    # The start‑method is already set – safe to ignore.
    pass

import torch
import logging
from fastapi import FastAPI
from .routers.transcribe import router as transcribe_router
from .routers.convert import router as convert_router

# 设置日志配置
logging.basicConfig(level=logging.INFO)  # 设置日志级别为 INFO
logger = logging.getLogger(__name__)  # 获取当前模块的日志记录器

# 检测是否有 CUDA 可用
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"
logger.info(f"使用设备: {device}, 计算类型: {compute_type}")
logger.info("API server started on port http://localhost:8010")

app = FastAPI()

# 挂载路由
app.include_router(transcribe_router)
app.include_router(convert_router)

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "message": "API 服务运行正常"}
