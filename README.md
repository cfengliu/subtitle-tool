# Subtitles Tool Monorepo（字幕工具）

這是一個語音轉文字的字幕工具 monorepo，整合：
* 🎧 api/：使用 FastAPI 與 Faster Whisper 的音訊轉錄後端
* 🖥️ frontend/：使用 Next.js 15 與 React 19 實作的字幕上傳與顯示介面

本專案使用 pnpm workspace 管理各子模組，方便統一依賴與指令管理。

## 📁 專案結構
```
subtitles-tool/
├── api/                          # 後端服務（Python FastAPI）
│   ├── requirements.txt
│   ├── src/
│   │   ├── whisper_api.py       # API 主入口
│   │   ├── routers/             # API 路由
│   │   ├── workers/             # 背景處理任務
│   │   └── utils/               # 工具函式
│   └── tests/                   # 測試檔案
│
├── frontend/                     # Next.js 前端
│   ├── public/
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   └── components/          # React 元件
│   ├── package.json
│   └── tsconfig.json
│
├── package.json                  # root package，使用 pnpm workspace 管理
├── pnpm-lock.yaml
├── CLAUDE.md                     # Claude Code 專案指引
├── README.md
└── LICENSE
```

## 🔧 快速開始

### 初始化項目

1. 安裝依賴：
```bash
# 使用 pnpm 安裝所有依賴（包括前端和 concurrently）
pnpm install
```

2. 構建項目：
```bash
# 構建前端和安裝 API 的 Python 依賴
pnpm run build:all
```

3. 啟動開發環境：
```bash
# 同時啟動前端和 API 服務（開發模式）
pnpm run dev:all
```

這將同時啟動：
- 前端服務：http://localhost:8002
- API 服務：http://localhost:8010

### 生產環境部署

```bash
# 啟動生產模式（包含音訊清理服務）
pnpm run start:all
```

## 📦 pnpm workspace 設定

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
    "dev:fe": "pnpm --filter frontend run dev --port 8002",
    "dev:api": "uvicorn api.src.whisper_api:app --host 0.0.0.0 --port 8010 --reload",
    "dev:all": "concurrently \"pnpm run dev:fe\" \"pnpm run dev:api\"",
    "build:fe": "pnpm install && pnpm --filter frontend run build",
    "build:api": "cd api && pip install -r requirements.txt",
    "build:all": "pnpm run build:fe && pnpm run build:api",
    "start:fe": "pnpm --filter frontend run start --port 8002",
    "start:api": "uvicorn api.src.whisper_api:app --port 8010 --workers 1",
    "start:all": "concurrently -k \"pnpm run start:fe\" \"pnpm run start:api\" \"pnpm run cleanup:audio\"",
    "cleanup:audio": "python -m api.src.cleanup_service"
  },
  "devDependencies": {
    "concurrently": "^8.2.0"
  }
}
```

你可以透過 root 執行 workspace 指令，例如：
```bash
pnpm run dev:fe          # 只啟動前端開發伺服器
pnpm run dev:api         # 只啟動 API 開發伺服器
pnpm run dev:all         # 同時啟動前後端開發伺服器
pnpm run build:fe        # 只構建前端
pnpm run build:api       # 只安裝 API 依賴
pnpm run build:all       # 構建所有項目
pnpm --filter frontend add some-package  # 為前端安裝特定包
```

## 🔧 使用說明

### 一、單獨運行後端（api/）

```bash
cd api
pip install -r requirements.txt
uvicorn src.whisper_api:app --host 0.0.0.0 --port 8010
```

POST 測試：
```bash
curl -X POST "http://localhost:8010/transcribe/" -F "file=@path/to/audio.mp3"
```

### 二、單獨運行前端（frontend/）

```bash
pnpm install            # 從 root 安裝所有 workspace 相依
pnpm run dev:fe         # 啟動前端（http://localhost:8002）
```

## 🧪 測試

### 前端測試
```bash
# Lint 前端程式碼
pnpm --filter frontend run lint
```

### 後端測試
```bash
# 執行所有 Python 測試
cd api && python run_tests.py

# 執行特定測試類別
cd api && python run_tests.py api        # API 端點測試
cd api && python run_tests.py utils      # 工具函式測試
cd api && python run_tests.py models     # 模型類別測試

# 使用 pytest 直接執行
cd api && pytest                         # 所有測試
cd api && pytest tests/test_utils.py -v  # 特定測試檔案
cd api && pytest -m "unit" -v            # 只執行單元測試
cd api && pytest -m "api" -v             # 只執行 API 測試
```

## 🎯 主要功能

- 🎤 音訊轉文字（支援多種音訊格式）
- 🎬 影片轉音訊（自動提取音軌）
- 📝 字幕產生（SRT 格式）
- 🔊 降噪處理（可選功能）
- 📊 即時任務進度追蹤
- 🧹 自動清理臨時檔案

## 🛠 技術堆疊

### 後端
- FastAPI：現代化的 Python Web 框架
- Faster Whisper：高效能語音辨識引擎
- FFmpeg：音訊/影片處理
- Multiprocessing：背景任務處理

### 前端
- Next.js 15：React 框架（App Router）
- React 19：使用者介面函式庫
- TypeScript：型別安全
- Tailwind CSS：樣式框架
- Radix UI：無障礙元件基礎

## 🧱 建議擴充

* 加入 @types/shared 資料夾來共享 TS 型別
* 加入 electron/ 或 mobile/ 資料夾實作桌面或行動版本
* 加入 scripts/ 夾儲存轉檔工具等 CLI 工具
* 整合更多語言模型支援
