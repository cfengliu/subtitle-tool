"""
测试工具函数模块
"""
import pytest
from src.whisper_api import (
    format_timestamp,
    convert_to_traditional_chinese,
    add_chinese_punctuation
)


class TestUtilityFunctions:
    """工具函数测试类"""
    
    def test_format_timestamp_zero(self):
        """测试零时间戳"""
        assert format_timestamp(0.0) == "00:00:00,000"
    
    def test_format_timestamp_minutes(self):
        """测试分钟级时间戳"""
        assert format_timestamp(65.5) == "00:01:05,500"
    
    def test_format_timestamp_hours(self):
        """测试小时级时间戳"""
        assert format_timestamp(3661.123) == "01:01:01,123"
    
    def test_format_timestamp_milliseconds(self):
        """测试毫秒精度"""
        assert format_timestamp(7323.998) == "02:02:03,997"
        assert format_timestamp(1.123) == "00:00:01,123"
    
    @pytest.mark.parametrize("seconds,expected", [
        (0, "00:00:00,000"),
        (1, "00:00:01,000"),
        (60, "00:01:00,000"),
        (3600, "01:00:00,000"),
        (3661.5, "01:01:01,500"),
    ])
    def test_format_timestamp_parametrized(self, seconds, expected):
        """参数化测试时间戳格式化"""
        assert format_timestamp(seconds) == expected


class TestChineseTextProcessing:
    """中文文本处理测试类"""
    
    def test_convert_traditional_unchanged(self):
        """测试繁体字保持不变"""
        assert convert_to_traditional_chinese("你好") == "你好"
    
    def test_convert_simplified_to_traditional(self):
        """测试简体转繁体"""
        assert convert_to_traditional_chinese("学习") == "學習"
        assert convert_to_traditional_chinese("计算机") == "計算機"
    
    def test_convert_empty_string(self):
        """测试空字符串"""
        assert convert_to_traditional_chinese("") == ""
    
    def test_convert_mixed_text(self):
        """测试混合文本"""
        result = convert_to_traditional_chinese("我在学习计算机")
        assert "學習" in result
        assert "計算機" in result
    
    def test_add_punctuation_chinese(self):
        """测试中文标点符号添加"""
        text = "你好吧这是测试"
        result = add_chinese_punctuation(text, "zh")
        # 应该包含某种标点符号
        assert any(punct in result for punct in ["，", "。", "！", "？"])
    
    def test_add_punctuation_non_chinese(self):
        """测试非中文语言不处理"""
        english_text = "Hello world"
        result = add_chinese_punctuation(english_text, "en")
        assert result == english_text
    
    def test_add_punctuation_already_punctuated(self):
        """测试已有标点符号的文本"""
        punctuated_text = "你好，这是测试。"
        result = add_chinese_punctuation(punctuated_text, "zh")
        assert result == punctuated_text
    
    def test_add_punctuation_empty_text(self):
        """测试空文本"""
        assert add_chinese_punctuation("", "zh") == ""
    
    def test_add_punctuation_none_language(self):
        """测试language为None的情况"""
        text = "测试文本"
        result = add_chinese_punctuation(text, None)
        assert result == text 