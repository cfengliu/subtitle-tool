from multiprocessing import Process, Queue, Manager
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from typing import Optional, Dict
import tempfile
import os
import logging
import uuid
import threading
from threading import Semaphore
import time
from ..workers.convert_worker import convert_worker
from ..utils.ffmpeg_utils import get_supported_formats
from urllib.parse import quote
import re

# 设置日志配置
logger = logging.getLogger(__name__)

# 并发控制配置 — 使用信号量限制同时进行的转换任务数量
MAX_CONCURRENT_CONVERT_TASKS = int(os.getenv("MAX_CONCURRENT_CONVERT_TASKS", "2"))
convert_semaphore = Semaphore(MAX_CONCURRENT_CONVERT_TASKS)

# 任务管理
active_convert_tasks: Dict[str, Dict] = {}  # 存储活跃的转换任务
convert_results: Dict[str, Dict] = {}  # 存储完成的任务结果

router = APIRouter(prefix="/convert", tags=["convert"])

class ConversionTask:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = "running"
        self.progress = 0
        self.process = None  # 存储进程对象
        
    def cancel(self):
        """强制终止转换进程"""
        if self.process and self.process.is_alive():
            logger.info(f"Terminating process for conversion task {self.task_id}")
            self.process.terminate()  # 发送 SIGTERM
            time.sleep(1)  # 等待进程优雅退出
            
            if self.process.is_alive():
                logger.info(f"Force killing process for conversion task {self.task_id}")
                self.process.kill()  # 强制杀死进程 SIGKILL
                
            self.process.join(timeout=5)  # 等待进程结束
        self.status = "cancelled"
        
    def is_cancelled(self):
        return self.status == "cancelled"

@router.post("/", 
    responses={
        200: {
            "description": "转换任务成功启动",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "started",
                        "message": "视频转音频任务已启动"
                    }
                }
            }
        },
        429: {
            "description": "同时转换任务数量超过限制",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Too many concurrent conversion requests. Please try again later."
                    }
                }
            }
        }
    }
)
async def start_video_to_audio_conversion(
    file: UploadFile = File(...),
    format: str = Form("mp3"),
    quality: str = Form("medium")
):
    """启动视频转音频任务，返回任务ID"""
    # 验证格式参数
    supported_formats = get_supported_formats()
    if format not in supported_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Supported formats: {', '.join(supported_formats)}"
        )
    
    # 验证质量参数
    if quality not in ['high', 'medium', 'low']:
        raise HTTPException(
            status_code=400,
            detail="Quality must be one of: high, medium, low"
        )
    
    # 并发控制：若已达到上限则立即拒绝请求
    if not convert_semaphore.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent conversion requests. Please try again later."
        )

    task_id = str(uuid.uuid4())
    logger.info(f"Starting conversion task {task_id} for file: {file.filename}")
    logger.info(f"Format: {format}, Quality: {quality}")

    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("video/"):
        convert_semaphore.release()
        raise HTTPException(
            status_code=400,
            detail="Please upload a video file"
        )

    # 暂存文件
    file_extension = os.path.splitext(file.filename or "video")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_video:
        temp_video.write(await file.read())
        temp_video_path = temp_video.name
        logger.info(f"Temporary video file created at: {temp_video_path}")

    # 创建任务
    task = ConversionTask(task_id)
    
    # 创建进程间通信对象
    result_queue = Queue()
    manager = Manager()
    progress_dict = manager.dict()
    progress_dict[task_id] = 0
    
    # 创建并启动转换进程
    process = Process(
        target=convert_worker,
        args=(temp_video_path, format, quality, result_queue, progress_dict, task_id)
    )
    process.start()
    task.process = process
    
    active_convert_tasks[task_id] = {
        "task": task,
        "temp_file": temp_video_path,
        "filename": file.filename,
        "format": format,
        "quality": quality,
        "process": process,
        "result_queue": result_queue,
        "progress_dict": progress_dict
    }
    
    # 在后台线程中监控进程
    def monitor_process():
        import time
        logger.info(f"MONITOR: Entering monitor_process function for task {task_id}")
        try:
            logger.info(f"MONITOR: Monitor thread started for conversion task {task_id}")
            logger.info(f"MONITOR: Process PID: {process.pid}, is_alive: {process.is_alive()}")
            
            # 簡化監控邏輯 - 直接使用 join 但加上超時
            logger.info(f"Waiting for process {task_id} to complete...")
            process.join(timeout=300)  # 最多等待5分鐘
            
            logger.info(f"Process join completed for task {task_id}")
            logger.info(f"Process is_alive: {process.is_alive()}, exit code: {process.exitcode}")
            
            # 如果進程還活著，說明超時了
            if process.is_alive():
                logger.error(f"Process {task_id} timed out, terminating...")
                process.terminate()
                time.sleep(1)
                if process.is_alive():
                    process.kill()
                task.status = "error"
                convert_results[task_id] = {
                    "status": "error",
                    "error": "Process timed out"
                }
                return
            
            # 給時間讓結果進入隊列
            logger.info(f"Waiting for result in queue for task {task_id}...")
            time.sleep(1.0)
            
            try:
                # 嘗試從隊列獲取結果
                result = result_queue.get(timeout=5.0)
                logger.info(f"Got result from queue for task {task_id}: status={result.get('status')}")
                
                if result.get("status") == "completed":
                    # 讀取音頻文件內容
                    output_path = result.get("output_path")
                    if output_path and os.path.exists(output_path):
                        try:
                            with open(output_path, "rb") as f:
                                audio_data = f.read()
                            
                            logger.info(f"Audio data read successfully, size: {len(audio_data)} bytes")
                            
                            # 將音頻數據添加到結果中
                            result["audio_data"] = audio_data
                            # 新增：將原始檔名存進結果
                            result["filename"] = active_convert_tasks[task_id]["filename"]
                            
                            # 清理臨時輸出文件
                            os.remove(output_path)
                            logger.info(f"Temporary output file deleted: {output_path}")
                            
                        except Exception as file_error:
                            logger.error(f"Failed to read or delete output file {output_path}: {file_error}")
                            result = {
                                "status": "error",
                                "error": f"Failed to read output file: {file_error}"
                            }
                    else:
                        logger.error(f"Output file not found: {output_path}")
                        result = {
                            "status": "error", 
                            "error": "Output file not found"
                        }
                    
                    if result.get("status") == "completed":
                        convert_results[task_id] = result
                        task.status = "completed"
                        logger.info(f"Task {task_id} completed successfully")
                    else:
                        task.status = "error"
                        convert_results[task_id] = result
                        logger.error(f"Task {task_id} failed during file reading")
                else:
                    task.status = "error"
                    convert_results[task_id] = result
                    logger.error(f"Task {task_id} failed: {result.get('error', 'Unknown error')}")
                
                # 清理隊列資源
                try:
                    result_queue.close()
                    result_queue.cancel_join_thread()
                    logger.info(f"Result queue cleaned up for task {task_id}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup result queue for task {task_id}: {cleanup_error}")
                    
            except Exception as queue_error:
                logger.warning(f"Failed to get result from queue for task {task_id}: {queue_error}")
                logger.warning(f"Process exit code: {process.exitcode}")
                
                # 即使沒有從隊列獲取到結果，也要設置狀態
                task.status = "error" if process.exitcode == 0 else "cancelled"
                convert_results[task_id] = {
                    "status": "error",
                    "error": f"Process completed with exit code {process.exitcode}, but failed to get result from queue: {queue_error}"
                }
                
        except Exception as e:
            logger.error(f"Error in monitor thread for task {task_id}: {e}", exc_info=True)
            task.status = "error"
            convert_results[task_id] = {
                "status": "error", 
                "error": f"Monitor thread error: {str(e)}"
            }
        finally:
            # 清理可能遺留的輸出文件
            try:
                if 'output_path' in locals() and output_path and os.path.exists(output_path):
                    os.remove(output_path)
                    logger.info(f"Cleanup: Temporary output file deleted: {output_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup output file {output_path}: {cleanup_error}")
            
            # 释放一个并发名额
            convert_semaphore.release()
            # 清理暂存文件
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
                logger.info(f"Temporary video file deleted: {temp_video_path}")
            # 从活跃任务中移除
            if task_id in active_convert_tasks:
                del active_convert_tasks[task_id]
    
    monitor_thread = threading.Thread(target=monitor_process)
    monitor_thread.daemon = True  # 設置為守護線程
    monitor_thread.start()
    logger.info(f"Monitor thread started with ID: {monitor_thread.ident} for task {task_id}")
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "视频转音频任务已启动"
    }

@router.post("/{task_id}/cancel",
    responses={
        200: {
            "description": "任务取消成功",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "cancelled",
                        "message": "转换任务已被强制终止"
                    }
                }
            }
        },
        404: {
            "description": "任务不存在或已完成",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "任务不存在或已完成"
                    }
                }
            }
        }
    }
)
async def cancel_conversion_task(task_id: str):
    """强制取消指定的转换任务"""
    if task_id not in active_convert_tasks:
        raise HTTPException(status_code=404, detail="任务不存在或已完成")
    
    task_info = active_convert_tasks[task_id]
    task = task_info["task"]
    
    # 取消任务
    task.cancel()
    logger.info(f"Conversion task {task_id} has been cancelled")
    
    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "转换任务已被强制终止"
    }

@router.get("/{task_id}/status",
    responses={
        200: {
            "description": "成功获取任务状态",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "running",
                        "progress": 45,
                        "filename": "video.mp4",
                        "format": "mp3",
                        "quality": "medium"
                    }
                }
            }
        },
        404: {
            "description": "任务不存在",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "任务不存在"
                    }
                }
            }
        }
    }
)
async def get_conversion_status(task_id: str):
    """获取转换任务状态"""
    # 检查活跃任务
    if task_id in active_convert_tasks:
        task_info = active_convert_tasks[task_id]
        task = task_info["task"]
        progress_dict = task_info["progress_dict"]
        
        current_progress = progress_dict.get(task_id, 0)
        
        return {
            "task_id": task_id,
            "status": task.status,
            "progress": current_progress,
            "filename": task_info["filename"],
            "format": task_info["format"],
            "quality": task_info["quality"]
        }
    
    # 检查已完成任务
    if task_id in convert_results:
        result = convert_results[task_id]
        return {
            "task_id": task_id,
            "status": result.get("status", "completed"),
            "progress": 100,
            "format": result.get("format"),
            "quality": result.get("quality"),
            "file_size": result.get("file_size")
        }
    
    raise HTTPException(status_code=404, detail="任务不存在")

@router.get("/{task_id}/result",
    responses={
        200: {
            "description": "成功获取转换结果",
            "content": {
                "audio/mpeg": {},
                "audio/wav": {},
                "audio/ogg": {},
                "audio/aac": {}
            }
        },
        202: {
            "description": "任务仍在进行中",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "任务仍在进行中"
                    }
                }
            }
        },
        404: {
            "description": "任务不存在",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "任务不存在"
                    }
                }
            }
        },
        410: {
            "description": "任务已被取消",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "任务已被取消"
                    }
                }
            }
        },
        500: {
            "description": "任务执行失败",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "任务执行失败"
                    }
                }
            }
        }
    }
)
async def get_conversion_result(task_id: str):
    """获取转换任务结果"""
    logger.info(f"Getting result for task {task_id}")
    logger.info(f"Active tasks: {list(active_convert_tasks.keys())}")
    logger.info(f"Completed results: {list(convert_results.keys())}")
    
    # 检查活跃任务
    if task_id in active_convert_tasks:
        task_info = active_convert_tasks[task_id]
        task = task_info["task"]
        
        logger.info(f"Task {task_id} found in active tasks, status: {task.status}")
        
        if task.is_cancelled():
            raise HTTPException(status_code=410, detail="任务已被取消")
        else:
            raise HTTPException(status_code=202, detail="任务仍在进行中")
    
    # 检查已完成任务
    if task_id in convert_results:
        result = convert_results[task_id]
        
        if result.get("status") == "completed":
            audio_data = result.get("audio_data")
            format = result.get("format", "mp3")
            
            # 设置正确的MIME类型
            mime_types = {
                "mp3": "audio/mpeg",
                "wav": "audio/wav", 
                "ogg": "audio/ogg",
                "aac": "audio/aac"
            }
            
            mime_type = mime_types.get(format, "audio/mpeg")
            
            # 設置檔名，優先用 result["filename"]
            filename = result.get("filename", f"converted_audio.{format}")
            import os
            base, ext = os.path.splitext(filename)
            if not ext or ext[1:] != format:
                filename = f"{base}.{format}"
            # 前面加上 converted_
            filename = f"converted_{filename}"
            # 產生 ASCII-only 的 fallback filename
            def ascii_filename(filename, fallback="file"):
                return re.sub(r'[^A-Za-z0-9_.-]', '_', filename) or fallback
            ascii_name = ascii_filename(filename)
            quoted_filename = quote(filename)
            return Response(
                content=audio_data,
                media_type=mime_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{ascii_name}"; filename*=UTF-8''{quoted_filename}',
                    "Content-Length": str(len(audio_data))
                }
            )
        else:
            error_message = result.get("error", "任务执行失败")
            raise HTTPException(status_code=500, detail=error_message)
    
    raise HTTPException(status_code=404, detail="任务不存在")

@router.get("/tasks")
async def list_active_conversion_tasks():
    """列出所有活跃的转换任务"""
    tasks = []
    for task_id, task_info in active_convert_tasks.items():
        task = task_info["task"]
        progress_dict = task_info["progress_dict"]
        
        tasks.append({
            "task_id": task_id,
            "status": task.status,
            "progress": progress_dict.get(task_id, 0),
            "filename": task_info["filename"],
            "format": task_info["format"],
            "quality": task_info["quality"]
        })
    
    return {"active_tasks": tasks, "count": len(tasks)}

@router.get("/formats")
async def get_supported_audio_formats():
    """获取支持的音频格式列表"""
    formats = get_supported_formats()
    return {
        "supported_formats": formats,
        "default_format": "mp3",
        "quality_options": ["high", "medium", "low"]
    }

