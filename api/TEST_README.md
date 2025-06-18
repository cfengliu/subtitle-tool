# 字幕转录API测试文档

## 概述

这是一个结构化的测试套件，采用Python测试最佳实践，为字幕转录API提供全面的单元测试覆盖。

## 测试结构

```
api/
├── tests/                    # 测试包
│   ├── __init__.py          # 包初始化
│   ├── conftest.py          # pytest配置和fixtures
│   ├── test_utils.py        # 工具函数测试
│   ├── test_models.py       # 模型类测试
│   └── test_api_endpoints.py # API端点测试
├── pytest.ini              # pytest配置文件
├── run_tests.py            # 测试运行脚本
└── requirements.txt        # 依赖包列表
```

## 测试分类

### 1. 工具函数测试 (`test_utils.py`)
- **时间戳格式化** - 测试SRT格式时间戳转换
- **简繁转换** - 测试中文简体转繁体功能  
- **标点符号处理** - 测试自动添加中文标点符号

### 2. 模型类测试 (`test_models.py`)
- **任务初始化** - 测试TranscriptionTask类创建
- **任务取消** - 测试任务取消和进程管理
- **状态转换** - 测试任务状态变化

### 3. API端点测试 (`test_api_endpoints.py`)
- **健康检查** - `/health` 端点测试
- **转录任务管理** - 所有转录相关端点测试
- **错误处理** - 各种错误情况的处理

## 测试特点

### ✅ 遵循最佳实践
- **清晰的测试结构** - 按功能模块分离测试文件
- **Fixtures重用** - 在`conftest.py`中定义通用测试数据
- **参数化测试** - 使用`@pytest.mark.parametrize`减少重复代码
- **Mock隔离** - 使用unittest.mock隔离外部依赖

### ✅ 完整的测试覆盖
- **正向用例** - 测试正常功能流程
- **边界条件** - 测试边界值和特殊情况
- **错误处理** - 测试各种错误情况
- **状态管理** - 测试对象状态转换

### ✅ 快速执行
- **无重型依赖** - 使用Mock避免加载Whisper模型
- **并行执行** - 支持pytest并行测试
- **选择性运行** - 支持按标签或模块运行测试

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `pytest` - 测试框架
- `httpx` - HTTP客户端（FastAPI TestClient需要）
- `opencc-python-reimplemented` - 简繁转换

## 运行测试

### 使用测试运行脚本（推荐）

```bash
# 运行所有测试
python run_tests.py

# 运行特定类型测试
python run_tests.py api        # API端点测试
python run_tests.py utils      # 工具函数测试  
python run_tests.py models     # 模型类测试

# 运行特定测试文件
python run_tests.py tests/test_utils.py

# 显示帮助
python run_tests.py help
```

### 使用pytest直接运行

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_utils.py -v

# 运行特定测试类
pytest tests/test_api_endpoints.py::TestHealthEndpoint -v

# 运行特定测试方法
pytest tests/test_utils.py::TestUtilityFunctions::test_format_timestamp_zero -v

# 按标签运行测试
pytest -m "unit" -v
pytest -m "api" -v
```

### 高级测试选项

```bash
# 显示测试覆盖率
pytest --cov=src --cov-report=html

# 并行运行测试
pytest -n auto

# 只运行失败的测试
pytest --lf

# 停止在第一个失败
pytest -x

# 详细输出
pytest -vvv
```

## 测试输出示例

```
==================== test session starts ====================
platform darwin -- Python 3.10.14, pytest-6.2.5
rootdir: /path/to/api, configfile: pytest.ini
collected 25 items

tests/test_utils.py::TestUtilityFunctions::test_format_timestamp_zero PASSED     [ 4%]
tests/test_utils.py::TestUtilityFunctions::test_format_timestamp_minutes PASSED [ 8%]
tests/test_utils.py::TestUtilityFunctions::test_format_timestamp_parametrized[0-00:00:00,000] PASSED [12%]
tests/test_models.py::TestTranscriptionTask::test_task_initialization PASSED    [16%]
tests/test_models.py::TestTranscriptionTask::test_task_cancel_without_process PASSED [20%]
tests/test_api_endpoints.py::TestHealthEndpoint::test_health_check_success PASSED [24%]
tests/test_api_endpoints.py::TestTranscribeEndpoints::test_start_transcription_success PASSED [28%]
...

==================== 25 passed in 1.23s ====================
```

## Fixtures说明

### 通用Fixtures (`conftest.py`)

- `client` - FastAPI测试客户端
- `sample_task_id` - 示例任务ID
- `sample_audio_file` - 模拟音频文件
- `mock_transcription_task` - 模拟转录任务对象
- `mock_process` - 模拟进程对象
- `sample_transcription_result` - 示例转录结果

### 使用示例

```python
def test_example(client, sample_task_id, sample_audio_file):
    """使用fixtures的测试示例"""
    response = client.post("/transcribe/", files=sample_audio_file)
    assert response.status_code == 200
```

## 测试标记

使用pytest标记来分类测试：

```python
@pytest.mark.unit
def test_utility_function():
    """单元测试"""
    pass

@pytest.mark.api  
def test_api_endpoint():
    """API测试"""
    pass

@pytest.mark.slow
def test_heavy_operation():
    """慢速测试"""
    pass
```

## 扩展测试

### 添加新测试

1. **新功能测试**：在相应的测试文件中添加测试方法
2. **新模块测试**：创建新的`test_*.py`文件
3. **新Fixtures**：在`conftest.py`中添加通用测试数据

### 集成测试

```python
# tests/test_integration.py
@pytest.mark.integration
def test_full_transcription_flow():
    """完整转录流程集成测试"""
    # 需要真实音频文件和模型
    pass
```

### 性能测试

```python
# tests/test_performance.py
@pytest.mark.slow
def test_concurrent_requests():
    """并发请求性能测试"""
    pass
```

## 最佳实践

### ✅ 推荐做法

1. **测试命名** - 使用描述性的测试方法名
2. **单一职责** - 每个测试只验证一个功能点
3. **独立测试** - 测试之间不应有依赖关系
4. **Mock外部依赖** - 隔离外部服务和重型操作
5. **参数化测试** - 对类似逻辑使用参数化减少重复

### ❌ 避免做法

1. **测试间依赖** - 不要让测试依赖其他测试的结果
2. **硬编码数据** - 使用fixtures而不是硬编码测试数据
3. **过度Mock** - 不要Mock被测试的代码本身
4. **忽略异常** - 确保测试异常情况和错误处理

## 持续集成

### GitHub Actions示例

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Run tests
      run: |
        python run_tests.py
```

## 故障排除

### 常见问题

1. **导入错误** - 检查Python路径和模块导入
2. **Fixture未找到** - 确保`conftest.py`在正确位置
3. **Mock失效** - 检查Mock的路径和调用方式
4. **测试超时** - 使用Mock避免实际的重型操作

### 调试技巧

```bash
# 详细输出调试信息
pytest -vvv --tb=long

# 进入调试器
pytest --pdb

# 只运行失败的测试
pytest --lf -vvv
``` 