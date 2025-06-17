import torch
from faster_whisper import WhisperModel
from fastapi import FastAPI, UploadFile, File, Form
from typing import Optional
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
logger.info("API server started on port http://localhost:8010")

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
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    logger.info("Received file: %s", file.filename)  # 記錄接收到的文件名
    if language:
        logger.info("Language specified: %s", language)  # 記錄指定的語言
    else:
        logger.info("No language specified, will auto-detect")  # 記錄將自動偵測語言

    # 暫存檔案
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio_path = temp_audio.name
        logger.info("Temporary file created at: %s", temp_audio_path)  # 記錄暫存文件路徑

    try:
        # 轉錄音頻，如果有指定語言就使用，否則自動偵測
        if language:
            segments, info = model.transcribe(temp_audio_path, language=language)
            detected_language = language
        else:
            segments, info = model.transcribe(temp_audio_path)
            detected_language = info.language
        
        logger.info("Detected/Used language: %s", detected_language)  # 記錄偵測到或使用的語言
        
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

    return {
        "srt": srt_output, 
        "txt": txt_output,
        "detected_language": detected_language
    }

@app.get("/languages")
async def get_supported_languages():
    """獲取支持的語言列表"""
    # Whisper 支持的語言代碼
    supported_languages = {
        "zh": "Chinese",
        "en": "English", 
        "ja": "Japanese",
        "ko": "Korean",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ar": "Arabic",
        "hi": "Hindi",
        "th": "Thai",
        "vi": "Vietnamese",
        "tr": "Turkish",
        "pl": "Polish",
        "nl": "Dutch",
        "sv": "Swedish",
        "da": "Danish",
        "no": "Norwegian",
        "fi": "Finnish",
        "hu": "Hungarian",
        "cs": "Czech",
        "sk": "Slovak",
        "hr": "Croatian",
        "bg": "Bulgarian",
        "ro": "Romanian",
        "uk": "Ukrainian",
        "he": "Hebrew",
        "fa": "Persian",
        "ur": "Urdu",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
        "ml": "Malayalam",
        "kn": "Kannada",
        "gu": "Gujarati",
        "pa": "Punjabi",
        "mr": "Marathi",
        "ne": "Nepali",
        "si": "Sinhala",
        "my": "Myanmar",
        "km": "Khmer",
        "lo": "Lao",
        "ka": "Georgian",
        "am": "Amharic",
        "is": "Icelandic",
        "lv": "Latvian",
        "lt": "Lithuanian",
        "et": "Estonian",
        "mt": "Maltese",
        "cy": "Welsh",
        "ga": "Irish",
        "eu": "Basque",
        "ca": "Catalan",
        "gl": "Galician",
        "ast": "Asturian",
        "az": "Azerbaijani",
        "be": "Belarusian",
        "bs": "Bosnian",
        "br": "Breton",
        "mk": "Macedonian",
        "mg": "Malagasy",
        "ms": "Malay",
        "sl": "Slovenian",
        "sq": "Albanian",
        "sw": "Swahili",
        "tl": "Tagalog",
        "tt": "Tatar",
        "yo": "Yoruba",
        "zu": "Zulu"
    }
    return {
        "supported_languages": supported_languages,
        "note": "使用語言代碼（如 'zh' 代表中文，'en' 代表英文）。如果不指定語言，系統將自動偵測。"
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {"status": "healthy", "message": "API 服務運行正常"}
