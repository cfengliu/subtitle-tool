# FFmpeg 相关的工具函数将在这里实现 

import subprocess
import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

def check_ffmpeg_installed() -> bool:
    """检查系统是否安装了FFmpeg"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def get_video_info(video_path: str) -> Optional[dict]:
    """获取视频文件信息"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            return info
        else:
            logger.error(f"FFprobe failed: {result.stderr}")
            return None
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return None

def convert_video_to_audio(
    input_path: str, 
    output_path: str, 
    format: str = 'mp3',
    quality: str = 'medium',
    progress_callback: Optional[callable] = None
) -> Tuple[bool, str]:
    """
    将视频文件转换为音频文件
    
    Args:
        input_path: 输入视频文件路径
        output_path: 输出音频文件路径
        format: 输出格式 ('mp3', 'wav', 'ogg', 'aac')
        quality: 音质 ('high', 'medium', 'low')
        progress_callback: 进度回调函数
    
    Returns:
        Tuple[bool, str]: (是否成功, 错误信息或成功信息)
    """
    try:
        # 检查FFmpeg是否可用
        if not check_ffmpeg_installed():
            return False, "FFmpeg not installed or not found in PATH"
        
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            return False, f"Input file not found: {input_path}"
        
        # 获取视频信息以计算进度
        video_info = get_video_info(input_path)
        total_duration = None
        if video_info and 'format' in video_info:
            try:
                total_duration = float(video_info['format'].get('duration', 0))
            except (ValueError, TypeError):
                pass
        
        # 设置音质参数
        quality_settings = {
            'high': {'mp3': '320k', 'aac': '256k', 'ogg': '320k', 'wav': None},
            'medium': {'mp3': '192k', 'aac': '128k', 'ogg': '192k', 'wav': None},
            'low': {'mp3': '128k', 'aac': '96k', 'ogg': '128k', 'wav': None}
        }
        
        # 构建FFmpeg命令
        cmd = ['ffmpeg', '-i', input_path, '-y']  # -y 覆盖输出文件
        
        # 添加格式特定参数
        if format == 'mp3':
            cmd.extend(['-codec:a', 'libmp3lame'])
            if quality_settings[quality]['mp3']:
                cmd.extend(['-b:a', quality_settings[quality]['mp3']])
        elif format == 'aac':
            cmd.extend(['-codec:a', 'aac'])
            if quality_settings[quality]['aac']:
                cmd.extend(['-b:a', quality_settings[quality]['aac']])
        elif format == 'ogg':
            cmd.extend(['-codec:a', 'libvorbis'])
            if quality_settings[quality]['ogg']:
                cmd.extend(['-b:a', quality_settings[quality]['ogg']])
        elif format == 'wav':
            cmd.extend(['-codec:a', 'pcm_s16le'])
        else:
            return False, f"Unsupported format: {format}"
        
        # 添加其他参数
        cmd.extend(['-vn'])  # 不包含视频流
        cmd.append(output_path)
        
        logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
        
        # 执行转换
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            universal_newlines=True
        )
        
        # 监控进度
        while True:
            output = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break
            
            if output and progress_callback and total_duration:
                # 解析FFmpeg输出中的时间信息
                if 'time=' in output:
                    try:
                        time_str = output.split('time=')[1].split()[0]
                        current_time = parse_time_string(time_str)
                        if current_time and total_duration > 0:
                            progress = min(100, int((current_time / total_duration) * 100))
                            progress_callback(progress)
                    except Exception as e:
                        logger.debug(f"Error parsing progress: {e}")
        
        # 等待进程完成
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"Conversion successful. Output file size: {file_size} bytes")
                return True, f"Successfully converted to {format.upper()}"
            else:
                return False, "Conversion completed but output file not found"
        else:
            logger.error(f"FFmpeg error: {stderr}")
            return False, f"FFmpeg conversion failed: {stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "Conversion timeout"
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return False, f"Conversion error: {str(e)}"

def parse_time_string(time_str: str) -> Optional[float]:
    """解析FFmpeg时间字符串 (HH:MM:SS.mmm) 为秒数"""
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except Exception:
        pass
    return None

def get_supported_formats() -> list:
    """获取支持的音频格式列表"""
    return ['mp3', 'wav', 'ogg', 'aac']

def validate_video_file(file_path: str) -> Tuple[bool, str]:
    """验证视频文件是否有效"""
    try:
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "File is empty"
        
        # 使用FFprobe检查文件格式
        video_info = get_video_info(file_path)
        if not video_info:
            return False, "Invalid video file or unsupported format"
        
        # 检查是否有音频流
        has_audio = False
        if 'streams' in video_info:
            for stream in video_info['streams']:
                if stream.get('codec_type') == 'audio':
                    has_audio = True
                    break
        
        if not has_audio:
            return False, "Video file does not contain audio stream"
        
        return True, "Valid video file"
        
    except Exception as e:
        return False, f"Error validating file: {str(e)}" 