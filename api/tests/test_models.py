"""
测试模型类
"""
import pytest
from unittest.mock import Mock
from src.whisper_api import TranscriptionTask


class TestTranscriptionTask:
    """转录任务类测试"""
    
    def test_task_initialization(self, sample_task_id):
        """测试任务初始化"""
        task = TranscriptionTask(sample_task_id)
        
        assert task.task_id == sample_task_id
        assert task.status == "running"
        assert task.progress == 0
        assert task.process is None
        assert not task.is_cancelled()
    
    def test_task_cancel_without_process(self, sample_task_id):
        """测试没有进程时的取消操作"""
        task = TranscriptionTask(sample_task_id)
        task.cancel()
        
        assert task.status == "cancelled"
        assert task.is_cancelled()
    
    def test_task_cancel_with_running_process(self, sample_task_id, mock_process):
        """测试有运行进程时的取消操作"""
        task = TranscriptionTask(sample_task_id)
        task.process = mock_process
        
        task.cancel()
        
        assert task.status == "cancelled"
        assert task.is_cancelled()
        mock_process.terminate.assert_called_once()
    
    def test_task_cancel_with_stubborn_process(self, sample_task_id):
        """测试顽固进程的强制终止"""
        task = TranscriptionTask(sample_task_id)
        
        # 模拟一个不会被terminate的进程
        stubborn_process = Mock()
        stubborn_process.is_alive.side_effect = [True, True, False]  # 第三次调用返回False
        task.process = stubborn_process
        
        task.cancel()
        
        assert task.status == "cancelled"
        stubborn_process.terminate.assert_called_once()
        stubborn_process.kill.assert_called_once()
    
    def test_task_status_transitions(self, sample_task_id):
        """测试任务状态转换"""
        task = TranscriptionTask(sample_task_id)
        
        # 初始状态
        assert task.status == "running"
        assert not task.is_cancelled()
        
        # 取消后状态
        task.cancel()
        assert task.status == "cancelled"
        assert task.is_cancelled()
    
    def test_task_with_dead_process(self, sample_task_id):
        """测试已死亡进程的处理"""
        task = TranscriptionTask(sample_task_id)
        
        dead_process = Mock()
        dead_process.is_alive.return_value = False
        task.process = dead_process
        
        task.cancel()
        
        assert task.status == "cancelled"
        # 死亡进程不应该被terminate
        dead_process.terminate.assert_not_called()
        dead_process.kill.assert_not_called() 