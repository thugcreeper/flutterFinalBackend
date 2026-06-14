# Flutter Final Backend

本專案是為 Flutter 行動應用程式設計的後端 API，使用 **FastAPI** 框架進行開發，並整合 **Firebase / Firestore** 作為資料庫與部分驗證服務。

---

## 🚀 功能特點

- **身分驗證 (Authentication)**
  - 本地帳號註冊與登入（使用 Argon2 加密演算法安全雜湊密碼）。
  - Google 登入整合（驗證前端傳遞的 Firebase ID Token）。
  - 基於 JWT 的無狀態存取權杖驗證。
- **使用者管理 (User Profile Management)**
  - 取得當前登入使用者的詳細資訊。
  - 更新使用者個人檔案（名稱、描述、頭像連結等）。
  - 刪除使用者帳號。
- **超商門市資訊整合 (Convenience Store API Integration & Database Sync)**
  - 自動從 7-Eleven 與全家便利商店的 API 獲取門市與定位資訊。
  - 透過 Batch 寫入將大量超商資訊同步至 Firestore 資料庫。

---

## 📂 專案目錄架構

```text
.
├── .env.example                # 環境變數設定範本
├── README.md                   # 專案說明文件
├── requirements.txt            # Python 依賴套件清單
├── key.json                    # Firebase 金鑰檔案（請勿推上 Git）
└── app/
    ├── main.py                 # FastAPI 應用程式入口與路由註冊
    ├── api/
    │   ├── authapi.py          # /auth 相關路由（註冊、登入、Google 登入）
    │   └── userapi.py          # /users 相關路由（個人資料取得、更新、刪除）
    ├── core/
    │   ├── config.py           # 環境變數設定載入
    │   ├── firebase.py         # Firebase Admin SDK 初始化與 Firestore 用戶端
    │   └── security.py         # 密碼 Hash (Argon2) 與 JWT 簽發/解析
    ├── repository/
    │   └── user_repository.py  # Firestore 使用者資料 CRUD 封裝
    ├── schemas/
    │   ├── auth.py             # 登入與註冊的 Pydantic 請求/回應模型
    │   └── user.py             # 使用者資料更新的 Pydantic 請求模型
    ├── script/
    │   ├── recordFamilyMartStore.py # 獲取並同步全家便利商店門市至 Firestore
    │   └── recordSevenElevenStore.py # 獲取並同步 7-11 門市至 Firestore
    └── services/
        └── auth_service.py     # 處理註冊、登入、Google 驗證之商業邏輯
```

---

## 🛠️ 開發環境配置

### 系統需求
- Python 3.10+ (本專案開發環境為 `python 3.13.0`)

### 1. 建立並啟動虛擬環境

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數 (`.env`)

請在專案根目錄下建立 `.env` 檔案，並配置以下欄位：

```ini
# JWT 相關設定
JWT_SECRET_KEY=你的隨機密鑰字串 (建議使用 openssl rand -hex 32 產生)
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Firebase 相關設定
FIREBASE_CREDENTIALS_JSON=key.json內容
FIRESTORE_USERS_COLLECTION=users

# 全家便利商店 API 密鑰 (執行全家門市同步腳本時需要)
FAMILYMART_API_KEY=你的全家 API 密鑰
```

---

## 🔌 啟動 API 服務

```bash
uvicorn app.main:app --reload --port 8000
```
啟動後可至瀏覽器查看自動產生的 API 文件：
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📦 超商門市資料同步腳本

本專案提供兩個獨立的腳本，用於向超商 API 請求門市位置資料，並將其同步到 Firestore。

### 1. 同步 7-Eleven 門市資料

```bash
python -m app.script.recordSevenElevenStore
```
* **運作機制**：透過 API 取得指定縣市與行政區的所有 7-11 門市資料（地址、經緯度、電話、店號等），並上傳至 Firestore 的 `7-11Store` 集合（以門市 ID 為 Document ID）。

### 2. 同步 全家便利商店 門市資料

```bash
python -m app.script.recordFamilyMartStore
```
* **運作機制**：使用全家地圖 API，取得門市位置，解析後轉換成標準格式，以批次（Batch）方式上傳至 Firestore 的 `familyMartStore` 集合。
* *注意：此腳本需要於 `.env` 中設定 `FAMILYMART_API_KEY`*。

---

## 接口規格說明 (API Specifications)

### 1. 驗證模組 (`/auth`)

| 節點 | 方法 | 說明 | 請求主體 (Body) |
| :--- | :---: | :--- | :--- |
| `/auth/register` | `POST` | 本地帳號註冊 | `{ "account": "username", "password": "password", "name": "Nickname" }` |
| `/auth/login` | `POST` | 本地帳號登入 | `{ "account": "username", "password": "password" }` |


### 2. 使用者資訊模組 (`/users`)

*所有 `/users` 路由皆需要於 Header 攜帶 `Authorization: Bearer <accessToken>`*

- **GET `/users/me`**
  - **說明**：取得當前登入使用者的個人資料。
- **PATCH `/users/me`**
  - **說明**：部分更新使用者資料。
  - **請求主體**：
    ```json
    {
      "account": "new_account",
      "name": "New Name",
      "description": "I love flutter!",
      "imageUrl": "https://example.com/avatar.png"
    }
    ```
- **DELETE `/users/me`**
  - **說明**：永久刪除當前使用者的帳號。

---

## 🗄️ 資料庫欄位結構 (Firestore Schema)

### `users` 集合 (Collection)

每個 User 文件包含以下欄位：
```json
{
  "id": "自動產生的唯一識別碼 (對應文件 ID)",
  "account": "使用者登入帳號",
  "provider": "註冊來源 (local 或 google)",
  "passwordHash": "經 Argon2 雜湊後的密碼 (Google 登入者為空字串)",
  "name": "使用者顯示名稱",
  "description": "個人自我介紹",
  "imageUrl": "頭像網址",
  "createdAt": "帳號建立時間"
}
```

### `7-11Store` 與 `familyMartStore` 集合

超商文件欄位結構如下：
```json
{
  "id": "門市店號 (作為文件 ID)",
  "name": "門市名稱",
  "address": "門市地址",
  "telephone": "門市電話",
  "open_time": "營業時間 (7-11 專用)",
  "latitude": 25.033964,
  "longitude": 121.564468
}
```
