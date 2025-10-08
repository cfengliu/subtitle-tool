from multiprocessing import Queue
import os
import torch
from faster_whisper import WhisperModel
import logging

from ..utils.text_conversion import convert_to_traditional_chinese
from ..utils.audio_processing import denoise_audio

# 设置日志配置
logger = logging.getLogger(__name__)

# Optional zh punctuation restoration (zhpr)
_ZHPR_AVAILABLE = True
try:
    # Avoid importing heavy modules unless needed
    from zhpr.predict import DocumentDataset, merge_stride, decode_pred  # type: ignore
    from transformers import AutoModelForTokenClassification, AutoTokenizer  # type: ignore
    from torch.utils.data import DataLoader  # type: ignore
    logger.info("zhpr modules loaded successfully - Chinese punctuation restoration available")
except Exception as e:
    _ZHPR_AVAILABLE = False
    logger.warning(f"zhpr modules not available - falling back to basic punctuation rules: {e}")

def format_timestamp(seconds: float) -> str:
    """将秒数格式化为 SRT 格式的时间字符串（hh:mm:ss,mmm）"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"

def group_segments_into_paragraphs(segments_list, max_gap_seconds=2.0, max_paragraph_segments=10, max_paragraph_chars=500):
    """將 segments 按時間間隔分組成段落，限制段落大小以避免內存和處理問題"""
    if not segments_list:
        return []
    
    paragraphs = []
    current_paragraph = [segments_list[0]]
    current_char_count = len(segments_list[0].text.strip())
    
    for i in range(1, len(segments_list)):
        prev_segment = segments_list[i-1]
        current_segment = segments_list[i]
        segment_text = current_segment.text.strip()
        
        # 檢查是否需要開始新段落的條件
        gap = current_segment.start - prev_segment.end
        would_exceed_segments = len(current_paragraph) >= max_paragraph_segments
        would_exceed_chars = current_char_count + len(segment_text) > max_paragraph_chars
        has_time_gap = gap > max_gap_seconds
        
        if has_time_gap or would_exceed_segments or would_exceed_chars:
            paragraphs.append(current_paragraph)
            current_paragraph = [current_segment]
            current_char_count = len(segment_text)
        else:
            current_paragraph.append(current_segment)
            current_char_count += len(segment_text)
    
    # 添加最後一個段落
    if current_paragraph:
        paragraphs.append(current_paragraph)
    
    return paragraphs

def process_paragraph_punctuation(paragraph_segments, zh_restorer, detected_language, worker_logger):
    """處理整個段落的標點符號，返回處理後的段落文本和每個segment的文本"""
    # 組合段落文本
    paragraph_text = ""
    segment_texts = []
    
    for segment in paragraph_segments:
        clean_text = segment.text.strip()
        segment_texts.append(clean_text)
        paragraph_text += clean_text
    
    # 處理標點符號
    if detected_language == 'zh':
        if zh_restorer is not None:
            try:
                punctuated_paragraph = zh_restorer.punctuate(paragraph_text)
                worker_logger.info(f"Applied zhpr punctuation to paragraph: '{paragraph_text[:50]}...' -> '{punctuated_paragraph[:50]}...'")
                distributed_result = distribute_punctuation_to_segments(segment_texts, paragraph_text, punctuated_paragraph)
                worker_logger.info(f"Distributed result: {distributed_result[:3]}...")  # Show first 3 segments
                return distributed_result
            except Exception as e:
                worker_logger.warning(f"zhpr punctuate failed for paragraph, falling back to rules: {e}")
                # 逐句處理作為後備方案
                result = []
                for segment_text in segment_texts:
                    result.append(add_chinese_punctuation(segment_text, detected_language))
                return result
        else:
            # 使用規則處理整個段落
            punctuated_paragraph = add_chinese_punctuation(paragraph_text, detected_language)
            return distribute_punctuation_to_segments(segment_texts, paragraph_text, punctuated_paragraph)
    
    # 非中文直接返回原文本
    return segment_texts

def distribute_punctuation_to_segments(original_segments, original_paragraph, punctuated_paragraph):
    """將標點符號處理後的段落文本重新分配給原始segments"""
    import re
    
    # 如果標點符號處理失敗或沒有變化，直接返回原文本
    if not punctuated_paragraph or punctuated_paragraph == original_paragraph:
        return original_segments
    
    # 移除原始段落中的所有空格來匹配
    clean_punctuated = punctuated_paragraph.replace(' ', '')

    def _preserve_length_placeholder(match):
        return ' ' * len(match.group(0))

    # 用空格佔位保留特殊 token 長度，避免破壞索引對齊
    clean_punctuated = re.sub(r'\[(UNK|PAD|CLS|SEP|MASK)\]', _preserve_length_placeholder, clean_punctuated)

    result = []
    punctuated_index = 0

    # 定義標點符號集合
    PUNCTUATION = '，。！？；：、（）【】""''…—'
    # 向前看的最大字符數（用於重新對齊）
    LOOKAHEAD = 3

    for segment_text in original_segments:
        clean_segment = segment_text.replace(' ', '')
        segment_result = ""

        # 查找這個segment在標點文本中的對應位置
        if punctuated_index < len(clean_punctuated):
            # 逐字符匹配並收集標點符號
            char_index = 0
            while char_index < len(clean_segment) and punctuated_index < len(clean_punctuated):
                orig_char = clean_segment[char_index]
                punct_char = clean_punctuated[punctuated_index]

                if orig_char == punct_char:
                    # 字符匹配，添加到結果
                    segment_result += punct_char
                    char_index += 1
                    punctuated_index += 1
                elif punct_char in PUNCTUATION:
                    # 遇到標點符號，添加到結果但不增加原文索引
                    segment_result += punct_char
                    punctuated_index += 1
                elif punct_char == ' ':
                    # 佔位符 - 跳過但保留索引位置
                    punctuated_index += 1
                else:
                    # 不匹配 - 嘗試向前看以重新對齊
                    realigned = False
                    for look_ahead in range(1, LOOKAHEAD + 1):
                        if punctuated_index + look_ahead < len(clean_punctuated):
                            future_punct_char = clean_punctuated[punctuated_index + look_ahead]
                            if future_punct_char == orig_char:
                                # 找到對齊點 - 跳過中間的標點符號
                                for skip_idx in range(look_ahead):
                                    skip_char = clean_punctuated[punctuated_index + skip_idx]
                                    if skip_char in PUNCTUATION:
                                        segment_result += skip_char
                                punctuated_index += look_ahead
                                realigned = True
                                break

                    if not realigned:
                        # 無法重新對齊 - 保留原文字符，跳過標點文本
                        segment_result += orig_char
                        char_index += 1
                        punctuated_index += 1

            # 處理原文剩餘的字符
            while char_index < len(clean_segment):
                segment_result += clean_segment[char_index]
                char_index += 1

            # 如果這是段落的最後一個segment，檢查是否有剩餘的標點符號
            if segment_text == original_segments[-1]:
                while punctuated_index < len(clean_punctuated):
                    remaining_char = clean_punctuated[punctuated_index]
                    if remaining_char in PUNCTUATION:
                        segment_result += remaining_char
                    punctuated_index += 1

        # 如果沒有找到匹配，使用原文本
        if not segment_result:
            segment_result = segment_text
        else:
            # 驗證：移除標點後應該與原文相同
            stripped_result = re.sub(f'[{re.escape(PUNCTUATION)}]', '', segment_result)
            stripped_result = stripped_result.replace(' ', '')
            if stripped_result != clean_segment:
                # segment 級別的回退 - 只回退這一個 segment
                segment_result = segment_text

        result.append(segment_result)
    
    return result

def add_chinese_punctuation(text: str, language: str) -> str:
    """为中文文本添加基本标点符号 - 简化版本"""
    if not text or language not in ['zh', 'chinese']:
        return text
    
    import re
    
    # 移除多余空格
    text = re.sub(r'\s+', '', text.strip())
    
    # 如果文本已经有足够的标点符号，直接返回
    punctuation_count = len(re.findall(r'[。！？，、；：]', text))
    text_length = len(text)
    if punctuation_count > 0 and (punctuation_count / text_length) > 0.02:
        return clean_punctuation_combinations(text)
    
    # 简单的规则：只在明确的语言标记处添加标点
    # 疑问词后加问号
    text = re.sub(r'(什么|为什么|怎么|哪里|哪儿|谁|何时|如何|是否|吗|呢)(?![。！？，、；：])', r'\1？', text)
    
    # 语气词后加逗号（但不在句子末尾，且只在句子开头）
    text = re.sub(r'^(那|这)(?=.{5,})(?![。！？，、；：])', r'\1，', text)
    
    # 连接词前加逗号（在句子中间）
    text = re.sub(r'(.{3,})(所以|因为|如果|就是|也就是说)(?=.{3,})(?![。！？，、；：])', r'\1，\2', text)
    
    # 转折词前加逗号
    text = re.sub(r'(.{3,})(但是|不过|然而|可是|而且|另外|同时|接着|然后)(?![。！？，、；：])', r'\1，\2', text)
    
    # 在句子结尾添加句号（如果没有其他标点）
    if not re.search(r'[。！？]$', text):
        text += '。'
    
    # 清理不合理的标点符号组合
    text = clean_punctuation_combinations(text)
    
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


class _ZhPunctuationRestorer:
    """Chinese punctuation restorer using zhpr README approach.

    Loads the pretrained model 'p208p2002/zh-wiki-punctuation-restore' and
    restores punctuation for a given Chinese text. If model loading fails,
    callers should catch exceptions and fall back.
    """

    def __init__(self, device: str = "cpu") -> None:
        self.device = device
        self.model_name = "p208p2002/zh-wiki-punctuation-restore"
        self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if self.device == "cuda":
            self.model.to("cuda")

    def punctuate(self, text: str, window_size: int = 256, step: int = 200) -> str:
        if not text:
            return text
        dataset = DocumentDataset(text, window_size=window_size, step=step)
        dataloader = DataLoader(dataset=dataset, shuffle=False, batch_size=4)

        self.model.eval()
        model_pred_out = []
        with torch.no_grad():
            for batch in dataloader:
                if self.device == "cuda":
                    batch = batch.to("cuda")
                batch_out = self._predict_step(batch)
                for out in batch_out:
                    model_pred_out.append(out)

        merged = merge_stride(model_pred_out, step)
        decoded = decode_pred(merged)
        return "".join(decoded)

    def _predict_step(self, batch):
        batch_out = []
        batch_input_ids = batch
        encodings = {"input_ids": batch_input_ids}
        output = self.model(**encodings)
        predicted_token_class_id_batch = output["logits"].argmax(-1)
        for predicted_token_class_ids, input_ids in zip(
            predicted_token_class_id_batch, batch_input_ids
        ):
            out = []
            tokens = self.tokenizer.convert_ids_to_tokens(input_ids)
            input_ids_list = input_ids.tolist()
            try:
                pad_start = input_ids_list.index(self.tokenizer.pad_token_id)
            except Exception:
                pad_start = len(input_ids_list)
            tokens = tokens[:pad_start]
            predicted_tokens_classes = [
                self.model.config.id2label[t.item()] for t in predicted_token_class_ids
            ]
            predicted_tokens_classes = predicted_tokens_classes[:pad_start]
            for token, ner in zip(tokens, predicted_tokens_classes):
                out.append((token, ner))
            batch_out.append(out)
        return batch_out

def transcribe_worker(
    audio_path: str,
    language: str,
    result_queue: Queue,
    progress_dict: dict,
    task_id: str,
    apply_denoise: bool = False,
):
    """在独立进程中执行转录的工作函数"""
    denoise_temp_path = None

    try:
        # 在子进程中设置日志
        import logging
        logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
        worker_logger = logging.getLogger(__name__)
        
        # 记录 zhpr 状态
        worker_logger.info(f"Worker {task_id} started - zhpr available: {_ZHPR_AVAILABLE}")
        
        processed_audio_path = audio_path

        if apply_denoise:
            try:
                current_progress = progress_dict.get(task_id, 0)
            except Exception:
                current_progress = 0

            progress_dict[task_id] = max(current_progress, 5)
            success, denoised_path, message = denoise_audio(audio_path)
            if success and denoised_path:
                processed_audio_path = denoised_path
                denoise_temp_path = denoised_path
                worker_logger.info(f"Noise reduction applied for task {task_id}: {message}")
                progress_dict[task_id] = max(progress_dict.get(task_id, 0), 10)
            else:
                worker_logger.warning(f"Noise reduction requested but failed for task {task_id}: {message}")

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
            segments, info = worker_model.transcribe(processed_audio_path, language=language, **transcribe_options)
            detected_language = language
        else:
            segments, info = worker_model.transcribe(processed_audio_path, **transcribe_options)
            detected_language = info.language
        
        # 生成 SRT 格式
        srt_output = ""
        # 生成纯文本格式
        txt_output = ""
        
        segments_list = list(segments)
        total_segments = len(segments_list)
        
        # Prepare zh punctuation restorer if needed
        zh_restorer = None
        def _is_zh(lang: str) -> bool:
            try:
                return lang == 'zh' or lang.startswith('zh') or lang.lower() in ('chinese',)
            except Exception:
                return False

        if (_ZHPR_AVAILABLE and ((language and _is_zh(language)) or (not language and _is_zh(detected_language)))):
            try:
                zh_restorer = _ZhPunctuationRestorer(device=device)
                worker_logger.info(f"Using zhpr ML-based punctuation restoration for Chinese text")
            except Exception as e:
                worker_logger.warning(f"Failed to initialize zhpr restorer: {e}")
                zh_restorer = None
        else:
            zh_restorer = None
            if ((language and _is_zh(language)) or (not language and _is_zh(detected_language))):
                worker_logger.info(f"Using rule-based punctuation restoration for Chinese text")

        # 將 segments 分組為段落並處理
        paragraphs = group_segments_into_paragraphs(segments_list, max_gap_seconds=2.0, max_paragraph_segments=10, max_paragraph_chars=500)
        
        # 統計段落信息
        max_paragraph_size = max(len(p) for p in paragraphs) if paragraphs else 0
        avg_paragraph_size = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        
        worker_logger.info(f"Grouped {len(segments_list)} segments into {len(paragraphs)} paragraphs")
        worker_logger.info(f"Paragraph stats - Max: {max_paragraph_size} segments, Avg: {avg_paragraph_size:.1f} segments")
        
        processed_segments = []
        for paragraph_idx, paragraph_segments in enumerate(paragraphs):
            # 處理段落標點符號
            paragraph_processed_texts = process_paragraph_punctuation(
                paragraph_segments, zh_restorer, detected_language, worker_logger
            )
            
            # 將處理結果與原始segments組合
            for segment, processed_text in zip(paragraph_segments, paragraph_processed_texts):
                processed_segments.append({
                    'segment': segment,
                    'processed_text': processed_text
                })
            
            # 更新進度
            progress_dict[task_id] = int(((paragraph_idx + 1) / len(paragraphs)) * 80)  # 保留20%用於後處理

        # 生成 SRT 輸出 - 使用原始 segment 文本，不添加標點符號
        for i, item in enumerate(processed_segments, start=1):
            segment = item['segment']
            segment_text = segment.text.strip()  # 使用原始文本
            
            start_ts = format_timestamp(segment.start)
            end_ts = format_timestamp(segment.end)
            
            # 如果是中文，轉換為繁體中文
            if detected_language == 'zh':
                segment_text = convert_to_traditional_chinese(segment_text)
            
            srt_output += f"{i}\n{start_ts} --> {end_ts}\n{segment_text}\n\n"
            
        # 生成 TXT 輸出
        no_space_languages = ['zh', 'ja', 'ko', 'th', 'chinese', 'japanese', 'korean', 'thai']
        for i, item in enumerate(processed_segments):
            segment_text = item['processed_text']
            
            # 如果是中文，轉換為繁體中文
            if detected_language == 'zh':
                segment_text = convert_to_traditional_chinese(segment_text)
            
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
            "status": "completed",
            "noise_reduction_applied": apply_denoise and denoise_temp_path is not None
        }
        result_queue.put(result)
        
    except Exception as e:
        logger.error("Error during transcription: %s", e)
        error_result = {"error": "Transcription failed.", "status": "error"}
        result_queue.put(error_result) 
    finally:
        if denoise_temp_path and os.path.exists(denoise_temp_path):
            try:
                os.remove(denoise_temp_path)
            except OSError:
                logger.warning(f"Failed to clean up denoised file: {denoise_temp_path}")
