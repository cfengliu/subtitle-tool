import torch
from faster_whisper import WhisperModel
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import Optional, Dict
import tempfile
import os
import logging
import uuid
import threading
import time
from multiprocessing import Process, Queue, Manager

# 設置日誌配置
logging.basicConfig(level=logging.INFO)  # 設置日誌級別為 INFO
logger = logging.getLogger(__name__)  # 獲取當前模塊的日誌記錄器

# 檢測是否有 CUDA 可用
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"
logger.info(f"使用設備: {device}, 計算類型: {compute_type}")
logger.info("API server started on port http://localhost:8010")

# 初始化 Whisper 模型
model = WhisperModel("large-v3", device=device, compute_type=compute_type)

app = FastAPI()

# 任務管理
active_tasks: Dict[str, Dict] = {}  # 存儲活躍的轉錄任務
task_results: Dict[str, Dict] = {}  # 存儲完成的任務結果

class TranscriptionTask:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.status = "running"
        self.progress = 0
        self.process = None  # 存儲進程對象
        
    def cancel(self):
        """強制終止轉錄進程"""
        if self.process and self.process.is_alive():
            logger.info(f"Terminating process for task {self.task_id}")
            self.process.terminate()  # 發送 SIGTERM
            time.sleep(1)  # 等待進程優雅退出
            
            if self.process.is_alive():
                logger.info(f"Force killing process for task {self.task_id}")
                self.process.kill()  # 強制殺死進程 SIGKILL
                
            self.process.join(timeout=5)  # 等待進程結束
        self.status = "cancelled"
        
    def is_cancelled(self):
        return self.status == "cancelled"

def format_timestamp(seconds: float) -> str:
    """將秒數格式化為 SRT 格式的時間字符串（hh:mm:ss,mmm）"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

def add_chinese_punctuation(text: str, language: str) -> str:
    """為中文文本添加基本標點符號"""
    if not text or language not in ['zh', 'chinese']:
        return text
    
    import re
    
    # 移除多餘空格
    text = re.sub(r'\s+', '', text.strip())
    
    # 如果文本已經有足夠的標點符號，直接返回
    punctuation_count = len(re.findall(r'[。！？，、；：]', text))
    text_length = len(text)
    if punctuation_count > 0 and (punctuation_count / text_length) > 0.05:
        return text
    
    # 基本的中文標點符號規則
    # 在語氣詞後添加逗號
    text = re.sub(r'(吧|呢|啊|哦|嗯|唉|哎|的話)(?![。！？，、；：])', r'\1，', text)
    
    # 在疑問詞後添加問號
    text = re.sub(r'(什麼|為什麼|怎麼|哪裡|哪兒|誰|何時|如何|是否|嗎|呢)(?![。！？，、；：])', r'\1？', text)
    
    # 在感嘆詞後添加感嘆號
    text = re.sub(r'(太好了|真的|不可能|天啊|哇|太棒了|amazing|wonderful)(?![。！？，、；：])', r'\1！', text)
    
    # 在連接詞後添加逗號
    text = re.sub(r'(然後|接著|之後|但是|不過|而且|另外|所以|因此|因為|由於)(?![。！？，、；：])', r'\1，', text)
    
    # 處理長句子，每15-20個字符添加逗號
    if len(text) > 20:
        # 在適當位置添加逗號分隔長句
        sentences = []
        current_sentence = ""
        for char in text:
            current_sentence += char
            if len(current_sentence) >= 15 and char in '的了在是有':
                current_sentence += '，'
                sentences.append(current_sentence)
                current_sentence = ""
        if current_sentence:
            sentences.append(current_sentence)
        text = ''.join(sentences)
    
    # 在句子結尾添加句號（如果沒有其他標點）
    if not re.search(r'[。！？]$', text):
        text += '。'
    
    # 清理重複的標點符號
    text = re.sub(r'([。！？，、；：])\1+', r'\1', text)
    
    return text

def transcribe_worker(audio_path: str, language: Optional[str], result_queue: Queue, progress_dict: dict, task_id: str):
    """在獨立進程中執行轉錄的工作函數"""
    try:
        # 在子進程中重新初始化模型
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        worker_model = WhisperModel("large-v3", device=device, compute_type=compute_type)
        
        # 轉錄音頻
        transcribe_options = {
            "word_timestamps": True,
            "vad_filter": True,
            "vad_parameters": dict(min_silence_duration_ms=500)
        }
        
        if language:
            segments, info = worker_model.transcribe(audio_path, language=language, **transcribe_options)
            detected_language = language
        else:
            segments, info = worker_model.transcribe(audio_path, **transcribe_options)
            detected_language = info.language
        
        # 生成 SRT 格式
        srt_output = ""
        # 生成純文本格式
        txt_output = ""
        
        segments_list = list(segments)
        total_segments = len(segments_list)
        
        for i, segment in enumerate(segments_list, start=1):
            # 更新進度
            progress_dict[task_id] = int((i / total_segments) * 100)
            
            start_ts = format_timestamp(segment.start)
            end_ts = format_timestamp(segment.end)
            
            # 處理每個片段的文本，添加標點符號
            segment_text = segment.text.strip()
            if detected_language == 'zh':
                segment_text = add_chinese_punctuation(segment_text, detected_language)
            
            srt_output += f"{i}\n{start_ts} --> {end_ts}\n{segment_text}\n\n"
            txt_output += f"{segment_text} "
        
        # 整理純文本格式（去除多餘空格）
        txt_output = txt_output.strip()
        
        # 對整個文本再次處理標點符號
        if detected_language == 'zh':
            txt_output = add_chinese_punctuation(txt_output, detected_language)
        
        # 設置最終進度
        progress_dict[task_id] = 100
        
        # 返回結果
        result = {
            "srt": srt_output, 
            "txt": txt_output,
            "detected_language": detected_language,
            "status": "completed"
        }
        result_queue.put(result)
        
    except Exception as e:
        logger.error("Error during transcription: %s", e)
        error_result = {"error": "Transcription failed.", "status": "error"}
        result_queue.put(error_result)

@app.post("/transcribe/")
async def start_transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """啟動轉錄任務，返回任務ID"""
    task_id = str(uuid.uuid4())
    logger.info(f"Starting transcription task {task_id} for file: {file.filename}")
    
    if language:
        logger.info("Language specified: %s", language)
    else:
        logger.info("No language specified, will auto-detect")

    # 暫存檔案
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio_path = temp_audio.name
        logger.info("Temporary file created at: %s", temp_audio_path)

    # 創建任務
    task = TranscriptionTask(task_id)
    
    # 創建進程間通信對象
    result_queue = Queue()
    manager = Manager()
    progress_dict = manager.dict()
    progress_dict[task_id] = 0
    
    # 創建並啟動轉錄進程
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
    
    # 在後台線程中監控進程
    def monitor_process():
        try:
            process.join()  # 等待進程完成
            
            if not result_queue.empty():
                result = result_queue.get()
                if result.get("status") == "completed":
                    task_results[task_id] = result
                    task.status = "completed"
                else:
                    task.status = "error"
            else:
                # 進程被終止
                task.status = "cancelled"
                
        except Exception as e:
            logger.error(f"Error monitoring process for task {task_id}: {e}")
            task.status = "error"
        finally:
            # 清理暫存文件
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)
                logger.info("Temporary file deleted: %s", temp_audio_path)
            # 從活躍任務中移除
            if task_id in active_tasks:
                del active_tasks[task_id]
    
    monitor_thread = threading.Thread(target=monitor_process)
    monitor_thread.start()
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "轉錄任務已啟動"
    }

@app.post("/transcribe/{task_id}/cancel")
async def cancel_transcribe_task(task_id: str):
    """強制取消指定的轉錄任務"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="任務不存在或已完成")
    
    task_info = active_tasks[task_id]
    task = task_info["task"]
    
    logger.info(f"Force cancelling task {task_id}")
    task.cancel()  # 這會強制終止進程
    
    return {
        "task_id": task_id,
        "status": "cancelled",
        "message": "任務已被強制終止"
    }

@app.get("/transcribe/{task_id}/status")
async def get_task_status(task_id: str):
    """獲取任務狀態"""
    # 檢查活躍任務
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
    
    # 檢查已完成任務
    if task_id in task_results:
        return {
            "task_id": task_id,
            "status": "completed",
            "progress": 100
        }
    
    raise HTTPException(status_code=404, detail="任務不存在")

@app.get("/transcribe/{task_id}/result")
async def get_task_result(task_id: str):
    """獲取任務結果"""
    if task_id not in task_results:
        if task_id in active_tasks:
            task = active_tasks[task_id]["task"]
            if task.status == "running":
                raise HTTPException(status_code=202, detail="任務仍在進行中")
            elif task.status == "cancelled":
                raise HTTPException(status_code=410, detail="任務已被取消")
            else:
                raise HTTPException(status_code=500, detail="任務執行失敗")
        else:
            raise HTTPException(status_code=404, detail="任務不存在")
    
    result = task_results[task_id]
    # 返回結果後清理
    del task_results[task_id]
    
    return result

@app.get("/transcribe/tasks")
async def list_active_tasks():
    """列出所有活躍任務"""
    tasks = []
    for task_id, task_info in active_tasks.items():
        task = task_info["task"]
        tasks.append({
            "task_id": task_id,
            "status": task.status,
            "progress": task.progress,
            "filename": task_info["filename"]
        })
    return {"active_tasks": tasks}

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "message": "API 服務運行正常"}
