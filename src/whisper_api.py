from faster_whisper import WhisperModel
from fastapi import FastAPI, UploadFile, File
import tempfile
import os

# 初始化 Whisper 模型
model = WhisperModel("medium", device="cuda", compute_type="float16")  # GPU
# model = WhisperModel("medium", device="cpu", compute_type="int8")  # CPU

app = FastAPI()

@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)):
    # 暫存檔案
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio_path = temp_audio.name

    # 轉錄音頻
    segments, _ = model.transcribe(temp_audio_path)
    transcript = " ".join(segment.text for segment in segments)

    # 刪除暫存文件
    os.remove(temp_audio_path)

    return {"transcript": transcript}

# 運行 FastAPI
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)