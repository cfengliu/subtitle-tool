# Subtitles Tool Monorepo（字幕工具）

這是一個語音轉文字的字幕工具 monorepo，整合：
* 🎧 api/：使用 FastAPI 與 Faster Whisper 的音訊轉錄後端
* 🖥️ frontend/：使用 React 實作的字幕上傳與顯示介面

本專案使用 npm workspace 管理各子模組，方便統一依賴與指令管理。

## 📁 專案結構
```
subtitles-tool/
├── api/                          # 後端服務（非 Node 專案）
│   ├── requirements.txt
│   └── src/
│       └── whisper_api.py
│
├── frontend/                     # React 前端
│   ├── public/
│   ├── src/
│   │   └── App.tsx
│   ├── package.json
│   └── tsconfig.json
│
├── package.json                  # root package，使用 npm workspace 管理 frontend
├── README.md
└── LICENSE
```
## 📦 npm workspace 設定

package.json（root）內容範例如下：
```
{
  "name": "subtitles-tool",
  "private": true,
  "workspaces": [
    "frontend"
  ],
  "scripts": {
    "dev": "npm --workspace frontend run dev",
    "build": "npm --workspace frontend run build"
  }
}
```

你可以透過 root 執行 workspace 指令，例如：
```
npm run dev
npm install -w frontend some-package
```

## 🔧 使用說明

### 一、後端（api/）

```
cd api
pip install -r requirements.txt
uvicorn src.whisper_api:app --host 0.0.0.0 --port 8000
```

POST 測試：
```
curl -X POST "http://localhost:8000/transcribe/" -F "file=@path/to/audio.mp3"
```

### 二、前端（frontend/）

```
npm install            # 從 root 安裝所有 workspace 相依
npm run dev            # 啟動前端（http://localhost:3000）
```

## 🧱 建議擴充

* 加入 @types/shared 資料夾來共享 TS 型別
* 加入 electron/ 或 mobile/ 資料夾實作桌面或行動版本
* 加入 scripts/ 夾儲存轉檔工具等 CLI 工具

📝 授權

本專案使用 MIT 授權，詳見 LICENSE 檔案。