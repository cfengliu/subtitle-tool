import types
from multiprocessing import Queue

import pytest


def test_format_timestamp_basic():
    from src.workers.transcribe_worker import format_timestamp

    assert format_timestamp(0.0) == "00:00:00,000"
    assert format_timestamp(1.234) == "00:00:01,234"
    assert format_timestamp(3661.5) == "01:01:01,500"


def test_add_chinese_punctuation_and_cleanup():
    from src.workers.transcribe_worker import add_chinese_punctuation

    # No punctuation initially; expect a sentence-final "。" added
    text = "这是一个测试"
    out = add_chinese_punctuation(text, "zh")
    assert out.endswith("。")
    # Should not introduce weird combos like ",。" etc.
    assert "，。" not in out and "。，" not in out


def test_transcribe_worker_zh_fallback_without_zhpr(monkeypatch):
    """Ensure zh fallback path runs without heavy deps by faking WhisperModel."""
    from src.workers import transcribe_worker as tw

    # Force zhpr path off
    monkeypatch.setattr(tw, "_ZHPR_AVAILABLE", False, raising=False)

    # Force CPU path
    monkeypatch.setattr(tw.torch.cuda, "is_available", lambda: False, raising=False)

    # Fake segment and model outputs
    class FakeSegment:
        def __init__(self, start, end, text):
            self.start = start
            self.end = end
            self.text = text

    class FakeInfo:
        language = "zh"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_path, language=None, **kwargs):
            segments = [
                FakeSegment(0.0, 1.0, "这是一个测试"),
            ]
            return iter(segments), FakeInfo()

    # Patch WhisperModel
    monkeypatch.setattr(tw, "WhisperModel", FakeModel, raising=True)

    # Prepare inputs
    result_queue = Queue()
    progress = {}
    task_id = "task-zh-fallback"

    # Run worker
    tw.transcribe_worker("/tmp/fake.wav", "zh", result_queue, progress, task_id)

    assert task_id in progress and progress[task_id] == 100
    result = result_queue.get(timeout=1)
    assert result["status"] == "completed"
    # Expect punctuation added; allow comma insertion by fallback rules
    assert result["txt"].endswith("。")
    import re
    normalized = re.sub(r"[，。！？、；：,.]", "", result["txt"])  # strip CJK punctuation
    assert normalized in ("這是一個測試", "这是一个测试")


def test_transcribe_worker_non_zh_spaces(monkeypatch):
    """Non-CJK languages should have space-separated txt output."""
    from src.workers import transcribe_worker as tw

    # Force CPU path
    monkeypatch.setattr(tw.torch.cuda, "is_available", lambda: False, raising=False)

    class FakeSegment:
        def __init__(self, start, end, text):
            self.start = start
            self.end = end
            self.text = text

    class FakeInfo:
        language = "en"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_path, language=None, **kwargs):
            segments = [
                FakeSegment(0.0, 0.5, "hello"),
                FakeSegment(0.5, 1.0, "world"),
            ]
            return iter(segments), FakeInfo()

    monkeypatch.setattr(tw, "WhisperModel", FakeModel, raising=True)

    result_queue = Queue()
    progress = {}
    task_id = "task-en"

    tw.transcribe_worker("/tmp/fake.wav", "en", result_queue, progress, task_id)

    result = result_queue.get(timeout=1)
    assert result["status"] == "completed"
    assert result["txt"] == "hello world"


def test_transcribe_worker_zh_with_zhpr_mock(monkeypatch):
    """Use a mocked zhpr restorer to punctuate Chinese text."""
    from src.workers import transcribe_worker as tw

    # Force CPU path
    monkeypatch.setattr(tw.torch.cuda, "is_available", lambda: False, raising=False)

    # Make zhpr path available and inject a lightweight fake restorer
    monkeypatch.setattr(tw, "_ZHPR_AVAILABLE", True, raising=False)

    class FakeZhPr:
        def __init__(self, device: str = "cpu"):
            self.device = device

        def punctuate(self, text: str, window_size: int = 256, step: int = 200) -> str:
            # Return already punctuated Traditional Chinese to avoid relying on OpenCC
            return "你好，這是測試嗎？"

    monkeypatch.setattr(tw, "_ZhPunctuationRestorer", FakeZhPr, raising=True)

    class FakeSegment:
        def __init__(self, start, end, text):
            self.start = start
            self.end = end
            self.text = text

    class FakeInfo:
        language = "zh"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass
        
        def transcribe(self, audio_path, language=None, **kwargs):
            segments = [
                FakeSegment(0.0, 1.0, "你好 這是測試嗎"),
            ]
            return iter(segments), FakeInfo()

    monkeypatch.setattr(tw, "WhisperModel", FakeModel, raising=True)

    result_queue = Queue()
    progress = {}
    task_id = "task-zh-zhpr"

    tw.transcribe_worker("/tmp/fake.wav", "zh", result_queue, progress, task_id)

    result = result_queue.get(timeout=1)
    assert result["status"] == "completed"
    # Expect zhpr output preserved (and/or OpenCC no-op) with punctuation
    assert result["txt"] == "你好，這是測試嗎？"
    assert "你好，這是測試嗎？" in result["srt"]


def test_transcribe_worker_zh_question_mark_fallback(monkeypatch):
    """Fallback rules add a question mark for interrogatives like '吗'."""
    from src.workers import transcribe_worker as tw

    # Disable zhpr so fallback regex-based punctuation runs
    monkeypatch.setattr(tw, "_ZHPR_AVAILABLE", False, raising=False)
    monkeypatch.setattr(tw.torch.cuda, "is_available", lambda: False, raising=False)

    class FakeSegment:
        def __init__(self, start, end, text):
            self.start = start
            self.end = end
            self.text = text

    class FakeInfo:
        language = "zh"

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio_path, language=None, **kwargs):
            segments = [
                FakeSegment(0.0, 1.0, "你好吗"),
            ]
            return iter(segments), FakeInfo()

    monkeypatch.setattr(tw, "WhisperModel", FakeModel, raising=True)

    result_queue = Queue()
    progress = {}
    task_id = "task-zh-qmark"

    tw.transcribe_worker("/tmp/fake.wav", "zh", result_queue, progress, task_id)

    result = result_queue.get(timeout=1)
    assert result["status"] == "completed"
    # Should end with a full-width question mark; allow either Traditional or Simplified
    assert result["txt"].endswith("？")
    assert ("嗎" in result["txt"]) or ("吗" in result["txt"])
