from multiprocessing import Queue
import torch
from faster_whisper import WhisperModel
import logging
import opencc

# 设置日志配置
logger = logging.getLogger(__name__)

def format_timestamp(seconds: float) -> str:
    """将秒数格式化为 SRT 格式的时间字符串（hh:mm:ss,mmm）"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

def convert_to_traditional_chinese(text: str) -> str:
    """将简体中文转换为繁体中文"""
    try:
        # 初始化 OpenCC 转换器 (简体转繁体)
        converter = opencc.OpenCC('s2t')
        return converter.convert(text)
    except Exception as e:
        logger.warning(f"Failed to convert to traditional Chinese: {e}")
        return text

def add_chinese_punctuation(text: str, language: str) -> str:
    """为中文文本添加基本标点符号"""
    if not text or language not in ['zh', 'chinese']:
        return text
    
    import re
    
    # 移除多余空格
    text = re.sub(r'\s+', '', text.strip())
    
    # 如果文本已经有足够的标点符号，直接返回
    punctuation_count = len(re.findall(r'[。！？，、；：]', text))
    text_length = len(text)
    if punctuation_count > 0 and (punctuation_count / text_length) > 0.05:
        return text
    
    # 基本的中文标点符号规则
    # 在语气词后添加逗号
    text = re.sub(r'(吧|呢|啊|哦|嗯|唉|哎|的话)(?![。！？，、；：])', r'\1，', text)
    
    # 在疑问词后添加问号
    text = re.sub(r'(什么|为什么|怎么|哪里|哪儿|谁|何时|如何|是否|吗|呢)(?![。！？，、；：])', r'\1？', text)
    
    # 在感叹词后添加感叹号
    text = re.sub(r'(太好了|真的|不可能|天啊|哇|太棒了|amazing|wonderful)(?![。！？，、；：])', r'\1！', text)
    
    # 在连接词后添加逗号
    text = re.sub(r'(然后|接着|之后|但是|不过|而且|另外|所以|因此|因为|由于)(?![。！？，、；：])', r'\1，', text)
    
    # 处理长句子，每15-20个字符添加逗号
    if len(text) > 20:
        # 在适当位置添加逗号分隔长句
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
    
    # 在句子结尾添加句号（如果没有其他标点）
    if not re.search(r'[。！？]$', text):
        text += '。'
    
    # 清理重复的标点符号
    text = re.sub(r'([。！？，、；：])\1+', r'\1', text)
    
    return text

def transcribe_worker(audio_path: str, language: str, result_queue: Queue, progress_dict: dict, task_id: str):
    """在独立进程中执行转录的工作函数"""
    try:
        # 在子进程中重新初始化模型
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        worker_model = WhisperModel("large-v3", device=device, compute_type=compute_type)
        
        # 转录音频
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
        # 生成纯文本格式
        txt_output = ""
        
        segments_list = list(segments)
        total_segments = len(segments_list)
        
        for i, segment in enumerate(segments_list, start=1):
            # 更新进度
            progress_dict[task_id] = int((i / total_segments) * 100)
            
            start_ts = format_timestamp(segment.start)
            end_ts = format_timestamp(segment.end)
            
            # 处理每个片段的文本，添加标点符号并转换为繁体中文
            segment_text = segment.text.strip()
            if detected_language == 'zh':
                segment_text = add_chinese_punctuation(segment_text, detected_language)
                # 转换为繁体中文
                segment_text = convert_to_traditional_chinese(segment_text)
            
            srt_output += f"{i}\n{start_ts} --> {end_ts}\n{segment_text}\n\n"
            
            # 根据语言决定是否需要空格分隔
            # 中文、日文、韩文、泰文不需要空格，其他语言需要空格
            no_space_languages = ['zh', 'ja', 'ko', 'th', 'chinese', 'japanese', 'korean', 'thai']
            
            if detected_language in no_space_languages:
                # 中文等语言直接连接，不加空格
                txt_output += segment_text
            else:
                # 其他语言需要空格分隔
                if txt_output:  # 如果不是第一个片段，前面加空格
                    txt_output += f" {segment_text}"
                else:
                    txt_output = segment_text
        
        # 整理纯文本格式（去除多余空格）
        txt_output = txt_output.strip()
        
        # 设置最终进度
        progress_dict[task_id] = 100
        
        # 返回结果
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