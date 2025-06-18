# 转换工作函数将在这里实现 
from multiprocessing import Queue
import os
import tempfile
import logging
from ..utils.ffmpeg_utils import convert_video_to_audio, validate_video_file

logger = logging.getLogger(__name__)

def convert_worker(
    video_path: str, 
    output_format: str, 
    quality: str, 
    result_queue: Queue, 
    progress_dict: dict, 
    task_id: str
):
    """在独立进程中执行视频转音频的工作函数"""
    try:
        logger.info(f"Starting conversion task {task_id}")
        logger.info(f"Input: {video_path}, Format: {output_format}, Quality: {quality}")
        
        # 验证输入文件
        is_valid, validation_message = validate_video_file(video_path)
        if not is_valid:
            logger.error(f"Video validation failed: {validation_message}")
            result_queue.put({
                "error": f"视频文件验证失败: {validation_message}",
                "status": "error"
            })
            return
        
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
            logger.debug(f"Task {task_id} progress: {progress}%")
        
        # 执行转换
        success, message = convert_video_to_audio(
            input_path=video_path,
            output_path=output_path,
            format=output_format,
            quality=quality,
            progress_callback=progress_callback
        )
        
        if success:
            # 检查输出文件是否存在且有内容
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                # 读取转换后的音频文件
                with open(output_path, 'rb') as f:
                    audio_data = f.read()
                
                # 设置最终进度
                progress_dict[task_id] = 100
                
                # 返回成功结果
                result = {
                    "audio_data": audio_data,
                    "format": output_format,
                    "quality": quality,
                    "file_size": len(audio_data),
                    "message": message,
                    "status": "completed"
                }
                result_queue.put(result)
                logger.info(f"Conversion task {task_id} completed successfully")
                
            else:
                logger.error(f"Output file not found or empty: {output_path}")
                result_queue.put({
                    "error": "转换完成但输出文件不存在或为空",
                    "status": "error"
                })
        else:
            logger.error(f"Conversion failed: {message}")
            result_queue.put({
                "error": f"转换失败: {message}",
                "status": "error"
            })
            
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        result_queue.put({
            "error": f"转换过程中发生错误: {str(e)}",
            "status": "error"
        })
    finally:
        # 清理临时文件
        try:
            if 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
                logger.info(f"Temporary output file deleted: {output_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {output_path}: {e}") 