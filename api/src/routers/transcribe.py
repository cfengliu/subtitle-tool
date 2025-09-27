from multiprocessing import Process, Queue, Manager
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import tempfile
import os
import logging
import uuid
import threading
from threading import Semaphore
import time
from ..workers.transcribe_worker import transcribe_worker
from ..utils.text_conversion import convert_to_traditional_chinese

# 设置日志配置
logger = logging.getLogger(__name__)

# 并发控制配置 — 使用信号量限制同时进行的转录任务数量
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))  # 可通过环境变量修改
concurrent_semaphore = Semaphore(MAX_CONCURRENT_TASKS)

# 任务管理
active_tasks: Dict[str, Dict] = {}  # 存储活跃的转录任务
task_results: Dict[str, Dict] = {}  # 存储完成的任务结果

router = APIRouter(prefix="/transcribe", tags=["transcribe"])

class TranscriptionTask:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = "running"
        self.progress = 0
        self.process = None  # 存储进程对象
        
    def cancel(self):
        """强制终止转录进程"""
        if self.process and self.process.is_alive():
            logger.info(f"Terminating process for task {self.task_id}")
            self.process.terminate()  # 发送 SIGTERM
            time.sleep(1)  # 等待进程优雅退出
            
            if self.process.is_alive():
                logger.info(f"Force killing process for task {self.task_id}")
                self.process.kill()  # 强制杀死进程 SIGKILL
                
            self.process.join(timeout=5)  # 等待进程结束
        self.status = "cancelled"
        
    def is_cancelled(self):
        return self.status == "cancelled"


class ConvertToTraditionalRequest(BaseModel):
    txt: Optional[str] = None
    srt: Optional[str] = None


class ConvertToTraditionalResponse(BaseModel):
    txt: Optional[str] = None
    srt: Optional[str] = None

@router.post("/", 
    responses={
        200: {
            "description": "转录任务成功启动",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "started",
                        "message": "转录任务已启动"
                    }
                }
            }
        },
        429: {
            "description": "同时转录任务数量超过限制",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Too many concurrent transcription requests. Please try again later."
                    }
                }
            }
        }
    }
)
async def start_transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """启动转录任务，返回任务ID"""
    # 并发控制：若已达到上限则立即拒绝请求
    if not concurrent_semaphore.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent transcription requests. Please try again later."
        )

    task_id = str(uuid.uuid4())
    logger.info(f"Starting transcription task {task_id} for file: {file.filename}")
    
    if language:
        logger.info("Language specified: %s", language)
    else:
        logger.info("No language specified, will auto-detect")

    # 暂存文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio_path = temp_audio.name
        logger.info("Temporary file created at: %s", temp_audio_path)

    # 创建任务
    task = TranscriptionTask(task_id)
    
    # 创建进程间通信对象
    result_queue = Queue()
    manager = Manager()
    progress_dict = manager.dict()
    progress_dict[task_id] = 0
    
    # 创建并启动转录进程
    process = Process(
        target=transcribe_worker,
        args=(temp_audio_path, language, result_queue, progress_dict, task_id)
    )
    process.start()
    task.process = process
    
    active_tasks[task_id] = {
        "task": task,
        "temp_file": temp_audio_path,
        "filename": file.filename,
        "process": process,
        "result_queue": result_queue,
        "progress_dict": progress_dict
    }
    
    # 在后台线程中监控进程
    def monitor_process():
        """Monitor the child process in a background thread and read the Queue early to avoid deadlock when sending large results."""
        try:
            result = None

            # Wait for data to appear in the result_queue. The worker puts the
            # result before exiting. If the payload is large (e.g. subtitles for
            # a one-hour audio file) and the parent never consumes it, the child
            # can block on Queue.put(), which in turn makes process.join()
            # block forever, leaving the task stuck at 100% progress.
            while True:
                if not result_queue.empty():
                    result = result_queue.get()
                    break

                # If the child process has already terminated, break the loop.
                if not process.is_alive():
                    break

                # Avoid busy-waiting.
                time.sleep(0.5)

            # Wait for the child process to fully terminate.
            process.join()

            if result:
                if result.get("status") == "completed":
                    task_results[task_id] = result
                    task.status = "completed"
                else:
                    task.status = "error"
            else:
                # If there is no result and the child process has terminated,
                # treat the task as cancelled or errored.
                task.status = "cancelled" if task.is_cancelled() else "error"
        except Exception as e:
            logger.error(f"Error monitoring process for task {task_id}: {e}")
            task.status = "error"
        finally:
            # Release one concurrency slot.
            concurrent_semaphore.release()

            # Clean up the temporary file.
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
                logger.info("Temporary file deleted: %s", temp_audio_path)

            # Remove the task from the active_tasks dict.
            active_tasks.pop(task_id, None)
    
    monitor_thread = threading.Thread(target=monitor_process)
    monitor_thread.start()
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "转录任务已启动"
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
                        "message": "任务已被强制终止"
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
async def cancel_transcribe_task(task_id: str):
    """强制取消指定的转录任务"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="任务不存在或已完成")
    
    task_info = active_tasks[task_id]
    task = task_info["task"]
    
    logger.info(f"Force cancelling task {task_id}")
    task.cancel()  # 这会强制终止进程
    
    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "任务已被强制终止"
    }


@router.post(
    "/convert-traditional",
    response_model=ConvertToTraditionalResponse,
    responses={
        200: {
            "description": "文本已成功转换为繁体中文",
            "content": {
                "application/json": {
                    "example": {
                        "txt": "繁體中文內容",
                        "srt": "1\\n00:00:00,000 --> 00:00:02,000\\n繁體字幕內容"
                    }
                }
            }
        },
        400: {
            "description": "缺少需要转换的文本内容",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "No text provided for conversion"
                    }
                }
            }
        }
    }
)
async def convert_transcription_to_traditional(payload: ConvertToTraditionalRequest):
    """Convert transcription payload to traditional Chinese."""

    if payload.txt is None and payload.srt is None:
        raise HTTPException(status_code=400, detail="No text provided for conversion")

    converted_txt = convert_to_traditional_chinese(payload.txt) if payload.txt is not None else None
    converted_srt = convert_to_traditional_chinese(payload.srt) if payload.srt is not None else None

    return ConvertToTraditionalResponse(txt=converted_txt, srt=converted_srt)

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
                        "filename": "audio.mp3"
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
async def get_task_status(task_id: str):
    """获取任务状态"""
    # 检查活跃任务
    if task_id in active_tasks:
        task = active_tasks[task_id]["task"]
        progress_dict = active_tasks[task_id]["progress_dict"]
        current_progress = progress_dict.get(task_id, 0)
        
        return {
            "task_id": task_id,
            "status": task.status,
            "progress": current_progress,
            "filename": active_tasks[task_id]["filename"]
        }
    
    # 检查已完成任务
    if task_id in task_results:
        return {
            "task_id": task_id,
            "status": "completed",
            "progress": 100
        }
    
    raise HTTPException(status_code=404, detail="任务不存在")

@router.get("/{task_id}/result",
    responses={
        200: {
            "description": "成功获取任务结果",
            "content": {
                "application/json": {
                    "example": {
                        "srt": "1\n00:00:00,000 --> 00:00:05,000\n你好，这是测试文字。\n\n",
                        "txt": "你好，这是测试文字。",
                        "detected_language": "zh",
                        "status": "completed"
                    }
                }
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
async def get_task_result(task_id: str):
    """获取任务结果"""
    if task_id not in task_results:
        if task_id in active_tasks:
            task = active_tasks[task_id]["task"]
            if task.status == "running":
                raise HTTPException(status_code=202, detail="任务仍在进行中")
            elif task.status == "cancelled":
                raise HTTPException(status_code=410, detail="任务已被取消")
            else:
                raise HTTPException(status_code=500, detail="任务执行失败")
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
    
    result = task_results[task_id]
    # 返回结果后清理
    del task_results[task_id]
    
    return result

@router.get("/tasks")
async def list_active_tasks():
    """列出所有活跃任务"""
    tasks = []
    for task_id, task_info in active_tasks.items():
        task = task_info["task"]
        tasks.append({
            "task_id": task_id,
            "status": task.status,
            "progress": active_tasks[task_id]["progress_dict"].get(task_id, 0),
            "filename": task_info["filename"]
        })
    return {"active_tasks": tasks} 
