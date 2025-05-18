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
├── package.json                  # root package，使用 npm workspace 管理 frontend 和 api
├── README.md
└── LICENSE
```

## 🔧 快速開始

### 初始化項目

1. 安裝依賴：
```bash
# 安裝 npm 依賴（包括前端和 concurrently）
npm install
```

2. 構建項目：
```bash
# 構建前端和安裝 API 的 Python 依賴
npm run build:all
```

3. 啟動項目：
```bash
# 同時啟動前端和 API 服務
npm run start:all
```

這將同時啟動：
- 前端服務：http://localhost:3000（或您配置的端口）
- API 服務：http://localhost:8000（uvicorn 默認端口）

## 📦 npm workspace 設定

package.json（root）內容範例如下：
```json
{
  "name": "subtitles-tool",
  "private": true,
  "workspaces": [
    "frontend",
    "api"
  ],
  "scripts": {
    "dev": "npm --workspace frontend run dev",
    "build": "npm --workspace frontend run build",
    "dev:api": "cd api && uvicorn src.whisper_api:app --reload",
    "build:api": "cd api && pip install -r requirements.txt",
    "start:all": "concurrently \"npm run dev\" \"npm run dev:api\"",
    "build:all": "npm run build && npm run build:api"
  },
  "devDependencies": {
    "concurrently": "^8.2.0"
  }
}
```

你可以透過 root 執行 workspace 指令，例如：
```bash
npm run dev          # 只啟動前端
npm run dev:api      # 只啟動 API
npm run build        # 只構建前端
npm run build:api    # 只安裝 API 依賴
npm install -w frontend some-package  # 為前端安裝特定包
```

## 🔧 使用說明

### 一、單獨運行後端（api/）

```bash
cd api
pip install -r requirements.txt
uvicorn src.whisper_api:app --host 0.0.0.0 --port 8000
```

POST 測試：
```bash
curl -X POST "http://localhost:8000/transcribe/" -F "file=@path/to/audio.mp3"
```

### 二、單獨運行前端（frontend/）

```bash
npm install            # 從 root 安裝所有 workspace 相依
npm run dev            # 啟動前端（http://localhost:3000）
```

## 🧱 建議擴充

* 加入 @types/shared 資料夾來共享 TS 型別
* 加入 electron/ 或 mobile/ 資料夾實作桌面或行動版本
* 加入 scripts/ 夾儲存轉檔工具等 CLI 工具

📝 授權

本專案使用 MIT 授權，詳見 LICENSE 檔案。