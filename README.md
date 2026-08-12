# 政务舆情态势平台 MVP

这是一个前后端分离的态势图项目，当前仓库包含：

- `backend/`：FastAPI 后端，负责读取 Excel 数据并提供 `GET /api/dashboard`
- `frontend/`：React + Vite 前端
- `static/`：由 FastAPI 直接托管的静态页面资源

## 目录结构

- `backend/app/main.py`：后端 API 入口
- `backend/app/dashboard_loader.py`：读取和整理仪表盘数据
- `backend/app/seed.py`：初始化或刷新数据
- `frontend/src/App.jsx`：前端主界面
- `static/index.html`：后端直接托管的静态页入口

## 运行环境

- Python 3.11+
- Node.js 18+

## 数据文件

后端默认读取本地 Excel 文件，路径在 `backend/app/config.py` 中配置，也可以通过环境变量覆盖：

- `SUMMARY_WORKBOOK`
- `DETAIL_DIR`

默认值如下：

- `SUMMARY_WORKBOOK=C:\Users\71017\OneDrive\桌面\动态态势图\民族团结进步促进法舆情统计最终版.xlsx`
- `DETAIL_DIR=C:\Users\71017\OneDrive\桌面\动态态势图\细节表`

如果你把数据文件放到别的地方，建议直接修改这两个环境变量。

## 后端启动

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m app.seed
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

启动后访问：

- `http://localhost:8000/`
- `http://localhost:8000/api/health`
- `http://localhost:8000/api/dashboard`

## 前端启动

如果你想单独跑前端开发环境：

```powershell
cd frontend
npm install
npm run dev
```

前端开发服务器默认访问：

- `http://localhost:5173`

## 说明

- `static/` 目录中的页面由 FastAPI 直接托管，不依赖前端开发服务器。
- 仓库里不建议提交虚拟环境、`__pycache__`、`node_modules`、`dist` 等生成文件。
