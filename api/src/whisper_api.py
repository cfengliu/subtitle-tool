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
        # 添加 word_timestamps=True 和其他參數來改善中文標點符號識別
        transcribe_options = {
            "word_timestamps": True,
            "vad_filter": True,
            "vad_parameters": dict(min_silence_duration_ms=500)
        }
        
        if language:
            segments, info = model.transcribe(temp_audio_path, language=language, **transcribe_options)
            detected_language = language
        else:
            segments, info = model.transcribe(temp_audio_path, **transcribe_options)
            detected_language = info.language
        
        logger.info("Detected/Used language: %s", detected_language)  # 記錄偵測到或使用的語言
        
        # 生成 SRT 格式
        srt_output = ""
        # 生成純文本格式
        txt_output = ""
        
        for i, segment in enumerate(segments, start=1):
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
