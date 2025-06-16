# 單一登入（SSO）引入說明與實作方案

## 📌 為什麼要引入 SSO Server？

1. ✅ **統一身份驗證**：用戶只需登入一次，即可訪問多個系統（GitLab、JumpServer、Web UI 等）。
2. ✅ **提升資安性**：集中管理帳號權限，支援多因素驗證（MFA）。
3. ✅ **簡化維運與審計**：帳號整合 AD，登入紀錄集中，便於追蹤與控管。
4. ✅ **減少重複帳號管理**：避免各系統重複建帳、密碼不同步的問題。

---

## 🛠 SSO 架構總覽

使用者 → SSO Server（Authentik） → AD/LDAP、RADIUS、Web App

- Authentik 作為 SSO Server，支援：
  - OIDC / SAML：對外提供 SSO
  - LDAP：對接 AD 取得帳號資訊
  - RADIUS：給 VPN/Wi-Fi 裝置使用

```
                        +------------------+
                        |   Web App (SSO)  |
                        +--------+---------+
                                 ↓ OIDC/SAML
                          +------+--------+
                          |   Authentik   |
                          +------+--------+
                                 ↓
         +------------------+    ↓ RADIUS 認證        +----------------+
         | Active Directory | <---------------------> | VPN / Wi-Fi   |
         |  (LDAP)          |                        | (RADIUS Client)|
         +------------------+                        +----------------+
```

---

## wifi 登入流程

```
sequenceDiagram
    participant User as 使用者裝置
    participant AP as Wi-Fi AP / 控制器
    participant RADIUS as Authentik RADIUS Provider
    participant Authentik as Authentik 核心
    participant LDAP as Windows AD (LDAP)

    User->>AP: 1. 發起 Wi-Fi 連線（802.1X EAP）
    AP->>RADIUS: 2. 發送 Access-Request（含帳號/密碼）
    RADIUS->>Authentik: 3. 傳遞帳密驗證請求
    Authentik->>LDAP: 4. 查詢帳號 / 驗證密碼
    LDAP-->>Authentik: 5. 回應驗證結果（成功/失敗）
    Authentik-->>RADIUS: 6. 回傳驗證結果（Access-Accept / Reject）
    RADIUS-->>AP: 7. 回傳驗證結果
    AP-->>User: 8. Wi-Fi 連線成功 / 拒絕
```

---

## 🚀 如何實作 SSO

### 1. 部署 Authentik
```bash
docker run -d \
  --name authentik \
  -p 9000:9000 \
  -e AUTHENTIK_SECRET_KEY=<your-secret> \
  ghcr.io/goauthentik/server:latest
```

2. 設定 LDAP 身份來源（接 Windows AD）
	•	LDAP Host: ldap://your-ad-server
	•	Base DN: DC=yourdomain,DC=com
	•	Bind 用戶與密碼填入 AD 查詢帳號

3. 整合服務端（範例）

| 服務       | 協議       | 說明                                   |
|------------|------------|----------------------------------------|
| GitLab     | OIDC       | 使用者登入即跳轉 Authentik 認證        |
| JumpServer | LDAP       | 使用 Authentik 或 AD 驗證使用者        |
| Web UI     | OIDC/SAML  | 可使用 oauth2-proxy 或原生整合         |
| VPN/Wi-Fi  | RADIUS     | VPN 透過 Authentik 驗證帳號密碼        |

⸻

🔐 建議
	•	開啟 2FA 提升資安
	•	設定群組對應權限（如 GitLab Admin）
	•	所有應用導回 Authentik，實現單一登入與登出