# Monorepo ASR+TTS 服務 PRD

**文件版本**：v0.1
**最後更新**：2025-10-05 (Asia/Taipei)
**作者/Owner**：Steve（產品/技術）、AI 助手（PRD 起稿）
**狀態**：草稿（可直接落地）

---

## 1. 背景與目標

現有服務已提供 Whisper（ASR）轉錄能力，前後端分層清楚（`api/` Python、`frontend/` Next.js）。本次改造要在 **同一個 monorepo** 內加入 **TTS（文字轉語音）**，並抽取 **共用音訊處理與基礎設施**，形成可複用的能力層。短中期目標如下：

* **MVP（2 週內）**：

  * 提供 `POST /tts/synthesize`（同步 & 伺機支援 streaming），能以 1–2 個主流開源模型（優先：Piper / Kokoro / XTTSv2 其一）生成語音檔（WAV/MP3）。
  * 前端提供簡易 UI（文字框 → 語音播放/下載）。
  * 共用模組 `common-audio`：取樣率轉換、VAD、loudnorm、檔案編碼/解碼。
  * 共用模組 `common-infra`：日誌、追蹤、任務佇列 SDK、S3 物件儲存封裝。

* **vNext（1–2 月）**：

  * **Streaming TTS**（WebSocket/Server-Sent Events）。
  * **零樣本/語音克隆**（上傳短樣本，生成近似音色）。
  * **中英雙語**與合成參數（語速、音高、情緒）。
  * **批次工作**（長文自動切片合成、併回單檔）。

**成功判準（Success Criteria）**：

* 從 PR 合併到可部署的 lead time ≤ 30 分鐘；
* 單句 120 字內的合成 **P95 延遲 ≤ 2.5 秒（GPU） / ≤ 8 秒（CPU）**；
* 99% 回應狀態 2xx；
* 前端可連續輸入 5 次請求無錯（demo-ready）。

---

## 2. 目標用戶與場景

* **內部工程/內容團隊**：

  * 將轉錄稿（ASR）校對後，直接在同系統合成旁白。
  * 偶爾需要批次把多段文案輸出為語音素材。
* **自動化流程（後台）**：

  * 以工作佇列（Redis/Celery/RQ）串接：上傳文案 → 佇列 → 產出檔案 → S3/MinIO 保存。

---

## 3. 範圍（Scope）

**In Scope（MVP）**

* 單語音色（固定/可選清單） TTS 合成。
* REST API + 單檔輸入輸出。
* 伺服器端轉檔（支援 22.05k/24k/48k Hz）與基礎後處理（normalize）。
* 前端最小功能頁（輸入文字、選語音、播放、下載）。

**Out of Scope（MVP 以後再做）**

* 完整的說話者克隆與情感控制（僅預留參數）。
* 多語自動語言偵測（先用顯式語言選單）。
* 權限/計費/配額（先跑內部可信網路）。

---

## 4. 系統與 Monorepo 架構

```
repo-root/
├─ api/                      # Python (FastAPI + workers)
│  ├─ Dockerfile.api.asr
│  ├─ Dockerfile.api.tts
│  ├─ requirements.txt
│  └─ src/
│     ├─ whisper_api.py      # 既有 ASR
│     ├─ tts_api.py          # 新：TTS 入口（FastAPI router 掛載）
│     ├─ routers/
│     │  ├─ asr.py
│     │  └─ tts.py           # 新：/tts/* REST 路由
│     ├─ workers/
│     │  ├─ transcribe_worker.py
│     │  └─ tts_worker.py    # 新：批次/長文合成
│     └─ common/             # 新：共用層
│        ├─ audio/           # resample, vad, loudnorm, codecs
│        └─ infra/           # logging, tracing, queue, s3 client
├─ frontend/                 # Next.js App Router
│  └─ src/
│     ├─ app/tts             # 新：TTS 頁面（/tts）
│     └─ lib/api             # 前端 API SDK（fetch 封裝）
├─ packages/                 # 可選：共用 TS/py 套件（未來）
├─ docker-compose.yml        # 本地一鍵起（api-asr、api-tts、redis、minio）
└─ .github/workflows/
   ├─ api-asr.yml            # 路徑過濾
   ├─ api-tts.yml            # 路徑過濾
   └─ frontend.yml
```

**關鍵設計**

* **雙入口同服務或獨立服務**：

  * 方案 A：同一個 FastAPI app 掛兩組 router（簡化部署）。
  * 方案 B：ASR/TTS 各自 uvicorn 服務（便於獨立擴縮）。MVP 先 A，預留 B。
* **模型資源管理**：

  * 以環境變數選擇模型：`TTS_BACKEND=piper|kokoro|xtts`；
  * 權重 **不進 Git**，開機或第一次請求時下載至 `~/.cache` 或掛載 volume；必要時用 DVC 指定版本。
* **任務佇列**：

  * Redis + RQ/Celery 其一；MVP 支援同步合成；長文/批次走 worker。
* **物件儲存**：

  * MinIO (S3 相容) 保存輸出；回傳簽名網址或直接串流。

---

## 5. 功能與 API（MVP）

### 5.1 TTS

* `GET /api/tts/healthz` → 200（回傳當前模型、設備、可用語音）
* `GET /api/tts/voices` → 可用語音清單（id、語言、gender、描述）
* `POST /api/tts/synthesize`

  * **Body**：`{ text, voice_id, lang, speed?, pitch?, format? (wav/mp3), normalize? }`
  * **200**：`audio/*`（檔流）或 `{ url }`（S3 連結）
  * **429/503**：佇列滿或 GPU 忙碌
* `POST /api/tts/jobs`

  * **Body**：`{ items: [{text, voice_id, ...}], concat?: true }`
  * **202**：`{ job_id }`
* `GET /api/tts/jobs/:id` → `{ status, progress, files: [{url, part_index}] }`

### 5.2 ASR（既有，列出對齊）

* `POST /api/asr/transcribe`（支援 wav/mp3/m4a）；
* `GET /api/asr/jobs/:id`；

**前端（/tts）**

* Textarea、語音下拉、語速/音高 slider、播放/下載按鈕；
* 近期列表（最近 10 次合成，連結 S3）。

---

## 6. 效能與容量目標（SLO/SLI）

* **延遲**：單句 120 字（約 8–12 秒音長）在 GPU 模式 **P95 ≤ 2.5 s**；CPU **P95 ≤ 8 s**。
* **併發**：

  * 同步 API：限制 **並行語音合成 ≤ GPU 數 × N**（以 semaphore 控制）。
  * 其餘排入佇列（可回 202 + job_id）。
* **輸出格式**：預設 WAV 24kHz / PCM16；可選 MP3 128k。
* **穩定性**：99% request 成功、5xx ≤ 千分之三。

---

## 7. 安全、授權與合規

* **授權**：

  * 程式碼 MIT/Apache-2.0；**模型權重需逐一核對**（Piper/Kokoro 多為 Apache/MIT；XTTSv2 的權重與商用條款需另行確認）。
* **資料保護**：

  * 僅內網可用；輸入文字/輸出音檔可選是否持久化（`RETENTION_DAYS`）。
* **濫用防護**：

  * 基礎速率限制（IP/user）；
  * 黑名單字詞（可選，MVP 可略）。

---

## 8. 部署與環境

* **Docker**：`Dockerfile.api.asr`、`Dockerfile.api.tts`（multi-stage）；
* **docker-compose（dev）**：`api-asr`、`api-tts`、`redis`、`minio`、`frontend`；
* **K8s（prod）**：

  * `Deployment` 分別對 `asr`/`tts`；
  * `HPA` 以 CPU/GPU 指標自動伸縮；
  * `ReadinessProbe`：載入模型後才就緒。

**環境變數（示例）**

```
TTS_BACKEND=piper|kokoro|xtts
TTS_DEVICE=cuda:0|cpu
S3_ENDPOINT=http://minio:9000
S3_BUCKET=media
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
QUEUE_URL=redis://redis:6379/0
MAX_CONCURRENCY=2
RETENTION_DAYS=7
```

---

## 9. 觀測性與運維

* **Logging**：結構化 JSON；關鍵欄位（req_id/model/latency_ms/device）。
* **Metrics**：

  * `tts_requests_total{model,voice}`
  * `tts_latency_ms_bucket{model,device}`（Histogram）
  * `queue_depth`、`gpu_mem_used_bytes`
* **Tracing**：OpenTelemetry（`/tts/synthesize` → `tts_infer` span）。
* **告警**：P95 延遲連續 5 分鐘超標；5xx 比例 > 1%。

---

## 10. 測試策略

* **單元測試**：共用 audio/infra、參數驗證。
* **整合測試**：啟動輕量模型（CPU）跑 e2e（`test_tts_api.py`）。
* **負載測試**：`k6` 或 `locust`，10/30/50 RPS 階梯，觀察 P95/P99。
* **回歸測試**：CI Path Filter；僅改動 TTS 相關路徑時跑 TTS 方案。

---

## 11. 里程碑與交付

* **M0（今天+3 天）**：目錄/共用層雛形、`/tts/healthz`、Piper/Kokoro 其一能合成。
* **M1（+7 天）**：`/tts/synthesize` 穩定、前端 `/tts` 頁面可播放/下載、S3 落地、簡單 metrics。
* **M2（+14 天）**：批次 `jobs`、最小 Streaming（SSE）、告警與 dashboard 初版。

**交付物**：

* API 與前端可用；
* docker-compose 一鍵啟動；
* README（安裝/環境變數/限流/常見錯誤）；
* 3 段 demo 文案 + 產出音檔（樣例）。

---

## 12. 風險與緩解

* **GPU/CPU 資源爭用**：

  * 緩解：兩服務可在不同 node；或 TTS 設定 `MAX_CONCURRENCY`，語音長文走 worker。
* **模型授權不清**：

  * 緩解：在 `MODELS.md` 列表化權重來源/版本/License；CI 檢查僅允許白名單模型。
* **長文 TTS OOM**：

  * 緩解：切片（按標點/長度），分段合成再無縫拼接；
* **音質主觀**：

  * 緩解：內部 MOS-like 打分表；提供 2–3 個 voice baseline。

---

## 13. 開放問題（待決）

1. MVP 選用哪個 TTS 後端作為 baseline（Piper/Kokoro/XTTSv2）？
2. 是否一開始就要支援 Streaming（SSE/WS）？
3. 物件存放使用 MinIO（內部）還是直接本地檔案系統？
4. 語音克隆功能是否納入 M2（需要授權與道德規範）？

---

## 14. 驗收標準（Acceptance Criteria）

* [ ] `POST /api/tts/synthesize` 可在 dev/prod 成功返回音檔，**P95 延遲**符合目標。
* [ ] 前端 `/tts` 頁面支援輸入、選聲音、播放、下載；
* [ ] docker-compose 本地一鍵跑通（含 Redis/MinIO）；
* [ ] 觀測：Prometheus 指標能看到 `tts_requests_total` 與延遲直方圖；
* [ ] README 清楚（安裝、變數、限制、常見錯誤）。

---

### 附錄 A：`docker-compose.yml` 雛形（摘要）

```yaml
services:
  redis:
    image: redis:7
  minio:
    image: minio/minio
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=adminadmin
    command: server /data --console-address :9001
    ports: ["9000:9000", "9001:9001"]

  api:
    build:
      context: ./api
      dockerfile: Dockerfile.api.tts
    environment:
      - TTS_BACKEND=piper
      - TTS_DEVICE=cpu
      - S3_ENDPOINT=http://minio:9000
      - S3_BUCKET=media
      - QUEUE_URL=redis://redis:6379/0
    depends_on: [redis, minio]
    ports: ["8000:8000"]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_BASE=http://localhost:8000
```

### 附錄 B：TTS 後端介面（Python）

```python
class TTSBackend(Protocol):
    def list_voices(self) -> list[Voice]: ...
    def synthesize(self, text: str, voice_id: str, lang: str,
                   speed: float = 1.0, pitch: float = 0.0,
                   fmt: str = "wav") -> bytes: ...
```

> 備註：本 PRD 為可執行草稿，後續會依選定模型與部署環境補充 `MODELS.md`、`OBSERVABILITY.md` 與 `SECURITY.md`。
