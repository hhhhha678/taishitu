# 政务舆情态势平台 MVP

本项目当前实现的是第一阶段的大屏版本：

- 后端：FastAPI + Pandas
- 前端：React + Vite + ECharts
- 数据源：历史统计总表 + 细节表
- 展示目标：非实时动态态势大屏

## 结构

- `backend/` 后端 API 和数据处理
- `frontend/` 前端态势看板

## 启动

### 数据源

- 默认读取：
  - `C:\Users\71017\OneDrive\桌面\动态态势图\民族团结进步促进法舆情统计最终版.xlsx`
  - `C:\Users\71017\OneDrive\桌面\动态态势图\细节表`
- 可通过环境变量覆盖：
  - `SUMMARY_WORKBOOK`
  - `DETAIL_DIR`

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m app.seed
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
浏览器打开 http://localhost:8000/
```

静态页面由 FastAPI 直接托管，不依赖本地 `npm install`。
