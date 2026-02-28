# Real-Time Environmental Risk Project

A streaming pipeline that simulates rainfall and river-level data, computes a sliding-window rainfall trend, derives a composite flood risk, and presents a live, card-style dashboard with charts and history.

## Overview
- Backend engine: [app.py](file:///c:/Users/admin/OneDrive/Desktop/real%20time%20AI/app.py) (Pathway on WSL/Ubuntu)
- Frontend server: [frontend.py](file:///c:/Users/admin/OneDrive/Desktop/real%20time%20AI/frontend.py) with UI [index.html](file:///c:/Users/admin/OneDrive/Desktop/real%20time%20AI/web/index.html)
- Standalone dashboard: [dashboard.py](file:///c:/Users/admin/OneDrive/Desktop/real%20time%20AI/dashboard.py) (chart + table)
- Auto launcher: [start-project.ps1](file:///c:/Users/admin/OneDrive/Desktop/real%20time%20AI/start-project.ps1)
- Stream outputs: web/data.jsonl (primary), web/rag.jsonl (RAG when OPENAI_API_KEY is set)

## Requirements
- Windows with WSL2 and Ubuntu-22.04
- Ubuntu: Python 3 and pip
- Windows: Python 3 to run frontend/dashboard
- Pathway (installed in Ubuntu): `python3 -m pip install --no-cache-dir pathway`

## Quick Start (Windows PowerShell)

```powershell
cd "C:\Users\admin\OneDrive\Desktop\real time AI"
.\start-project.ps1
```

- Optional parameters:

```powershell
.\start-project.ps1 -Distro "Ubuntu-22.04" -FrontendPort "8001" -OpenAIKey "sk-..." -Location "Gurugram"
```

- This starts the backend in WSL and the frontend in PowerShell, then opens the browser.

## Manual Run

### Backend (Ubuntu / WSL)
```bash
cd "/mnt/c/Users/admin/OneDrive/Desktop/real time AI"
# optional: only needed for RAG explanations
export OPENAI_API_KEY="sk-..."
python3 app.py
```

### Frontend (Windows PowerShell)
```powershell
cd "C:\Users\admin\OneDrive\Desktop\real time AI"
# optional: set location label
$env:FRONTEND_LOCATION="Noida"
python .\frontend.py
```

### Dashboard (Windows PowerShell)
```powershell
cd "C:\Users\admin\OneDrive\Desktop\real time AI"
$env:DASHBOARD_PORT="8090"
$env:FRONTEND_LOCATION="Noida"
python .\dashboard.py
```

## URLs
- Frontend (auto-selects free port; default 8001): http://localhost:8001/
- Dashboard (auto-selects free port; default 8010): http://localhost:8010/

## Frontend API
- `GET /api/latest` → latest JSON row from data.jsonl; falls back to rag.jsonl if primary is empty
- `GET /api/latest-rag` → latest JSON row from rag.jsonl
- `GET /api/history?n=50` → last N rows as JSON array (from data.jsonl; fallback rag.jsonl)
- `GET /api/location` → `{ "name": "<FRONTEND_LOCATION>" }` if set; otherwise 204

## Environment Variables
- `OPENAI_API_KEY` (Ubuntu backend): enables RAG explanations, writes to web/rag.jsonl
- `FRONTEND_PORT` (Windows frontend): preferred port for frontend; will try next ports if busy
- `FRONTEND_LOCATION` (Windows frontend/dashboard): sets header location; otherwise uses browser geolocation
- `DASHBOARD_PORT` (Windows dashboard): preferred port for dashboard; will try next ports if busy

## Troubleshooting
- 204 on `/api/latest`: backend not writing yet; ensure `python3 app.py` is running in Ubuntu
- Port conflict: servers auto-try subsequent ports and print the bound URL
- pip timeouts (Ubuntu): use `--timeout 600 --retries 20 --no-cache-dir`, or `-i https://pypi.org/simple`
- Paths: use `/mnt/c/...` only inside Ubuntu; in PowerShell use `C:\...`

## Project Structure
- `app.py` — Pathway stream and risk logic; writes JSONL
- `frontend.py` — serves `/` and `api` endpoints; reads JSONL
- `web/index.html` — card-style UI with score bar, tips, and metrics
- `dashboard.py` — chart + table dashboard; reads JSONL
- `start-project.ps1` — launches backend in WSL and frontend in Windows
- `web/data.jsonl` — primary stream
- `web/rag.jsonl` — RAG stream when OPENAI_API_KEY is set

## Notes
- Do not hardcode secrets; use environment variables
- The UI auto-refreshes; charts and table update every few seconds
