# 转换工作函数将在这里实现 
from multiprocessing import Queue
import os
import tempfile
import logging
import sys
from ..utils.ffmpeg_utils import convert_video_to_audio, validate_video_file

# 配置子進程日誌
def setup_worker_logging():
    """為子進程設置日誌配置"""
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('INFO:%(name)s:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def convert_worker(
    video_path: str, 
    output_format: str, 
    quality: str, 
    result_queue: Queue, 
    progress_dict: dict, 
    task_id: str
):
    """在独立进程中执行视频转音频的工作函数"""
    # 設置子進程日誌
    logger = setup_worker_logging()
    
    try:
        logger.info(f"Worker process started for conversion task {task_id}")
        logger.info(f"Input: {video_path}, Format: {output_format}, Quality: {quality}")
        
        # 驗證輸入文件是否存在
        if not os.path.exists(video_path):
            error_msg = f"Input video file not found: {video_path}"
            logger.error(error_msg)
            result_queue.put({
                "error": error_msg,
                "status": "error"
            })
            return
        
        # 檢查文件大小
        file_size = os.path.getsize(video_path)
        logger.info(f"Input file size: {file_size} bytes")
        
        if file_size == 0:
            error_msg = "Input video file is empty"
            logger.error(error_msg)
            result_queue.put({
                "error": error_msg,
                "status": "error"
            })
            return
        
        # 验证输入文件
        logger.info("Validating video file...")
        is_valid, validation_message = validate_video_file(video_path)
        if not is_valid:
            error_msg = f"Video validation failed: {validation_message}"
            logger.error(error_msg)
            result_queue.put({
                "error": f"视频文件验证失败: {validation_message}",
                "status": "error"
            })
            return
        
        logger.info(f"Video validation successful: {validation_message}")
        
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=f'.{output_format}',
            prefix=f'converted_audio_{task_id}_'
        ) as temp_output:
            output_path = temp_output.name
        
        logger.info(f"Output will be saved to: {output_path}")
        
        # 进度回调函数
        def progress_callback(progress: int):
            progress_dict[task_id] = progress
            logger.info(f"Task {task_id} progress: {progress}%")
        
        # 执行转换
        logger.info("Starting FFmpeg conversion...")
        success, message = convert_video_to_audio(
            input_path=video_path,
            output_path=output_path,
            format=output_format,
            quality=quality,
            progress_callback=progress_callback
        )
        
        logger.info(f"FFmpeg conversion result: success={success}, message={message}")
        
        if success:
            # 检查输出文件是否存在且有内容
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                output_size = os.path.getsize(output_path)
                logger.info(f"Output file created successfully, size: {output_size} bytes")
                
                # 设置最终进度
                progress_dict[task_id] = 100
                
                # 只传递文件路径，不读取文件内容
                result = {
                    "status": "completed",
                    "output_path": output_path,
                    "format": output_format,
                    "quality": quality,
                    "file_size": output_size,
                    "message": message
                }
                logger.info(f"Putting result into queue for task {task_id}")
                result_queue.put(result)
                logger.info(f"Result successfully put into queue for task {task_id}")
                logger.info(f"Conversion task {task_id} completed successfully")
                
            else:
                error_msg = f"Output file not found or empty: {output_path}"
                if os.path.exists(output_path):
                    error_msg += f" (file exists but size is {os.path.getsize(output_path)})"
                else:
                    error_msg += " (file does not exist)"
                    
                logger.error(error_msg)
                result_queue.put({
                    "error": "转换完成但输出文件不存在或为空",
                    "status": "error"
                })
        else:
            error_msg = f"Conversion failed: {message}"
            logger.error(error_msg)
            error_result = {
                "error": f"转换失败: {message}",
                "status": "error"
            }
            logger.info(f"Putting error result into queue for task {task_id}")
            result_queue.put(error_result)
            logger.info(f"Error result successfully put into queue for task {task_id}")
            
    except Exception as e:
        error_msg = f"Error during conversion: {e}"
        logger.error(error_msg, exc_info=True)
        exception_result = {
            "error": f"转换过程中发生错误: {str(e)}",
            "status": "error"
        }
        logger.info(f"Putting exception result into queue for task {task_id}")
        result_queue.put(exception_result)
        logger.info(f"Exception result successfully put into queue for task {task_id}")
    finally:
        # 注意：不在這裡清理輸出文件，因為父進程需要讀取它
        # 父進程會在讀取完文件後負責清理
        logger.info(f"Worker process finished for conversion task {task_id}") 