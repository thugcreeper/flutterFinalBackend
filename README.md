# flutterFinalBackend

# 建立虛擬環境
python -m venv .venv

# 啟動虛擬環境
.venv\Scripts\activate

# 安裝依賴套件
pip install -r requirements.txt

# 啟動 API
uvicorn app.main:app --reload

# 環境變數
JWT_SECRET_KEY=請改成自己的隨機密鑰
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json 的路徑 (可選)
FIRESTORE_USERS_COLLECTION=users

# 登入設計
- account: 使用者輸入的登入帳號
- id: 系統自動產生唯一識別碼
- provider: local 或 google

# 使用者文件欄位 (Firestore)
- id (回傳時對應文件 ID)
- account
- provider
- passwordHash (local 用, google 為空字串)
- name
- description
- imageUrl
- createdAt

# 後端 ASCII 架構

後端主要目錄與檔案概覽（供快速導覽）：

```
.
├── README.md
├── requirements.txt
└── app/
	├── main.py                     # FastAPI 應用入口、路由註冊
	├── api/
	│   ├── authapi.py              # /auth 註冊 / 登入 / google-login
	│   └── userapi.py              # /users/me GET/PATCH/DELETE
	├── services/
	│   └── auth_service.py         # 註冊／登入／Google 登入與使用者商業邏輯
	├── repository/
	│   └── user_repository.py      # Firestore CRUD 封裝
	├── core/
	│   ├── config.py               # 環境設定 (.env)
	│   ├── firebase.py             # Firebase / Firestore 初始化
	│   └── security.py             # 密碼雜湊與 JWT 操作
	└── schemas/
		├── auth.py                 # Pydantic 請求/回應模型
		└── user.py
```

# API
- POST /auth/register
	- body: { "account": "tom001", "password": "123456", "name": "Tom" }
- POST /auth/login
	- body: { "account": "tom001", "password": "123456" }
- POST /auth/google-login
	- body: { "idToken": "firebase-id-token" }

- GET /users/me
	- header: Authorization: Bearer <accessToken>
- PATCH /users/me
	- header: Authorization: Bearer <accessToken>
	- body: { "account": "tom002", "name": "Tom", "description": "...", "imageUrl": "..." }
- DELETE /users/me
	- header: Authorization: Bearer <accessToken>

    