import torch
from faster_whisper import WhisperModel
from fastapi import FastAPI, UploadFile, File
import tempfile
import os
import logging

# 設置日誌配置
logging.basicConfig(level=logging.INFO)  # 設置日誌級別為 INFO
logger = logging.getLogger(__name__)  # 獲取當前模塊的日誌記錄器

# 檢測是否有 CUDA 可用
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "int8"
logger.info(f"使用設備: {device}, 計算類型: {compute_type}")

# 初始化 Whisper 模型
model = WhisperModel("large-v3", device=device, compute_type=compute_type)

app = FastAPI()

def format_timestamp(seconds: float) -> str:
    """將秒數格式化為 SRT 格式的時間字符串（hh:mm:ss,mmm）"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)):
    logger.info("Received file: %s", file.filename)  # 記錄接收到的文件名

    # 暫存檔案
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio_path = temp_audio.name
        logger.info("Temporary file created at: %s", temp_audio_path)  # 記錄暫存文件路徑

    try:
        # 轉錄音頻
        segments, _ = model.transcribe(temp_audio_path)
        
        # 生成 SRT 格式
        srt_output = ""
        # 生成純文本格式
        txt_output = ""
        
        for i, segment in enumerate(segments, start=1):
            start_ts = format_timestamp(segment.start)
            end_ts = format_timestamp(segment.end)
            srt_output += f"{i}\n{start_ts} --> {end_ts}\n{segment.text.strip()}\n\n"
            txt_output += f"{segment.text.strip()} "
        
        # 整理純文本格式（去除多餘空格）
        txt_output = txt_output.strip()
        
        logger.info("Transcription completed successfully.")  # 記錄轉錄成功

    except Exception as e:
        logger.error("Error during transcription: %s", e)  # 記錄錯誤信息
        return {"error": "Transcription failed."}

    finally:
        # 刪除暫存文件
        os.remove(temp_audio_path)
        logger.info("Temporary file deleted: %s", temp_audio_path)  # 記錄暫存文件刪除

    return {"srt": srt_output, "txt": txt_output}

# 運行 FastAPI
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)