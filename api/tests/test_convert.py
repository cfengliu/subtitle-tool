"""
测试convert功能相关的端点和工具函数
"""
import pytest
import uuid
import tempfile
import os
from unittest.mock import patch, Mock, MagicMock
from fastapi import status
from io import BytesIO


class TestConvertEndpoints:
    """转换相关端点测试"""
    
    @patch('src.routers.convert.convert_semaphore')
    @patch('src.routers.convert.Process')
    @patch('src.routers.convert.Manager')
    @patch('src.routers.convert.Queue')
    @patch('src.routers.convert.get_supported_formats')
    def test_start_video_conversion_success(
        self, mock_get_formats, mock_queue, mock_manager, mock_process, mock_semaphore,
        client, sample_video_file
    ):
        """测试启动视频转换任务成功"""
        # 设置mock
        mock_semaphore.acquire.return_value = True
        mock_get_formats.return_value = ['mp3', 'wav', 'ogg', 'aac']
        mock_manager_instance = Mock()
        mock_manager.return_value = mock_manager_instance
        mock_manager_instance.dict.return_value = {}
        mock_process.return_value = Mock()
        
        # 发送请求
        response = client.post(
            "/convert/",
            files=sample_video_file,
            data={"format": "mp3", "quality": "medium"}
        )
        
        # 验证响应
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "started"
        assert data["message"] == "视频转音频任务已启动"
    
    @patch('src.routers.convert.convert_semaphore')
    def test_start_conversion_concurrent_limit(
        self, mock_semaphore, client, sample_video_file
    ):
        """测试并发限制"""
        mock_semaphore.acquire.return_value = False
        
        response = client.post(
            "/convert/", 
            files=sample_video_file,
            data={"format": "mp3", "quality": "medium"}
        )
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Too many concurrent conversion requests" in response.json()["detail"]
    
    @patch('src.routers.convert.get_supported_formats')
    def test_start_conversion_unsupported_format(
        self, mock_get_formats, client, sample_video_file
    ):
        """测试不支持的格式"""
        mock_get_formats.return_value = ['mp3', 'wav']
        
        response = client.post(
            "/convert/",
            files=sample_video_file,
            data={"format": "xyz", "quality": "medium"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported format" in response.json()["detail"]
    
    def test_start_conversion_invalid_quality(self, client, sample_video_file):
        """测试无效的质量参数"""
        response = client.post(
            "/convert/",
            files=sample_video_file,
            data={"format": "mp3", "quality": "invalid"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Quality must be one of" in response.json()["detail"]
    
    def test_start_conversion_invalid_file_type(self, client, sample_audio_file):
        """测试无效的文件类型（非视频文件）"""
        response = client.post(
            "/convert/",
            files=sample_audio_file,
            data={"format": "mp3", "quality": "medium"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Please upload a video file" in response.json()["detail"]
    
    def test_get_conversion_status_not_found(self, client, sample_task_id):
        """测试获取不存在任务的状态"""
        response = client.get(f"/convert/{sample_task_id}/status")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "任务不存在"
    
    @patch('src.routers.convert.active_convert_tasks')
    def test_get_conversion_status_running(
        self, mock_active_tasks, client, sample_task_id, mock_active_convert_task_data
    ):
        """测试获取运行中任务状态"""
        mock_active_tasks.__contains__.return_value = True
        mock_active_tasks.__getitem__.return_value = mock_active_convert_task_data
        
        response = client.get(f"/convert/{sample_task_id}/status")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == sample_task_id
        assert data["status"] == "running"
        assert "progress" in data
        assert "filename" in data
        assert "format" in data
        assert "quality" in data
    
    def test_get_conversion_result_not_found(self, client, sample_task_id):
        """测试获取不存在任务的结果"""
        response = client.get(f"/convert/{sample_task_id}/result")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "任务不存在"
    
    @patch('src.routers.convert.convert_results')
    def test_get_conversion_result_completed(
        self, mock_convert_results, client, sample_task_id, sample_conversion_result
    ):
        """测试获取已完成任务结果"""
        mock_convert_results.__contains__.return_value = True
        mock_convert_results.__getitem__.return_value = sample_conversion_result
        mock_convert_results.__delitem__ = Mock()
        
        response = client.get(f"/convert/{sample_task_id}/result")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "audio/mpeg"
        assert len(response.content) == len(sample_conversion_result["audio_data"])
    
    @patch('src.routers.convert.active_convert_tasks')
    def test_get_conversion_result_still_running(
        self, mock_active_tasks, client, sample_task_id
    ):
        """测试获取仍在运行任务的结果"""
        mock_task = Mock()
        mock_task.status = "running"
        mock_task.is_cancelled.return_value = False
        
        mock_active_tasks.__contains__.return_value = True
        mock_active_tasks.__getitem__.return_value = {"task": mock_task}
        
        response = client.get(f"/convert/{sample_task_id}/result")
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["detail"] == "任务仍在进行中"
    
    @patch('src.routers.convert.convert_results')
    def test_get_conversion_result_error(
        self, mock_convert_results, client, sample_task_id, sample_conversion_error
    ):
        """测试获取失败任务的结果"""
        mock_convert_results.__contains__.return_value = True
        mock_convert_results.__getitem__.return_value = sample_conversion_error
        
        response = client.get(f"/convert/{sample_task_id}/result")
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "error" in response.json()["detail"]
    
    def test_cancel_conversion_task_not_found(self, client, sample_task_id):
        """测试取消不存在的任务"""
        response = client.post(f"/convert/{sample_task_id}/cancel")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "任务不存在或已完成"
    
    @patch('src.routers.convert.active_convert_tasks')
    def test_cancel_conversion_task_success(
        self, mock_active_tasks, client, sample_task_id
    ):
        """测试成功取消任务"""
        mock_task = Mock()
        mock_active_tasks.__contains__.return_value = True
        mock_active_tasks.__getitem__.return_value = {"task": mock_task}
        
        response = client.post(f"/convert/{sample_task_id}/cancel")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == sample_task_id
        assert data["status"] == "cancelled"
        assert data["message"] == "转换任务已被强制终止"
        mock_task.cancel.assert_called_once()
    
    def test_list_active_conversion_tasks_empty(self, client):
        """测试列出空的活跃转换任务"""
        response = client.get("/convert/tasks")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "active_tasks" in data
        assert isinstance(data["active_tasks"], list)
    
    @patch('src.routers.convert.active_convert_tasks')
    def test_list_active_conversion_tasks_with_data(self, mock_active_tasks, client):
        """测试列出有数据的活跃转换任务"""
        task_id1 = "task-1"
        task_id2 = "task-2"
        
        mock_task1 = Mock()
        mock_task1.status = "running"
        mock_task2 = Mock()
        mock_task2.status = "running"
        
        mock_progress_dict1 = Mock()
        mock_progress_dict1.get.return_value = 30
        
        mock_progress_dict2 = Mock()
        mock_progress_dict2.get.return_value = 70
        
        task_info1 = {
            "task": mock_task1,
            "progress_dict": mock_progress_dict1,
            "filename": "video1.mp4",
            "format": "mp3",
            "quality": "medium"
        }
        task_info2 = {
            "task": mock_task2,
            "progress_dict": mock_progress_dict2,
            "filename": "video2.mp4",
            "format": "wav",
            "quality": "high"
        }
        
        mock_active_tasks.items.return_value = [
            (task_id1, task_info1),
            (task_id2, task_info2)
        ]
        
        response = client.get("/convert/tasks")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["active_tasks"]) == 2
        
        # 验证第一个任务
        task1_data = data["active_tasks"][0]
        assert task1_data["task_id"] == task_id1
        assert task1_data["status"] == "running"
        assert task1_data["progress"] == 30
        assert task1_data["filename"] == "video1.mp4"
        assert task1_data["format"] == "mp3"
        assert task1_data["quality"] == "medium"
        
        # 验证第二个任务
        task2_data = data["active_tasks"][1]
        assert task2_data["task_id"] == task_id2
        assert task2_data["status"] == "running"
        assert task2_data["progress"] == 70
        assert task2_data["filename"] == "video2.mp4"
        assert task2_data["format"] == "wav"
        assert task2_data["quality"] == "high"
    
    @patch('src.routers.convert.get_supported_formats')
    def test_get_supported_audio_formats(self, mock_get_formats, client):
        """测试获取支持的音频格式"""
        mock_get_formats.return_value = ['mp3', 'wav', 'ogg', 'aac']
        
        response = client.get("/convert/formats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "supported_formats" in data
        assert data["supported_formats"] == ['mp3', 'wav', 'ogg', 'aac']


class TestConvertWorker:
    """转换工作函数测试"""
    
    @patch('src.workers.convert_worker.validate_video_file')
    @patch('src.workers.convert_worker.convert_video_to_audio')
    @patch('src.workers.convert_worker.tempfile.NamedTemporaryFile')
    @patch('src.workers.convert_worker.os.path.exists')
    @patch('src.workers.convert_worker.os.path.getsize')
    @patch('builtins.open')
    def test_convert_worker_success(
        self, mock_open, mock_getsize, mock_exists, mock_tempfile, 
        mock_convert, mock_validate, sample_task_id
    ):
        """测试转换工作函数成功执行"""
        from src.workers.convert_worker import convert_worker
        from queue import Queue
        
        # 设置mock
        mock_validate.return_value = (True, "Valid video file")
        mock_convert.return_value = (True, "Conversion successful")
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        
        # 模拟临时文件
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test_output.mp3"
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        mock_tempfile.return_value.__exit__.return_value = None
        
        # 模拟文件读取
        mock_audio_data = b"fake audio data"
        mock_file_handle = Mock()
        mock_file_handle.read.return_value = mock_audio_data
        mock_file_handle.__enter__ = Mock(return_value=mock_file_handle)
        mock_file_handle.__exit__ = Mock(return_value=None)
        mock_open.return_value = mock_file_handle
        
        # 创建队列和进度字典 - 使用普通的queue.Queue和dict来避免multiprocessing问题
        result_queue = Queue()
        progress_dict = {}
        
        # 执行转换
        convert_worker(
            video_path="/tmp/test_video.mp4",
            output_format="mp3",
            quality="medium",
            result_queue=result_queue,
            progress_dict=progress_dict,
            task_id=sample_task_id
        )
        
        # 验证结果
        assert not result_queue.empty()
        result = result_queue.get()
        assert result["status"] == "completed"
        assert result["audio_data"] == mock_audio_data
        assert result["format"] == "mp3"
        assert result["quality"] == "medium"
        assert result["file_size"] == len(mock_audio_data)
        assert progress_dict[sample_task_id] == 100
    
    @patch('src.workers.convert_worker.validate_video_file')
    def test_convert_worker_invalid_video(self, mock_validate, sample_task_id):
        """测试转换工作函数处理无效视频文件"""
        from src.workers.convert_worker import convert_worker
        from queue import Queue
        
        # 设置mock
        mock_validate.return_value = (False, "Invalid video format")
        
        # 创建队列和进度字典
        result_queue = Queue()
        progress_dict = {}
        
        # 执行转换
        convert_worker(
            video_path="/tmp/invalid_video.txt",
            output_format="mp3",
            quality="medium",
            result_queue=result_queue,
            progress_dict=progress_dict,
            task_id=sample_task_id
        )
        
        # 验证结果
        assert not result_queue.empty()
        result = result_queue.get()
        assert result["status"] == "error"
        assert "视频文件验证失败" in result["error"]
    
    @patch('src.workers.convert_worker.validate_video_file')
    @patch('src.workers.convert_worker.convert_video_to_audio')
    @patch('src.workers.convert_worker.tempfile.NamedTemporaryFile')
    def test_convert_worker_conversion_failure(
        self, mock_tempfile, mock_convert, mock_validate, sample_task_id
    ):
        """测试转换工作函数处理转换失败"""
        from src.workers.convert_worker import convert_worker
        from queue import Queue
        
        # 设置mock
        mock_validate.return_value = (True, "Valid video file")
        mock_convert.return_value = (False, "FFmpeg error: conversion failed")
        
        # 模拟临时文件
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test_output.mp3"
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        # 创建队列和进度字典
        result_queue = Queue()
        progress_dict = {}
        
        # 执行转换
        convert_worker(
            video_path="/tmp/test_video.mp4",
            output_format="mp3",
            quality="medium",
            result_queue=result_queue,
            progress_dict=progress_dict,
            task_id=sample_task_id
        )
        
        # 验证结果
        assert not result_queue.empty()
        result = result_queue.get()
        assert result["status"] == "error"
        assert "转换失败" in result["error"]
    
    @patch('src.workers.convert_worker.validate_video_file')
    @patch('src.workers.convert_worker.convert_video_to_audio')
    @patch('src.workers.convert_worker.tempfile.NamedTemporaryFile')
    @patch('src.workers.convert_worker.os.path.exists')
    @patch('src.workers.convert_worker.os.path.getsize')
    def test_convert_worker_empty_output(
        self, mock_getsize, mock_exists, mock_tempfile, mock_convert, mock_validate, sample_task_id
    ):
        """测试转换工作函数处理空输出文件"""
        from src.workers.convert_worker import convert_worker
        from queue import Queue
        
        # 设置mock
        mock_validate.return_value = (True, "Valid video file")
        mock_convert.return_value = (True, "Conversion successful")
        mock_exists.return_value = True
        mock_getsize.return_value = 0  # 空文件
        
        # 模拟临时文件
        mock_temp_file = Mock()
        mock_temp_file.name = "/tmp/test_output.mp3"
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file
        
        # 创建队列和进度字典
        result_queue = Queue()
        progress_dict = {}
        
        # 执行转换
        convert_worker(
            video_path="/tmp/test_video.mp4",
            output_format="mp3",
            quality="medium",
            result_queue=result_queue,
            progress_dict=progress_dict,
            task_id=sample_task_id
        )
        
        # 验证结果
        assert not result_queue.empty()
        result = result_queue.get()
        assert result["status"] == "error"
        assert "转换完成但输出文件不存在或为空" in result["error"]


class TestConversionTask:
    """转换任务类测试"""
    
    def test_conversion_task_creation(self, sample_task_id):
        """测试转换任务创建"""
        from src.routers.convert import ConversionTask
        
        task = ConversionTask(sample_task_id)
        assert task.task_id == sample_task_id
        assert task.status == "running"
        assert task.progress == 0
        assert task.process is None
    
    def test_conversion_task_cancel(self, sample_task_id):
        """测试转换任务取消"""
        from src.routers.convert import ConversionTask
        
        # 创建任务
        task = ConversionTask(sample_task_id)
        
        # 模拟进程
        mock_process = Mock()
        mock_process.is_alive.return_value = True
        task.process = mock_process
        
        # 取消任务
        task.cancel()
        
        # 验证
        assert task.status == "cancelled"
        mock_process.terminate.assert_called_once()
        mock_process.join.assert_called_once()
    
    def test_conversion_task_cancel_force_kill(self, sample_task_id):
        """测试转换任务强制终止"""
        from src.routers.convert import ConversionTask
        
        # 创建任务
        task = ConversionTask(sample_task_id)
        
        # 模拟顽固进程
        mock_process = Mock()
        mock_process.is_alive.side_effect = [True, True, False]  # 第一次和第二次调用返回True，第三次返回False
        task.process = mock_process
        
        # 取消任务
        task.cancel()
        
        # 验证强制终止被调用
        assert task.status == "cancelled"
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        mock_process.join.assert_called_once()
    
    def test_conversion_task_is_cancelled(self, sample_task_id):
        """测试转换任务取消状态检查"""
        from src.routers.convert import ConversionTask
        
        task = ConversionTask(sample_task_id)
        assert not task.is_cancelled()
        
        task.status = "cancelled"
        assert task.is_cancelled()


class TestFFmpegUtils:
    """FFmpeg工具函数测试"""
    
    @patch('src.utils.ffmpeg_utils.check_ffmpeg_installed')
    @patch('src.utils.ffmpeg_utils.os.path.exists')
    @patch('src.utils.ffmpeg_utils.get_video_info')
    @patch('src.utils.ffmpeg_utils.subprocess.Popen')
    @patch('src.utils.ffmpeg_utils.os.path.getsize')
    def test_convert_video_to_audio_success(
        self, mock_getsize, mock_popen, mock_get_info, mock_exists, mock_check_ffmpeg
    ):
        """测试FFmpeg转换成功"""
        from src.utils.ffmpeg_utils import convert_video_to_audio
        
        # 设置mock
        mock_check_ffmpeg.return_value = True
        mock_exists.return_value = True
        mock_get_info.return_value = {"format": {"duration": "10.0"}}
        mock_getsize.return_value = 1024
        
        # 模拟进程 - 简化处理，直接让poll()返回0跳过while循环
        mock_process = Mock()
        mock_process.poll.return_value = 0  # 直接返回0，跳过while循环
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("", "")
        # 即使跳过while循环，也需要mock stderr.readline以防万一
        mock_stderr = Mock()
        mock_stderr.readline.return_value = ""
        mock_process.stderr = mock_stderr
        mock_popen.return_value = mock_process
        
        # 执行转换
        success, message = convert_video_to_audio(
            input_path="/tmp/input.mp4",
            output_path="/tmp/output.mp3",
            format="mp3",
            quality="medium"
        )
        
        # 验证结果
        assert success is True
        assert "Successfully converted to MP3" in message
    
    @patch('src.utils.ffmpeg_utils.check_ffmpeg_installed')
    def test_convert_video_to_audio_no_ffmpeg(self, mock_check_ffmpeg):
        """测试FFmpeg未安装"""
        from src.utils.ffmpeg_utils import convert_video_to_audio
        
        mock_check_ffmpeg.return_value = False
        
        success, message = convert_video_to_audio(
            input_path="/tmp/input.mp4",
            output_path="/tmp/output.mp3"
        )
        
        assert success is False
        assert "FFmpeg not installed" in message
    
    @patch('src.utils.ffmpeg_utils.check_ffmpeg_installed')
    @patch('src.utils.ffmpeg_utils.os.path.exists')
    def test_convert_video_to_audio_file_not_found(self, mock_exists, mock_check_ffmpeg):
        """测试输入文件不存在"""
        from src.utils.ffmpeg_utils import convert_video_to_audio
        
        mock_check_ffmpeg.return_value = True
        mock_exists.return_value = False
        
        success, message = convert_video_to_audio(
            input_path="/tmp/nonexistent.mp4",
            output_path="/tmp/output.mp3"
        )
        
        assert success is False
        assert "Input file not found" in message
    
    @patch('src.utils.ffmpeg_utils.check_ffmpeg_installed')
    @patch('src.utils.ffmpeg_utils.os.path.exists')
    @patch('src.utils.ffmpeg_utils.get_video_info')
    @patch('src.utils.ffmpeg_utils.subprocess.Popen')
    def test_convert_video_to_audio_ffmpeg_error(
        self, mock_popen, mock_get_info, mock_exists, mock_check_ffmpeg
    ):
        """测试FFmpeg转换失败"""
        from src.utils.ffmpeg_utils import convert_video_to_audio
        
        # 设置mock
        mock_check_ffmpeg.return_value = True
        mock_exists.return_value = True
        mock_get_info.return_value = {"format": {"duration": "10.0"}}
        
        # 模拟进程失败 - 直接抛出异常来模拟转换错误
        mock_popen.side_effect = Exception("Invalid codec")
        
        # 执行转换
        success, message = convert_video_to_audio(
            input_path="/tmp/input.mp4",
            output_path="/tmp/output.mp3",
            format="mp3",
            quality="medium"
        )
        
        # 验证结果
        assert success is False
        assert "Conversion error" in message
        assert "Invalid codec" in message 