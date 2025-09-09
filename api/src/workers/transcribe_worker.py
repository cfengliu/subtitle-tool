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
    """为中文文本添加基本标点符号 - 改进版本"""
    if not text or language not in ['zh', 'chinese']:
        return text
    
    import re
    
    # 移除多余空格
    text = re.sub(r'\s+', '', text.strip())
    
    # 如果文本已经有标点符号，只做清理
    punctuation_count = len(re.findall(r'[。！？，、；：]', text))
    if punctuation_count > 0:
        return clean_punctuation_combinations(text)
    
    # 基于语义的智能标点添加
    text = add_semantic_punctuation(text)
    
    # 清理不合理的标点符号组合
    text = clean_punctuation_combinations(text)
    
    return text

def add_semantic_punctuation(text: str) -> str:
    """基于语义和语法规则添加标点符号"""
    import re
    
    # 1. 疑问句处理（最高优先级）
    question_patterns = [
        r'(什么|为什么|怎么|哪里|哪儿|谁|何时|如何|是否)(.{0,10}?)$',
        r'(.{0,20}?)(吗|呢)$',
        r'^(是不是|对不对|好不好|行不行)(.*)$'
    ]
    
    for pattern in question_patterns:
        if re.search(pattern, text):
            if not text.endswith('？'):
                text = re.sub(r'$', '？', text)
            return text
    
    # 2. 感叹句处理
    exclamation_patterns = [
        r'(太好了|真的|不可能|天啊|哇|太棒了|厉害|完了|糟糕)',
        r'(好棒|太棒|真棒|不错|很好|非常好)'
    ]
    
    for pattern in exclamation_patterns:
        if re.search(pattern, text):
            if not re.search(r'[。！？]$', text):
                text += '！'
            return text
    
    # 3. 复合句处理 - 按语义切分
    text = add_compound_sentence_punctuation(text)
    
    # 4. 如果没有句尾标点，添加句号
    if not re.search(r'[。！？]$', text):
        text += '。'
    
    return text

def add_compound_sentence_punctuation(text: str) -> str:
    """处理复合句的标点符号"""
    import re
    
    # 转折关系
    text = re.sub(r'(.{5,}?)(但是|不过|然而|可是|只是)(.{5,})', r'\1，\2\3', text)
    
    # 因果关系
    text = re.sub(r'(.{5,}?)(因为|由于|既然)(.{5,}?)(所以|因此|就)', r'\1，\2\3，\4', text)
    
    # 递进关系
    text = re.sub(r'(.{5,}?)(而且|并且|另外|此外|同时)(.{5,})', r'\1，\2\3', text)
    
    # 时间顺序
    text = re.sub(r'(.{5,}?)(然后|接着|之后|后来|接下来)(.{5,})', r'\1，\2\3', text)
    
    # 条件关系
    text = re.sub(r'(.{5,}?)(如果|要是|假如)(.{5,}?)(就|那么)', r'\1，\2\3，\4', text)
    
    return text

def clean_punctuation_combinations(text: str) -> str:
    """清理不合理的标点符号组合"""
    import re
    
    # 清理连续的标点符号组合
    text = re.sub(r'，。', '。', text)  # 逗号后跟句号 -> 句号
    text = re.sub(r'。，', '。', text)  # 句号后跟逗号 -> 句号
    text = re.sub(r'，，+', '，', text)  # 多个逗号 -> 单个逗号
    text = re.sub(r'。。+', '。', text)  # 多个句号 -> 单个句号
    
    # 清理短语后不合理的标点符号
    text = re.sub(r'(会|也会|可能会|应该|就是|这样|那个)。(?=.)', r'\1，', text)  # 短语后的句号改为逗号
    
    # 移除句子开头的逗号
    text = re.sub(r'^，', '', text)
    
    # 移除句子结尾多余的逗号
    text = re.sub(r'，$', '。', text)
    
    # 清理连接词后的重复逗号
    text = re.sub(r'(然后|但是|而且|所以)，，', r'\1，', text)
    
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