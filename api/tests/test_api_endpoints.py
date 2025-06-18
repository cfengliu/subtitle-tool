"""
测试API端点
"""
import pytest
from unittest.mock import patch, Mock
from fastapi import status


class TestHealthEndpoint:
    """健康检查端点测试"""
    
    def test_health_check_success(self, client):
        """测试健康检查成功"""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "API 服務運行正常" in data["message"]


class TestTranscribeEndpoints:
    """转录相关端点测试"""
    
    @patch('src.whisper_api.concurrent_semaphore')
    @patch('src.whisper_api.Process')
    @patch('src.whisper_api.Manager')
    @patch('src.whisper_api.Queue')
    def test_start_transcription_success(
        self, mock_queue, mock_manager, mock_process, mock_semaphore,
        client, sample_audio_file
    ):
        """测试启动转录任务成功"""
        # 设置mock
        mock_semaphore.acquire.return_value = True
        mock_manager_instance = Mock()
        mock_manager.return_value = mock_manager_instance
        mock_manager_instance.dict.return_value = {}
        mock_process.return_value = Mock()
        
        # 发送请求
        response = client.post(
            "/transcribe/",
            files=sample_audio_file,
            data={"language": "zh"}
        )
        
        # 验证响应
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "started"
        assert data["message"] == "轉錄任務已啟動"
    
    @patch('src.whisper_api.concurrent_semaphore')
    def test_start_transcription_concurrent_limit(
        self, mock_semaphore, client, sample_audio_file
    ):
        """测试并发限制"""
        mock_semaphore.acquire.return_value = False
        
        response = client.post("/transcribe/", files=sample_audio_file)
        
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Too many concurrent transcription requests" in response.json()["detail"]
    
    def test_get_task_status_not_found(self, client, sample_task_id):
        """测试获取不存在任务的状态"""
        response = client.get(f"/transcribe/{sample_task_id}/status")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "任務不存在"
    
    @patch('src.whisper_api.active_tasks')
    def test_get_task_status_running(
        self, mock_active_tasks, client, sample_task_id, mock_active_task_data
    ):
        """测试获取运行中任务状态"""
        mock_active_tasks.__contains__.return_value = True
        mock_active_tasks.__getitem__.return_value = mock_active_task_data
        
        response = client.get(f"/transcribe/{sample_task_id}/status")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == sample_task_id
        assert data["status"] == "running"
        assert "progress" in data
        assert "filename" in data
    
    def test_get_task_result_not_found(self, client, sample_task_id):
        """测试获取不存在任务的结果"""
        response = client.get(f"/transcribe/{sample_task_id}/result")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "任務不存在"
    
    @patch('src.whisper_api.task_results')
    def test_get_task_result_completed(
        self, mock_task_results, client, sample_task_id, sample_transcription_result
    ):
        """测试获取已完成任务结果"""
        mock_task_results.__contains__.return_value = True
        mock_task_results.__getitem__.return_value = sample_transcription_result
        mock_task_results.__delitem__ = Mock()
        
        response = client.get(f"/transcribe/{sample_task_id}/result")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["srt"] == sample_transcription_result["srt"]
        assert data["txt"] == sample_transcription_result["txt"]
        assert data["detected_language"] == "zh"
        assert data["status"] == "completed"
    
    @patch('src.whisper_api.active_tasks')
    def test_get_task_result_still_running(
        self, mock_active_tasks, client, sample_task_id
    ):
        """测试获取仍在运行任务的结果"""
        mock_task = Mock()
        mock_task.status = "running"
        
        mock_active_tasks.__contains__.return_value = True
        mock_active_tasks.__getitem__.return_value = {"task": mock_task}
        
        response = client.get(f"/transcribe/{sample_task_id}/result")
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["detail"] == "任務仍在進行中"
    
    def test_cancel_task_not_found(self, client, sample_task_id):
        """测试取消不存在的任务"""
        response = client.post(f"/transcribe/{sample_task_id}/cancel")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "任務不存在或已完成"
    
    @patch('src.whisper_api.active_tasks')
    def test_cancel_task_success(
        self, mock_active_tasks, client, sample_task_id
    ):
        """测试成功取消任务"""
        mock_task = Mock()
        mock_active_tasks.__contains__.return_value = True
        mock_active_tasks.__getitem__.return_value = {"task": mock_task}
        
        response = client.post(f"/transcribe/{sample_task_id}/cancel")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == sample_task_id
        assert data["status"] == "cancelled"
        assert data["message"] == "任務已被強制終止"
        mock_task.cancel.assert_called_once()
    
    def test_list_active_tasks_empty(self, client):
        """测试列出空的活跃任务"""
        response = client.get("/transcribe/tasks")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "active_tasks" in data
        assert isinstance(data["active_tasks"], list)
    
    @patch('src.whisper_api.active_tasks')
    def test_list_active_tasks_with_data(self, mock_active_tasks, client):
        """测试列出有数据的活跃任务"""
        task_id1 = "task-1"
        task_id2 = "task-2"
        
        mock_task1 = Mock()
        mock_task1.status = "running"
        mock_task2 = Mock()
        mock_task2.status = "running"
        
        # 创建mock的progress_dict，模拟实际的字典行为
        mock_progress_dict1 = Mock()
        mock_progress_dict1.get.return_value = 30
        
        mock_progress_dict2 = Mock()
        mock_progress_dict2.get.return_value = 70
        
        # 模拟active_tasks的结构和访问模式
        task_info1 = {
            "task": mock_task1,
            "progress_dict": mock_progress_dict1,
            "filename": "audio1.mp3"
        }
        task_info2 = {
            "task": mock_task2,
            "progress_dict": mock_progress_dict2,
            "filename": "audio2.mp3"
        }
        
        mock_active_tasks.items.return_value = [
            (task_id1, task_info1),
            (task_id2, task_info2)
        ]
        
        # 模拟通过key访问的行为
        def mock_getitem(key):
            if key == task_id1:
                return task_info1
            elif key == task_id2:
                return task_info2
            else:
                raise KeyError(key)
        
        mock_active_tasks.__getitem__.side_effect = mock_getitem
        
        response = client.get("/transcribe/tasks")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["active_tasks"]) == 2
        
        # 验证任务数据
        tasks = {task["task_id"]: task for task in data["active_tasks"]}
        assert tasks[task_id1]["status"] == "running"
        assert tasks[task_id1]["progress"] == 30
        assert tasks[task_id2]["progress"] == 70 