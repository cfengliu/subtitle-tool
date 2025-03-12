# subtitle-tool

## 使用方法

1. **启动服务**:
   在项目目录中运行以下命令以启动 FastAPI 服务：

   ```bash
   uvicorn src.whisper_api:app --host 0.0.0.0 --port 8000
   ```

2. **发送音频文件**:
   使用 POST 请求将音频文件发送到 `/transcribe/` 端点。可以使用工具如 Postman 或 curl 进行测试。

   示例 curl 命令：

   ```bash
   curl -X POST "http://localhost:8000/transcribe/" -F "file=@path/to/your/audio.mp3"
   ```

3. **获取转录结果**:
   服务将返回一个 JSON 响应，包含转录文本：

   ```json
   {
       "transcript": "转录的文本内容"
   }
   ```

## 注意事项

- 确保你的环境中安装了 CUDA 工具包（如果使用 GPU 版本的 Faster Whisper）。
- 可以根据需要修改 `src/whisper_api.py` 中的模型配置。

## 许可证

此项目使用 MIT 许可证。请查看 LICENSE 文件以获取更多信息。
 
