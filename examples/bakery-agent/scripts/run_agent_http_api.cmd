@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" scripts\agent_http_api.py --host 0.0.0.0 --port 8765 --timeout 360 >> "runs\agent_http_api.out.log" 2>> "runs\agent_http_api.err.log"
