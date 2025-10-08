# 📋 語音服務 Monorepo 改造 PRD

## 1. 項目背景

### 現狀
- 已有 Whisper STT (語音轉文字) 服務運行
- 採用 monorepo 架構（API + Frontend）
- 需要擴展 TTS (文字轉語音) 功能

### 目標
將語音服務改造為統一的 monorepo 平台，支持 STT 和 TTS 雙向語音處理能力

---

## 2. 架構設計

### 2.1 目錄結構
```
speech-services/
├── pnpm-workspace.yaml
├── README.md
├── CHANGELOG.md
│
├── api/                          # Python 後端服務
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── src/
│   │   ├── main.py              # FastAPI 主應用
│   │   ├── config.py            # 配置管理
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── stt.py           # STT 路由
│   │   │   └── tts.py           # TTS 路由（新增）
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── transcribe_worker.py
│   │   │   └── tts_worker.py    # 新增
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── stt_models.py
│   │   │   └── tts_models.py    # 新增
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── audio_utils.py   # 共用音頻處理
│   │   │   ├── file_utils.py
│   │   │   └── validation.py
│   │   └── cleanup_service.py
│   └── tests/
│       ├── test_stt_endpoints.py
│       ├── test_tts_endpoints.py # 新增
│       └── test_audio_utils.py
│
├── frontend/                     # Next.js 前端
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── stt/            # STT 頁面
│   │   │   ├── tts/            # TTS 頁面（新增）
│   │   │   └── dashboard/      # 統一儀表板（新增）
│   │   ├── components/
│   │   │   ├── stt/
│   │   │   ├── tts/            # 新增
│   │   │   └── shared/         # 共用組件
│   │   ├── contexts/
│   │   │   └── AudioContext.tsx # 共用音頻狀態
│   │   └── lib/
│   │       └── api-client.ts    # 統一 API 客戶端
│   └── styles/
│
├── shared/                       # 共用代碼（可選）
│   ├── types/                   # TypeScript 類型定義
│   │   ├── stt.ts
│   │   └── tts.ts
│   └── constants/               # 共用常量
│
└── docs/                        # 文檔
    ├── API.md
    ├── DEPLOYMENT.md
    └── DEVELOPMENT.md
```

---

## 3. 功能需求

### 3.1 核心功能

#### STT (現有功能保留)
- ✅ 音頻文件上傳
- ✅ Whisper 模型轉錄
- ✅ 支持多語言
- ✅ WebSocket 實時進度

#### TTS (新增功能)
- 🆕 文字轉語音
- 🆕 多種聲音選擇
- 🆕 語速、音調控制
- 🆕 支持 SSML 標記
- 🆕 音頻格式選擇 (MP3/WAV/OGG)

#### 共用功能
- 🆕 統一的文件管理
- 🆕 任務隊列和狀態追蹤
- 🆕 使用量統計儀表板
- 🆕 錯誤處理和重試機制

### 3.2 前端功能

```
Dashboard (新增)
├── 服務總覽
├── 使用統計
└── 最近任務

STT 頁面
├── 文件上傳區
├── 實時轉錄顯示
└── 結果下載

TTS 頁面 (新增)
├── 文字輸入區
├── 聲音參數設置
├── 即時預聽
└── 音頻下載
```

---

## 4. 技術規格

### 4.1 API 端點設計

#### STT API (現有)
```python
POST   /api/v1/stt/transcribe      # 轉錄音頻
GET    /api/v1/stt/status/{job_id} # 查詢狀態
GET    /api/v1/stt/result/{job_id} # 獲取結果
WS     /api/v1/stt/ws/{job_id}     # WebSocket 連接
```

#### TTS API (新增)
```python
POST   /api/v1/tts/synthesize      # 合成語音
GET    /api/v1/tts/status/{job_id} # 查詢狀態
GET    /api/v1/tts/audio/{job_id}  # 下載音頻
GET    /api/v1/tts/voices           # 獲取可用聲音列表
```

#### 共用 API
```python
GET    /api/v1/health              # 健康檢查
GET    /api/v1/stats               # 使用統計
DELETE /api/v1/cleanup             # 清理臨時文件
```

### 4.2 數據模型

#### TTS Request (新增)
```python
class TTSRequest(BaseModel):
    text: str
    voice: str = "default"
    speed: float = 1.0        # 0.5 - 2.0
    pitch: float = 1.0        # 0.5 - 2.0
    format: str = "mp3"       # mp3/wav/ogg
    ssml: bool = False        # 是否使用 SSML
```

#### Job Status (統一)
```python
class JobStatus(BaseModel):
    job_id: str
    type: str                 # "stt" or "tts"
    status: str              # pending/processing/completed/failed
    progress: float          # 0-100
    created_at: datetime
    completed_at: Optional[datetime]
    result_url: Optional[str]
    error: Optional[str]
```

### 4.3 技術選型

**後端**
- FastAPI (現有)
- Celery/RQ (任務隊列) - 新增
- Redis (快取 & 隊列) - 新增
- TTS 引擎選擇：
  - Option 1: Coqui TTS (開源)
  - Option 2: ElevenLabs API (商業)
  - Option 3: Azure TTS (穩定)

**前端**
- Next.js 15 (現有)
- shadcn/ui (現有)
- Zustand (狀態管理) - 新增
- React Query (API 狀態) - 新增

---

## 5. 實施計劃

### Phase 1: 基礎架構 (Week 1)
- [ ] 重構 API 目錄結構
- [ ] 建立 routers 模塊化架構
- [ ] 設置 Redis 和任務隊列
- [ ] 統一配置管理

### Phase 2: TTS 後端 (Week 2)
- [ ] 實現 TTS router 和 endpoints
- [ ] 開發 TTS worker
- [ ] 音頻生成和格式轉換
- [ ] 編寫單元測試

### Phase 3: 前端整合 (Week 3)
- [ ] 建立 TTS 頁面和組件
- [ ] 實現統一 Dashboard
- [ ] 共用組件抽取
- [ ] API 客戶端統一

### Phase 4: 優化和測試 (Week 4)
- [ ] 性能優化
- [ ] 端到端測試
- [ ] 文檔完善
- [ ] 部署準備

---

## 6. 成功指標

### 技術指標
- ✅ API 響應時間 < 200ms (非處理接口)
- ✅ TTS 生成時間 < 5s (100 字以內)
- ✅ 測試覆蓋率 > 80%
- ✅ 錯誤率 < 1%

### 開發指標
- ✅ 代碼復用率 > 30%
- ✅ 部署時間 < 10 分鐘
- ✅ 新功能開發週期縮短 40%

---

## 7. 風險和挑戰

### 技術風險
1. **TTS 模型選擇**
   - 緩解：先做 POC 比較不同方案
   
2. **任務隊列穩定性**
   - 緩解：實現重試機制和監控

3. **音頻文件存儲**
   - 緩解：實現自動清理和 CDN 分發

### 開發風險
1. **架構重構影響現有功能**
   - 緩解：保持向後兼容，分階段遷移

2. **前後端同步開發**
   - 緩解：先定義清楚 API 契約

---

## 8. 下一步行動

### 立即開始
1. [ ] 技術選型 POC (TTS 引擎對比)
2. [ ] 設計詳細 API 規格
3. [ ] 建立開發分支

### 本週完成
1. [ ] Phase 1 基礎架構搭建
2. [ ] 編寫開發文檔
3. [ ] 團隊技術評審

---

**PRD 版本**: v1.0  
**最後更新**: 2025-10-05  
**負責人**: [Your Name]  
**預計完成**: 4 週後