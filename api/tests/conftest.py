"""
pytest配置文件 - 定义测试的通用fixtures和配置
"""
import pytest
import uuid
from unittest.mock import Mock, MagicMock
from fastapi.testclient import TestClient
from io import BytesIO

# 导入被测试的模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.whisper_api import app
from src.routers.transcribe import TranscriptionTask


@pytest.fixture
def client():
    """FastAPI测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_task_id():
    """生成示例任务ID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_audio_file():
    """生成示例音频文件"""
    audio_content = b"fake audio content for testing"
    return {
        "file": ("test_audio.mp3", BytesIO(audio_content), "audio/mpeg")
    }


@pytest.fixture
def mock_transcription_task():
    """模拟转录任务对象"""
    task_id = str(uuid.uuid4())
    task = TranscriptionTask(task_id)
    return task


@pytest.fixture
def mock_process():
    """模拟进程对象"""
    process = Mock()
    process.is_alive.return_value = True
    process.terminate = Mock()
    process.kill = Mock()
    process.join = Mock()
    process.start = Mock()
    return process


@pytest.fixture
def sample_transcription_result():
    """示例转录结果"""
    return {
        "srt": "1\n00:00:00,000 --> 00:00:05,000\n你好，這是測試。\n\n",
        "txt": "你好，這是測試。",
        "detected_language": "zh",
        "status": "completed"
    }


@pytest.fixture
def mock_active_task_data(sample_task_id, mock_transcription_task):
    """模拟活跃任务数据"""
    return {
        "task": mock_transcription_task,
        "temp_file": "/tmp/test_audio.mp3",
        "filename": "test_audio.mp3",
        "process": Mock(),
        "result_queue": Mock(),
        "progress_dict": {sample_task_id: 50}
    }


@pytest.fixture
def sample_video_file():
    """生成示例视频文件"""
    video_content = b"fake video content for testing"
    return {
        "file": ("test_video.mp4", BytesIO(video_content), "video/mp4")
    }


@pytest.fixture
def mock_conversion_task():
    """模拟转换任务对象"""
    from src.routers.convert import ConversionTask
    task_id = str(uuid.uuid4())
    task = ConversionTask(task_id)
    return task


@pytest.fixture
def mock_active_convert_task_data(sample_task_id, mock_conversion_task):
    """模拟活跃转换任务数据"""
    return {
        "task": mock_conversion_task,
        "temp_file": "/tmp/test_video.mp4",
        "filename": "test_video.mp4",
        "format": "mp3",
        "quality": "medium",
        "process": Mock(),
        "result_queue": Mock(),
        "progress_dict": {sample_task_id: 75}
    }


@pytest.fixture
def sample_conversion_result():
    """示例转换结果"""
    return {
        "audio_data": b"fake converted audio data",
        "format": "mp3",
        "quality": "medium",
        "file_size": 1024,
        "message": "Successfully converted to MP3",
        "status": "completed"
    }


@pytest.fixture
def sample_conversion_error():
    """示例转换错误结果"""
    return {
        "error": "转换失败: FFmpeg error occurred",
        "status": "error"
    } 